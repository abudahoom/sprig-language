from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Node:
    line: int
    column: int


class Expr(Node):
    pass


@dataclass(frozen=True)
class Literal(Expr):
    value: Any


@dataclass(frozen=True)
class Variable(Expr):
    name: str


@dataclass(frozen=True)
class Unary(Expr):
    operator: str
    operand: Expr


@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    operator: str
    right: Expr


@dataclass(frozen=True)
class Logical(Expr):
    left: Expr
    operator: str
    right: Expr


@dataclass(frozen=True)
class Assignment(Expr):
    target: Expr
    value: Expr


@dataclass(frozen=True)
class Call(Expr):
    callee: Expr
    arguments: tuple[Expr, ...]


@dataclass(frozen=True)
class ListLiteral(Expr):
    elements: tuple[Expr, ...]


@dataclass(frozen=True)
class Index(Expr):
    collection: Expr
    index: Expr


class Stmt(Node):
    pass


@dataclass(frozen=True)
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass(frozen=True)
class LetStmt(Stmt):
    name: str
    initializer: Expr


@dataclass(frozen=True)
class BlockStmt(Stmt):
    statements: tuple[Stmt, ...]


@dataclass(frozen=True)
class IfStmt(Stmt):
    condition: Expr
    then_branch: BlockStmt
    else_branch: BlockStmt | IfStmt | None


@dataclass(frozen=True)
class WhileStmt(Stmt):
    condition: Expr
    body: BlockStmt


@dataclass(frozen=True)
class ForStmt(Stmt):
    name: str
    iterable: Expr
    body: BlockStmt


@dataclass(frozen=True)
class FunctionStmt(Stmt):
    name: str
    parameters: tuple[str, ...]
    body: BlockStmt


@dataclass(frozen=True)
class ReturnStmt(Stmt):
    value: Expr


Program = tuple[Stmt, ...]
