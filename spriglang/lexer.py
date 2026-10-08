from __future__ import annotations

from .errors import LexerError
from .tokens import KEYWORDS, Token, TokenType


class Lexer:
    def __init__(self, source: str, filename: str = "<source>") -> None:
        self.source = source
        self.filename = filename
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1

    def scan_tokens(self) -> list[Token]:
        while not self._at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def _scan_token(self) -> None:
        char = self._advance()
        single = {
            "(": TokenType.LEFT_PAREN,
            ")": TokenType.RIGHT_PAREN,
            "{": TokenType.LEFT_BRACE,
            "}": TokenType.RIGHT_BRACE,
            "[": TokenType.LEFT_BRACKET,
            "]": TokenType.RIGHT_BRACKET,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "%": TokenType.PERCENT,
        }
        if char in single:
            self._add(single[char])
        elif char == "!":
            self._add(TokenType.BANG_EQUAL if self._match("=") else TokenType.BANG)
        elif char == "=":
            self._add(TokenType.EQUAL_EQUAL if self._match("=") else TokenType.EQUAL)
        elif char == "<":
            self._add(TokenType.LESS_EQUAL if self._match("=") else TokenType.LESS)
        elif char == ">":
            self._add(TokenType.GREATER_EQUAL if self._match("=") else TokenType.GREATER)
        elif char == "/":
            if self._match("/"):
                while self._peek() not in ("\n", "\0"):
                    self._advance()
            else:
                self._add(TokenType.SLASH)
        elif char == "#":
            while self._peek() not in ("\n", "\0"):
                self._advance()
        elif char in (" ", "\r", "\t"):
            return
        elif char == "\n":
            self._add(TokenType.NEWLINE)
        elif char in ('"', "'"):
            self._string(char)
        elif char.isdigit():
            self._number()
        elif char.isalpha() or char == "_":
            self._identifier()
        else:
            raise LexerError(
                f"unexpected character {char!r}",
                line=self.start_line,
                column=self.start_column,
                source=self.source,
                filename=self.filename,
            )

    def _string(self, quote: str) -> None:
        value: list[str] = []
        escapes = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
        while not self._at_end() and self._peek() != quote:
            char = self._advance()
            if char == "\n":
                raise self._error("strings cannot span lines")
            if char == "\\":
                if self._at_end():
                    raise self._error("unfinished escape sequence")
                escaped = self._advance()
                if escaped not in escapes:
                    raise self._error(f"unknown escape sequence \\{escaped}")
                value.append(escapes[escaped])
            else:
                value.append(char)
        if self._at_end():
            raise self._error("unterminated string")
        self._advance()
        self._add(TokenType.STRING, "".join(value))

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()
        is_float = False
        if self._peek() == "." and self._peek_next().isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit():
                self._advance()
        text = self.source[self.start : self.current]
        self._add(TokenType.NUMBER, float(text) if is_float else int(text))

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[self.start : self.current]
        self._add(KEYWORDS.get(text, TokenType.IDENTIFIER))

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self.current] != expected:
            return False
        self._advance()
        return True

    def _peek(self) -> str:
        return "\0" if self._at_end() else self.source[self.current]

    def _peek_next(self) -> str:
        return "\0" if self.current + 1 >= len(self.source) else self.source[self.current + 1]

    def _add(self, token_type: TokenType, literal: object = None) -> None:
        text = self.source[self.start : self.current]
        self.tokens.append(Token(token_type, text, literal, self.start_line, self.start_column))

    def _at_end(self) -> bool:
        return self.current >= len(self.source)

    def _error(self, message: str) -> LexerError:
        return LexerError(
            message,
            line=self.start_line,
            column=self.start_column,
            source=self.source,
            filename=self.filename,
        )

