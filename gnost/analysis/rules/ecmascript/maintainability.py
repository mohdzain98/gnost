"""Maintainability rules for JavaScript and TypeScript: the shared rules with JavaScript's syntax.

Complexity, length, nesting and parameter limits are language-neutral (see `gnost.analysis.rules.shared`);
here they are tied to the JavaScript and TypeScript syntax tables.
"""

from __future__ import annotations

from gnost.analysis.rules import shared
from gnost.analysis.rules.ecmascript.syntax import ECMASCRIPT

LANGUAGES = ("javascript", "typescript")


class Complexity(shared.Complexity):
    languages = LANGUAGES
    syntax = ECMASCRIPT


class LongFunction(shared.LongFunction):
    languages = LANGUAGES
    syntax = ECMASCRIPT


class LongFile(shared.LongFile):
    languages = LANGUAGES


class DeepNesting(shared.DeepNesting):
    languages = LANGUAGES
    syntax = ECMASCRIPT


class ManyParameters(shared.ManyParameters):
    languages = LANGUAGES
    syntax = ECMASCRIPT
