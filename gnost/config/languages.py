from typing import Dict

LANGUAGES = {
    "py": {"name": "Python", "comment": "#"},
    "js": {"name": "JavaScript", "comment": "//"},
    "jsx": {"name": "JavaScript", "comment": "//"},
    "ts": {"name": "TypeScript", "comment": "//"},
    "tsx": {"name": "TypeScript", "comment": "//"},
    "java": {"name": "Java", "comment": "//"},
    "c": {"name": "C", "comment": "//"},
    "cpp": {"name": "C++", "comment": "//"},
}


def by_language_name(
    by_extension: Dict[str, Dict[str, int]],
) -> Dict[str, Dict[str, int]]:
    """Merge per-extension counts into one entry per language (js and jsx are JavaScript)."""
    merged = {}
    for ext, stats in by_extension.items():
        name = LANGUAGES.get(ext, {}).get("name", ext.upper())
        into = merged.setdefault(name, {key: 0 for key in stats})
        for key, value in stats.items():
            into[key] = into.get(key, 0) + value
    return merged
