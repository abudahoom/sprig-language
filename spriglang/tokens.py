from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Single-character punctuation.
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    # One- or two-character operators.
    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    NEWLINE = auto()

    LET = auto()
    FN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    EOF = auto()


KEYWORDS = {
    "let": TokenType.LET,
    "fn": TokenType.FN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "none": TokenType.NONE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int

    def __str__(self) -> str:
        value = "" if self.literal is None else f" {self.literal!r}"
        return f"{self.line}:{self.column} {self.type.name} {self.lexeme!r}{value}"
