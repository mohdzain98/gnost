"""Observability rules for JavaScript and TypeScript: errors that leave no trace, stray console output.

A failure that is swallowed cannot be found in production; `console.log` instead of a logger cannot
be filtered or shipped. Findings feed the `observability` analyzer score.
"""

from __future__ import annotations

import re

from gnost.analysis.rules import shared
from gnost.analysis.rules.ecmascript.syntax import ECMASCRIPT

LANGUAGES = ("javascript", "typescript")


class SwallowedError(shared.SwallowedError):
    languages = LANGUAGES
    syntax = ECMASCRIPT
    logger_names = re.compile(
        r"^(console|logger|log|winston|pino|bunyan|Sentry|Rollbar|Bugsnag|captureException)\b",
        re.IGNORECASE,
    )


class PrintLogging(shared.PrintLogging):
    """`console.log` is for debugging; production code should use a logger."""

    languages = LANGUAGES
    syntax = ECMASCRIPT
    remediation = "Use a logger with levels (pino, winston, a framework logger) and remove debug output."
    METHODS = ("log", "debug", "info", "trace")

    def is_console(self, target: str) -> bool:
        head, _, method = target.partition(".")
        return head == "console" and method in self.METHODS
