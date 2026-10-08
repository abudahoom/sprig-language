from __future__ import annotations

from .ast_nodes import (
    Assignment,
    Binary,
    BlockStmt,
    Call,
    Expr,
    ExpressionStmt,
    ForStmt,
    FunctionStmt,
    IfStmt,
    Index,
    LetStmt,
    ListLiteral,
    Literal,
    Logical,
    Program,
    ReturnStmt,
    Stmt,
    Unary,
    Variable,
    WhileStmt,
)
from .errors import ParseError
from .tokens import Token, TokenType as T


class Parser:
    def __init__(self, tokens: list[Token], source: str = "", filename: str = "<source>") -> None:
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.current = 0
        self.function_depth = 0

    def parse(self) -> Program:
        statements: list[Stmt] = []
        self._skip_separators()
        while not self._at_end():
            statements.append(self._declaration())
            self._consume_terminator("expected a newline or ';' after statement")
        return tuple(statements)

    def _declaration(self) -> Stmt:
        if self._match(T.LET):
            return self._let_declaration()
        if self._match(T.FN):
            return self._function_declaration()
        return self._statement()

    def _let_declaration(self) -> LetStmt:
        keyword = self._previous()
        name = self._consume(T.IDENTIFIER, "expected a variable name after 'let'")
        if self._match(T.EQUAL):
            initializer = self._expression()
        else:
            initializer = Literal(name.line, name.column, None)
        return LetStmt(keyword.line, keyword.column, name.lexeme, initializer)

    def _function_declaration(self) -> FunctionStmt:
        keyword = self._previous()
        name = self._consume(T.IDENTIFIER, "expected a function name after 'fn'")
        self._consume(T.LEFT_PAREN, "expected '(' after function name")
        parameters: list[str] = []
        if not self._check(T.RIGHT_PAREN):
            while True:
                if len(parameters) >= 255:
                    raise self._error(self._peek(), "functions cannot have more than 255 parameters")
                parameter = self._consume(T.IDENTIFIER, "expected parameter name")
                parameters.append(parameter.lexeme)
                if not self._match(T.COMMA):
                    break
        self._consume(T.RIGHT_PAREN, "expected ')' after parameters")
        self.function_depth += 1
        try:
            body = self._block("expected '{' before function body")
        finally:
            self.function_depth -= 1
        return FunctionStmt(keyword.line, keyword.column, name.lexeme, tuple(parameters), body)

    def _statement(self) -> Stmt:
        if self._match(T.IF):
            return self._if_statement()
        if self._match(T.WHILE):
            return self._while_statement()
        if self._match(T.FOR):
            return self._for_statement()
        if self._match(T.RETURN):
            return self._return_statement()
        if self._check(T.LEFT_BRACE):
            return self._block("expected '{'")
        expression = self._expression()
        return ExpressionStmt(expression.line, expression.column, expression)

    def _if_statement(self) -> IfStmt:
        keyword = self._previous()
        condition = self._expression()
        then_branch = self._block("expected '{' after if condition")
        # Newlines may appear before `else`, but they still terminate an if
        # statement when no else follows.
        saved = self.current
        self._skip_newlines()
        if not self._check(T.ELSE):
            self.current = saved
        else_branch: BlockStmt | IfStmt | None = None
        if self._match(T.ELSE):
            if self._match(T.IF):
                else_branch = self._if_statement()
            else:
                else_branch = self._block("expected '{' after 'else'")
        return IfStmt(keyword.line, keyword.column, condition, then_branch, else_branch)

    def _while_statement(self) -> WhileStmt:
        keyword = self._previous()
        condition = self._expression()
        body = self._block("expected '{' after while condition")
        return WhileStmt(keyword.line, keyword.column, condition, body)

    def _for_statement(self) -> ForStmt:
        keyword = self._previous()
        name = self._consume(T.IDENTIFIER, "expected a loop variable after 'for'")
        self._consume(T.IN, "expected 'in' after loop variable")
        iterable = self._expression()
        body = self._block("expected '{' after for loop iterable")
        return ForStmt(keyword.line, keyword.column, name.lexeme, iterable, body)

    def _return_statement(self) -> ReturnStmt:
        keyword = self._previous()
        if self.function_depth == 0:
            raise self._error(keyword, "'return' can only be used inside a function")
        if self._check(T.NEWLINE, T.SEMICOLON, T.RIGHT_BRACE, T.EOF):
            value: Expr = Literal(keyword.line, keyword.column, None)
        else:
            value = self._expression()
        return ReturnStmt(keyword.line, keyword.column, value)

    def _block(self, message: str) -> BlockStmt:
        brace = self._consume(T.LEFT_BRACE, message)
        statements: list[Stmt] = []
        self._skip_separators()
        while not self._check(T.RIGHT_BRACE) and not self._at_end():
            statements.append(self._declaration())
            self._consume_terminator("expected a newline, ';', or '}' after statement")
        self._consume(T.RIGHT_BRACE, "expected '}' after block")
        return BlockStmt(brace.line, brace.column, tuple(statements))

    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expression = self._or()
        if self._match(T.EQUAL):
            equals = self._previous()
            value = self._assignment()
            if not isinstance(expression, (Variable, Index)):
                raise self._error(equals, "assignment target must be a variable or list index")
            return Assignment(equals.line, equals.column, expression, value)
        return expression

    def _or(self) -> Expr:
        expression = self._and()
        while self._match(T.OR):
            operator = self._previous()
            right = self._and()
            expression = Logical(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _and(self) -> Expr:
        expression = self._equality()
        while self._match(T.AND):
            operator = self._previous()
            right = self._equality()
            expression = Logical(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _equality(self) -> Expr:
        expression = self._comparison()
        while self._match(T.EQUAL_EQUAL, T.BANG_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expression = Binary(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _comparison(self) -> Expr:
        expression = self._term()
        while self._match(T.GREATER, T.GREATER_EQUAL, T.LESS, T.LESS_EQUAL):
            operator = self._previous()
            right = self._term()
            expression = Binary(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _term(self) -> Expr:
        expression = self._factor()
        while self._match(T.PLUS, T.MINUS):
            operator = self._previous()
            right = self._factor()
            expression = Binary(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _factor(self) -> Expr:
        expression = self._unary()
        while self._match(T.STAR, T.SLASH, T.PERCENT):
            operator = self._previous()
            right = self._unary()
            expression = Binary(operator.line, operator.column, expression, operator.lexeme, right)
        return expression

    def _unary(self) -> Expr:
        if self._match(T.NOT, T.BANG, T.MINUS, T.PLUS):
            operator = self._previous()
            operand = self._unary()
            return Unary(operator.line, operator.column, operator.lexeme, operand)
        return self._call()

    def _call(self) -> Expr:
        expression = self._primary()
        while True:
            if self._match(T.LEFT_PAREN):
                arguments: list[Expr] = []
                if not self._check(T.RIGHT_PAREN):
                    while True:
                        if len(arguments) >= 255:
                            raise self._error(self._peek(), "calls cannot have more than 255 arguments")
                        arguments.append(self._expression())
                        if not self._match(T.COMMA):
                            break
                paren = self._consume(T.RIGHT_PAREN, "expected ')' after arguments")
                expression = Call(paren.line, paren.column, expression, tuple(arguments))
            elif self._match(T.LEFT_BRACKET):
                bracket = self._previous()
                index = self._expression()
                self._consume(T.RIGHT_BRACKET, "expected ']' after index")
                expression = Index(bracket.line, bracket.column, expression, index)
            else:
                break
        return expression

    def _primary(self) -> Expr:
        if self._match(T.FALSE):
            token = self._previous()
            return Literal(token.line, token.column, False)
        if self._match(T.TRUE):
            token = self._previous()
            return Literal(token.line, token.column, True)
        if self._match(T.NONE):
            token = self._previous()
            return Literal(token.line, token.column, None)
        if self._match(T.NUMBER, T.STRING):
            token = self._previous()
            return Literal(token.line, token.column, token.literal)
        if self._match(T.IDENTIFIER):
            token = self._previous()
            return Variable(token.line, token.column, token.lexeme)
        if self._match(T.LEFT_PAREN):
            expression = self._expression()
            self._consume(T.RIGHT_PAREN, "expected ')' after expression")
            return expression
        if self._match(T.LEFT_BRACKET):
            opening = self._previous()
            elements: list[Expr] = []
            if not self._check(T.RIGHT_BRACKET):
                while True:
                    elements.append(self._expression())
                    if not self._match(T.COMMA):
                        break
            self._consume(T.RIGHT_BRACKET, "expected ']' after list")
            return ListLiteral(opening.line, opening.column, tuple(elements))
        raise self._error(self._peek(), "expected an expression")

    def _consume_terminator(self, message: str) -> None:
        if self._check(T.RIGHT_BRACE, T.EOF):
            return
        if not self._match(T.NEWLINE, T.SEMICOLON):
            raise self._error(self._peek(), message)
        self._skip_separators()

    def _skip_separators(self) -> None:
        while self._match(T.NEWLINE, T.SEMICOLON):
            pass

    def _skip_newlines(self) -> None:
        while self._match(T.NEWLINE):
            pass

    def _match(self, *types: T) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _consume(self, token_type: T, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _check(self, *types: T) -> bool:
        return self._peek().type in types

    def _advance(self) -> Token:
        if not self._at_end():
            self.current += 1
        return self._previous()

    def _at_end(self) -> bool:
        return self._peek().type is T.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> ParseError:
        detail = message if token.type is T.EOF else f"{message}; found {token.lexeme!r}"
        return ParseError(
            detail,
            line=token.line,
            column=token.column,
            source=self.source,
            filename=self.filename,
        )
