import ast


async def extract_function_node(source_code, function_name):
    """
    Parse the source code and return the AST node for the specified function.
    """
    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


async def max_depth(node, level=0):
    if not isinstance(node, ast.AST) or not hasattr(node, "_fields"):
        return level
    return max(
        [
            (
                await max_depth(getattr(node, field), level + 1)
                if isinstance(getattr(node, field), list)
                else await max_depth(getattr(node, field), level + 1)
            )
            for field in node._fields
            if getattr(node, field) is not None
        ]
        + [level]
    )


async def analyze_function_complexity(func_node):
    """
    Analyze nesting, loops, conditionals, and compute LOC & cyclomatic complexity.
    """
    stats = {
        "loc": 0,
        "nesting_depth": 0,
        "ifs": 0,
        "fors": 0,
        "whiles": 0,
        "returns": 0,
        "calls": 0,
    }

    async def visit(node, depth=0):
        stats["nesting_depth"] = max(stats["nesting_depth"], depth)

        if isinstance(node, ast.If):
            stats["ifs"] += 1
        elif isinstance(node, ast.For):
            stats["fors"] += 1
        elif isinstance(node, ast.While):
            stats["whiles"] += 1
        elif isinstance(node, ast.Return):
            stats["returns"] += 1
        elif isinstance(node, ast.Call):
            stats["calls"] += 1

        for child in ast.iter_child_nodes(node):
            await visit(
                child,
                (
                    depth + 1
                    if isinstance(node, (ast.If, ast.For, ast.While, ast.Try))
                    else depth
                ),
            )

    await visit(func_node)
    stats["nesting_depth"] = await max_depth(func_node)
    stats["loc"] = (
        func_node.end_lineno - func_node.lineno + 1
        if hasattr(func_node, "end_lineno")
        else "?"
    )
    return stats


async def suggest_improvements(stats, cc_score):
    """
    Provide suggestions based on stats and cyclomatic complexity.
    """
    suggestions = []

    if stats["loc"] != "?" and stats["loc"] > 100:
        suggestions.append("Split the function into smaller units (LOC > 100).")

    if stats["nesting_depth"] > 3:
        suggestions.append("Reduce nesting by using early returns or guard clauses.")

    if stats["ifs"] > 5:
        suggestions.append("Too many conditionals — consider simplifying logic.")

    if stats["fors"] + stats["whiles"] > 3:
        suggestions.append("Too many loops — could indicate a need for decomposition.")

    if cc_score > 10:
        suggestions.append(
            "Cyclomatic complexity is high — simplify branches or logic."
        )

    if not suggestions:
        suggestions.append("Function is within reasonable complexity limits.")

    final_suggestion = " ".join(suggestions)
    return final_suggestion


async def analyze_function_in_file(filepath, function_name, cc_score):
    """
    Main callable function: accepts file path and function name, returns analysis dict.
    """
    try:
        with open(filepath, "r") as f:
            source_code = f.read()
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

    func_node = await extract_function_node(source_code, function_name)
    if func_node is None:
        return {"error": f"Function '{function_name}' not found in {filepath}"}

    stats = await analyze_function_complexity(func_node)
    suggestions = await suggest_improvements(stats, cc_score)

    return {
        "function": function_name,
        "file": filepath,
        "metrics": stats,
        "suggestions": suggestions,
    }
