import ast
from typing import Set, Optional


class DFTypeEnv:
    def __init__(self):
        self.pd_aliases: Set[str] = set()  # e.g., {'pandas', 'pd'}
        self.df_names: Set[str] = set()  # names likely to be DataFrames
        self.df_attrs: Set[str] = (
            set()
        )  # attributes on 'self' that are DataFrames (e.g., 'df_merged')
        self.direct_df_names: Set[str] = set()  # names imported as DataFrame class

    def mark_df(self, name: str):
        if name:
            self.df_names.add(name)

    def mark_attr_df(self, attr_name: str):
        if attr_name:
            self.df_attrs.add(attr_name)

    def is_dataframe_name(self, name: str) -> bool:
        return name in self.df_names

    def is_dataframe_attr(self, attr: str) -> bool:
        return attr in self.df_attrs


def _get_root_name(node: ast.AST) -> Optional[str]:
    # From Name/Attribute chain, get the leftmost Name.id
    cur = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    if isinstance(cur, ast.Name):
        return cur.id
    return None


def _attr_tail(node: ast.AST) -> Optional[str]:
    # If node is Attribute (e.g., self.df_merged), return final attr ('df_merged')
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _call_fullname(call: ast.Call) -> Optional[str]:
    # Return dotted name of a call like "pd.read_csv" or "pd.DataFrame"
    def dotted(attr: ast.AST) -> Optional[str]:
        parts = []
        cur = attr
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None

    if isinstance(call.func, ast.Attribute):
        return dotted(call.func)
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def collect_pandas_info(tree: ast.AST) -> DFTypeEnv:
    env = DFTypeEnv()

    # 1) imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pandas":
                    env.pd_aliases.add(alias.asname or "pandas")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("pandas"):
                for alias in node.names:
                    if alias.name == "DataFrame":
                        # from pandas import DataFrame as DF
                        env.direct_df_names.add(alias.asname or "DataFrame")

    # Build some helper sets of pandas call names
    pd_df_ctor = {"DataFrame"}
    pd_df_readers = {
        "read_csv",
        "read_parquet",
        "read_excel",
        "read_json",
        "read_feather",
        "read_orc",
        "read_html",
        "read_pickle",
    }

    # 2) annotate parents for later outermost-subscript filtering (optional)
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            setattr(child, "parent", parent)

    # 3) scan assignments & calls
    for node in ast.walk(tree):
        # a) Assignments: x = <call/Name>
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
            # type annotation hint
            ann = node.annotation
            ann_txt = None
            if isinstance(ann, ast.Name):
                ann_txt = ann.id
            elif isinstance(ann, ast.Attribute):
                ann_txt = _call_fullname(
                    ast.Call(func=ann, args=[], keywords=[])
                )  # hack to reuse dotted resolver
            elif isinstance(ann, ast.Constant) and isinstance(ann.value, str):
                ann_txt = ann.value
            if ann_txt and "DataFrame" in ann_txt:
                # mark target as df
                for t in targets:
                    if isinstance(t, ast.Name):
                        env.mark_df(t.id)
                    elif isinstance(t, ast.Attribute) and _is_name(t.value, "self"):
                        env.mark_attr_df(t.attr)

        else:
            value = None

        # Detect DF-producing calls on RHS
        if value and isinstance(value, ast.Call):
            fn = _call_fullname(value)
            # cases: pd.DataFrame(...), pd.read_csv(...), DataFrame(...), DF(...)
            is_pd_ctor = False
            if fn:
                parts = fn.split(".")
                if (
                    len(parts) >= 2
                    and parts[0] in env.pd_aliases
                    and parts[1] in pd_df_ctor.union(pd_df_readers)
                ):
                    is_pd_ctor = True
                elif parts[-1] in env.direct_df_names or parts[-1] == "DataFrame":
                    is_pd_ctor = True

            # mark targets as DF
            if is_pd_ctor and targets:
                for t in targets:
                    if isinstance(t, ast.Name):
                        env.mark_df(t.id)
                    elif isinstance(t, ast.Attribute) and _is_name(t.value, "self"):
                        env.mark_attr_df(t.attr)

        # b) Method calls returning DF (heuristics)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                base_name = _get_root_name(call.func.value)
                # common DF-returning methods
                if call.func.attr in {
                    "merge",
                    "join",
                    "assign",
                    "pipe",
                    "pivot",
                    "pivot_table",
                    "dropna",
                    "fillna",
                }:
                    if base_name in env.df_names:
                        for t in node.targets:
                            if isinstance(t, ast.Name):
                                env.mark_df(t.id)
                            elif isinstance(t, ast.Attribute) and _is_name(
                                t.value, "self"
                            ):
                                env.mark_attr_df(t.attr)

        # c) Heuristic: usage of DF-ish attributes on a name → mark it as DF
        if isinstance(node, ast.Attribute):
            if node.attr in {"columns", "dtypes", "iloc", "loc", "shape"}:
                root = _get_root_name(node)
                if root:
                    env.mark_df(root)
            # self.df_... attributes: if they use DF-ish attr later, we’ll mark via above

    return env


def is_dataframe_expr(env: DFTypeEnv, node: ast.AST) -> bool:
    """
    Given an expression used as 'base[...]', decide if it’s a DataFrame.
    """
    # root variable case: df_merged[...]
    root = _get_root_name(node)
    if root and env.is_dataframe_name(root):
        return True

    # self.df_merged[...] case
    if (
        isinstance(node, ast.Attribute)
        and _is_name(node.value, "self")
        and env.is_dataframe_attr(node.attr)
    ):
        return True

    # Fallback heuristic: if it's a Name that looks like df*, be careful but NOT definitive
    # return bool(root and root.startswith(("df", "dataframe")))
    return False
