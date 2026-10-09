"""Conservative build-time checks for Sprig's mutable lexical environments.

Function bodies may refer to later declarations in enclosing scopes. Bindings
are still resolved at runtime: this pass must not turn closures into snapshots
or assume that a reassigned function keeps its original signature.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields

from . import ast_nodes as ast
from .errors import SemanticError
from .runtime import make_globals


@dataclass
class Binding:
    arity: int | None = None


@dataclass
class Scope:
    active: dict[str, Binding]
    future: dict[str, Binding]


class SemanticAnalyzer:
    def check(self, program: ast.Program) -> None:
        self.writes: set[str] = set()
        self.declarations: Counter[str] = Counter()
        self._collect(program)
        builtins = make_globals(lambda text: None).values
        self.builtin_names = set(builtins)
        initial = {
            name: Binding(function.arity if self._stable(name) else None)
            for name, function in builtins.items()
        }
        self.scopes = [Scope(initial, self._future(program))]
        self.deferred_boundary = 0
        self.function_depth = 0
        self._statements(program)

    def _collect(self, value: object) -> None:
        if isinstance(value, ast.Assignment) and isinstance(value.target, ast.Variable):
            self.writes.add(value.target.name)
        if isinstance(value, (ast.LetStmt, ast.FunctionStmt, ast.ForStmt)):
            self.declarations[value.name] += 1
        if isinstance(value, ast.FunctionStmt):
            self.declarations.update(value.parameters)
        if isinstance(value, ast.Node):
            for field in fields(value):
                self._collect(getattr(value, field.name))
        elif isinstance(value, tuple):
            for child in value:
                self._collect(child)

    def _stable(self, name: str) -> bool:
        limit = 0 if name in self.builtin_names else 1
        return name not in self.writes and self.declarations[name] <= limit

    def _binding(self, statement: ast.Stmt) -> Binding:
        if isinstance(statement, ast.FunctionStmt) and self._stable(statement.name):
            return Binding(len(statement.parameters))
        return Binding()

    def _future(self, statements: tuple[ast.Stmt, ...]) -> dict[str, Binding]:
        return {
            statement.name: self._binding(statement)
            for statement in statements
            if isinstance(statement, (ast.LetStmt, ast.FunctionStmt))
        }

    def _lookup(self, name: str, node: ast.Node, *, assignment: bool = False) -> Binding:
        for index in range(len(self.scopes) - 1, -1, -1):
            scope = self.scopes[index]
            if index < self.deferred_boundary and name in scope.future:
                return scope.future[name]
            if name in scope.active:
                return scope.active[name]
        message = f"cannot assign to undefined variable {name!r}" if assignment else f"undefined variable {name!r}"
        raise SemanticError(message, line=node.line, column=node.column)

    def _statements(self, statements: tuple[ast.Stmt, ...]) -> None:
        for statement in statements:
            self._statement(statement)
            if isinstance(statement, ast.ReturnStmt):
                break

    def _block(self, block: ast.BlockStmt, initial: dict[str, Binding] | None = None) -> None:
        self.scopes.append(Scope(dict(initial or {}), self._future(block.statements)))
        try:
            self._statements(block.statements)
        finally:
            self.scopes.pop()

    def _statement(self, node: ast.Stmt) -> None:
        if isinstance(node, ast.ExpressionStmt):
            self._expression(node.expression)
        elif isinstance(node, ast.LetStmt):
            self._expression(node.initializer)
            self.scopes[-1].active[node.name] = Binding()
        elif isinstance(node, ast.BlockStmt):
            self._block(node)
        elif isinstance(node, ast.FunctionStmt):
            self.scopes[-1].active[node.name] = self._binding(node)
            previous = self.deferred_boundary
            self.deferred_boundary = len(self.scopes)
            self.function_depth += 1
            try:
                self._block(node.body, {name: Binding() for name in node.parameters})
            finally:
                self.function_depth -= 1
                self.deferred_boundary = previous
        elif isinstance(node, ast.ReturnStmt):
            if not self.function_depth:
                raise SemanticError("'return' can only be used inside a function", line=node.line, column=node.column)
            self._expression(node.value)
        elif isinstance(node, ast.IfStmt):
            self._expression(node.condition)
            known = self._truth(node.condition)
            if known is not False:
                self._block(node.then_branch)
            if known is not True and node.else_branch is not None:
                self._statement(node.else_branch)
        elif isinstance(node, ast.WhileStmt):
            self._expression(node.condition)
            if self._truth(node.condition) is not False:
                self._block(node.body)
        elif isinstance(node, ast.ForStmt):
            self._expression(node.iterable)
            if self._truth(node.iterable) is not False:
                self._block(node.body, {node.name: Binding()})
        else:
            raise AssertionError(f"unhandled statement {type(node).__name__}")

    @staticmethod
    def _truth(node: ast.Expr) -> bool | None:
        if isinstance(node, ast.Literal):
            return bool(node.value)
        if isinstance(node, ast.ListLiteral):
            return bool(node.elements)
        if isinstance(node, ast.Unary) and node.operator in ("not", "!"):
            value = SemanticAnalyzer._truth(node.operand)
            return None if value is None else not value
        return None

    def _expression(self, node: ast.Expr) -> Binding:
        if isinstance(node, ast.Variable):
            return self._lookup(node.name, node)
        if isinstance(node, ast.Literal):
            pass
        elif isinstance(node, ast.Unary):
            self._expression(node.operand)
        elif isinstance(node, (ast.Binary, ast.Logical)):
            self._expression(node.left)
            known = self._truth(node.left)
            skip = isinstance(node, ast.Logical) and (
                (node.operator == "and" and known is False)
                or (node.operator == "or" and known is True)
            )
            if not skip:
                self._expression(node.right)
        elif isinstance(node, ast.Assignment):
            if isinstance(node.target, ast.Variable):
                self._expression(node.value)
                self._lookup(node.target.name, node, assignment=True)
            elif isinstance(node.target, ast.Index):
                self._expression(node.target.collection)
                self._expression(node.target.index)
                self._expression(node.value)
            else:
                raise SemanticError("assignment target must be a variable or list index", line=node.line, column=node.column)
        elif isinstance(node, ast.Call):
            binding = self._expression(node.callee)
            for argument in node.arguments:
                self._expression(argument)
            if binding.arity is not None and binding.arity != len(node.arguments):
                raise SemanticError(
                    f"expected {binding.arity} arguments but got {len(node.arguments)}",
                    line=node.line, column=node.column,
                )
            if isinstance(node.callee, (ast.Literal, ast.ListLiteral)):
                raise SemanticError("only functions can be called", line=node.line, column=node.column)
        elif isinstance(node, ast.ListLiteral):
            for element in node.elements:
                self._expression(element)
        elif isinstance(node, ast.Index):
            self._expression(node.collection)
            self._expression(node.index)
        else:
            raise AssertionError(f"unhandled expression {type(node).__name__}")
        return Binding()
