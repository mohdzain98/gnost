"""Paths written with backslashes must behave like paths written with slashes."""

from gnost.languages.python import PythonAdapter
from gnost.scanner.filters import should_ignore, should_skip
from gnost.utils.paths import base, shorten, tail


def test_shorten_strips_root_with_either_separator():
    assert shorten("C:\\proj\\app\\api.py", "C:\\proj") == "app/api.py"
    assert shorten("/proj/app/api.py", "/proj") == "app/api.py"
    assert shorten("/proj/app/api.py:12", "/proj") == "app/api.py:12"


def test_tail_and_base():
    assert tail("C:\\proj\\app\\api.py") == "app/api.py"
    assert base("C:\\proj\\app\\api.py") == "api.py"


def test_ignored_folders_match_backslash_paths():
    assert should_ignore("C:\\proj\\node_modules\\x.py")
    assert should_skip("node_modules\\pkg", set(), {"node_modules"})
    assert not should_ignore("C:\\proj\\src\\x.py")


def test_entry_file_name_with_backslashes():
    assert PythonAdapter().is_entry_file_name("C:\\proj\\main.py")
