"""`.gnost.toml`: per-project settings.

Looked up from the scanned folder upwards (it stops at the repository root), so a
file at the root of a repo applies to every command run inside it. Precedence is
command-line flags, then this file, then built-in defaults. Unknown keys are
reported as warnings; wrong value types are errors that name the key.

Example::

    exclude = ["legacy", "*.generated.ts"]      # skipped by onboard and analyze

    [onboard]
    max_edges = 150          # largest diagram drawn file by file
    collapse = 1             # always group diagrams by folder
    depth = 3                # limit flow depth

    [caution]                # which files are "risky to change"
    threshold = 50           # lowest score reported (0-100)
    limit = 15               # most files reported
    [caution.weights]        # most a signal can add to a score (0-1)
    size = 0.5
    [caution.ranges]         # [counts as 0, counts as 1]
    size = [300, 1500]

    [analyze]
    analyzers = ["maintainability", "readability"]
    timeout = 600
    max_findings = 500
    parallel = true
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from gnost.core.caution import (
    DEFAULT_RANGES,
    DEFAULT_WEIGHTS,
    CautionSettings,
)

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

CONFIG_NAME = ".gnost.toml"


class ConfigError(Exception):
    """The config file cannot be used; the message names the file and key."""


_NUMBER = (int, float)
# section -> key -> accepted type(s); `None` section is the top level
SCHEMA: Dict[Optional[str], Dict[str, Any]] = {
    None: {"exclude": list},
    "onboard": {"max_edges": int, "collapse": int, "depth": int},
    "caution": {"threshold": _NUMBER, "limit": int},
    "analyze": {
        "analyzers": list,
        "timeout": int,
        "max_findings": int,
        "parallel": bool,
    },
}
_TABLES = {"caution.weights", "caution.ranges"}


@dataclass
class GnostConfig:
    path: Optional[str] = None
    values: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def get(self, section: Optional[str], key: str, default: Any = None) -> Any:
        scope = self.values if section is None else self.values.get(section, {})
        return scope.get(key, default)

    @property
    def exclude(self) -> List[str]:
        return list(self.get(None, "exclude", []))

    def pick(self, section: str, key: str, cli_value: Any, default: Any) -> Any:
        """CLI flag, else config file, else default."""
        if cli_value is not None:
            return cli_value
        return self.get(section, key, default)

    def caution_settings(self) -> CautionSettings:
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(self.values.get("caution", {}).get("weights", {}))
        ranges = dict(DEFAULT_RANGES)
        for name, pair in self.values.get("caution", {}).get("ranges", {}).items():
            ranges[name] = (float(pair[0]), float(pair[1]))
        caution = self.values.get("caution", {})
        base = CautionSettings()
        return CautionSettings(
            weights=weights,
            ranges=ranges,
            threshold=float(caution.get("threshold", base.threshold)),
            limit=int(caution.get("limit", base.limit)),
        )


def find_config(start: str) -> Optional[str]:
    """The nearest `.gnost.toml` from `start` upwards, not past the repo root."""
    current = os.path.abspath(start)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        candidate = os.path.join(current, CONFIG_NAME)
        if os.path.isfile(candidate):
            return candidate
        if os.path.isdir(os.path.join(current, ".git")):
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def load_config(start: str = ".") -> GnostConfig:
    """Load and validate the config that applies to `start` (empty if none)."""
    path = find_config(start)
    if path is None:
        return GnostConfig()
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: not valid TOML ({exc})") from exc
    except OSError as exc:
        raise ConfigError(f"{path}: cannot be read ({exc})") from exc

    config = GnostConfig(path=path)
    _validate(raw, config)
    return config


def _type_name(expected: Any) -> str:
    if expected is _NUMBER:
        return "a number"
    return {list: "a list", int: "an integer", bool: "true or false"}[expected]


def _is(value: Any, expected: Any) -> bool:
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected is _NUMBER:
        return isinstance(value, _NUMBER) and not isinstance(value, bool)
    return isinstance(value, expected)


def _validate(raw: Dict[str, Any], config: GnostConfig) -> None:
    where = config.path or CONFIG_NAME
    values: Dict[str, Any] = {}

    for key, value in raw.items():
        if key in SCHEMA[None]:
            _check(where, key, value, SCHEMA[None][key])
            values[key] = value
        elif key in SCHEMA and isinstance(value, dict):
            values[key] = _validate_section(where, key, value, config)
        else:
            config.warnings.append(f"{where}: unknown setting '{key}' (ignored)")

    exclude = values.get("exclude", [])
    if not all(isinstance(p, str) for p in exclude):
        raise ConfigError(f"{where}: 'exclude' must be a list of strings")
    config.values = values


def _validate_section(
    where: str, section: str, raw: Dict[str, Any], config: GnostConfig
) -> Dict[str, Any]:
    allowed = SCHEMA[section]
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        dotted = f"{section}.{key}"
        if key in allowed:
            _check(where, dotted, value, allowed[key])
            out[key] = value
        elif dotted in _TABLES and isinstance(value, dict):
            out[key] = _validate_table(where, dotted, value, config)
        else:
            config.warnings.append(f"{where}: unknown setting '{dotted}' (ignored)")

    if section == "analyze" and "analyzers" in out:
        if not all(isinstance(a, str) for a in out["analyzers"]):
            raise ConfigError(f"{where}: 'analyze.analyzers' must be a list of strings")
    return out


def _validate_table(
    where: str, dotted: str, raw: Dict[str, Any], config: GnostConfig
) -> Dict[str, Any]:
    signals = (
        set(DEFAULT_WEIGHTS) if dotted.endswith("weights") else set(DEFAULT_RANGES)
    )
    out: Dict[str, Any] = {}
    for name, value in raw.items():
        full = f"{dotted}.{name}"
        if name not in signals:
            config.warnings.append(f"{where}: unknown setting '{full}' (ignored)")
        elif dotted.endswith("weights"):
            _check(where, full, value, _NUMBER)
            if not 0 <= value <= 1:
                raise ConfigError(f"{where}: '{full}' must be between 0 and 1")
            out[name] = value
        else:
            if not (
                isinstance(value, list)
                and len(value) == 2
                and all(_is(v, _NUMBER) for v in value)
            ):
                raise ConfigError(
                    f"{where}: '{full}' must be two numbers, e.g. [200, 1000]"
                )
            if value[0] >= value[1]:
                raise ConfigError(
                    f"{where}: '{full}' needs the first number below the second"
                )
            out[name] = value
    return out


def _check(where: str, key: str, value: Any, expected: Any) -> None:
    if not _is(value, expected):
        raise ConfigError(
            f"{where}: '{key}' must be {_type_name(expected)}, got {value!r}"
        )


def report_warnings(config: GnostConfig) -> None:
    for message in config.warnings:
        print(f"gnost: warning: {message}", file=sys.stderr)
