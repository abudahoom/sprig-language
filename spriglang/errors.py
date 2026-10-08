from __future__ import annotations


class SprigError(Exception):
    """Base class for user-facing Sprig errors."""

    kind = "Sprig error"

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
        source: str | None = None,
        filename: str = "<source>",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.source = source
        self.filename = filename

    def __str__(self) -> str:
        if self.line is None:
            return f"{self.kind}: {self.message}"
        location = f"{self.filename}:{self.line}:{self.column or 1}"
        result = f"{location}: {self.kind}: {self.message}"
        if self.source:
            lines = self.source.splitlines()
            if 1 <= self.line <= len(lines):
                text = lines[self.line - 1]
                caret = " " * max(0, (self.column or 1) - 1) + "^"
                result += f"\n  {text}\n  {caret}"
        return result


class LexerError(SprigError):
    kind = "lexer error"


class ParseError(SprigError):
    kind = "parse error"


class RuntimeSprigError(SprigError):
    kind = "runtime error"


def enrich_error(error: SprigError, source: str, filename: str) -> SprigError:
    if error.source is None:
        error.source = source
    if error.filename == "<source>":
        error.filename = filename
    return error

