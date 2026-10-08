from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import ast_nodes as ast
from .errors import RuntimeSprigError
from .runtime import (
    Environment,
    NativeFunction,
    binary_operation,
    get_index,
    make_globals,
    set_index,
    truthy,
    unary_operation,
)


@dataclass
class ReturnSignal(Exception):
    value: Any


@dataclass
class UserFunction:
    declaration: ast.FunctionStmt
    closure: Environment
    interpreter: Interpreter

    @property
    def arity(self) -> int:
        return len(self.declaration.parameters)

    def call(self, arguments: list[Any]) -> Any:
        environment = Environment(self.closure)
        for name, value in zip(self.declaration.parameters, arguments):
            environment.define(name, value)
        try:
            self.interpreter.execute_block(self.declaration.body.statements, environment)
        except ReturnSignal as signal:
            return signal.value
        return None

    def __repr__(self) -> str:
        return f"<fn {self.declaration.name}>"


class Interpreter:
    def __init__(self, output: Callable[[str], None] = print) -> None:
        self.globals = make_globals(output)
        self.environment = self.globals

    def interpret(self, program: ast.Program) -> Any:
        result = None
        for statement in program:
            result = self.execute(statement)
        return result

    def execute(self, statement: ast.Stmt) -> Any:
        if isinstance(statement, ast.ExpressionStmt):
            return self.evaluate(statement.expression)
        if isinstance(statement, ast.LetStmt):
            value = self.evaluate(statement.initializer)
            self.environment.define(statement.name, value)
            return None
        if isinstance(statement, ast.BlockStmt):
            self.execute_block(statement.statements, Environment(self.environment))
            return None
        if isinstance(statement, ast.IfStmt):
            if truthy(self.evaluate(statement.condition)):
                return self.execute(statement.then_branch)
            if statement.else_branch is not None:
                return self.execute(statement.else_branch)
            return None
        if isinstance(statement, ast.WhileStmt):
            while truthy(self.evaluate(statement.condition)):
                self.execute(statement.body)
            return None
        if isinstance(statement, ast.ForStmt):
            iterable = self.evaluate(statement.iterable)
            try:
                iterator = iter(iterable)
            except TypeError as error:
                raise self._runtime(statement, "for loops need an iterable value") from error
            for item in iterator:
                environment = Environment(self.environment)
                environment.define(statement.name, item)
                self.execute_block(statement.body.statements, environment)
            return None
        if isinstance(statement, ast.FunctionStmt):
            function = UserFunction(statement, self.environment, self)
            self.environment.define(statement.name, function)
            return None
        if isinstance(statement, ast.ReturnStmt):
            raise ReturnSignal(self.evaluate(statement.value))
        raise AssertionError(f"unhandled statement {type(statement).__name__}")

    def execute_block(self, statements: tuple[ast.Stmt, ...], environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous

    def evaluate(self, expression: ast.Expr) -> Any:
        try:
            if isinstance(expression, ast.Literal):
                return expression.value
            if isinstance(expression, ast.Variable):
                return self.environment.get(expression.name, expression.line, expression.column)
            if isinstance(expression, ast.Unary):
                return unary_operation(expression.operator, self.evaluate(expression.operand))
            if isinstance(expression, ast.Binary):
                left = self.evaluate(expression.left)
                right = self.evaluate(expression.right)
                return binary_operation(expression.operator, left, right)
            if isinstance(expression, ast.Logical):
                left = self.evaluate(expression.left)
                if expression.operator == "or":
                    return left if truthy(left) else self.evaluate(expression.right)
                return self.evaluate(expression.right) if truthy(left) else left
            if isinstance(expression, ast.Assignment):
                value = self.evaluate(expression.value)
                if isinstance(expression.target, ast.Variable):
                    self.environment.assign(expression.target.name, value, expression.line, expression.column)
                    return value
                if isinstance(expression.target, ast.Index):
                    collection = self.evaluate(expression.target.collection)
                    index = self.evaluate(expression.target.index)
                    return set_index(collection, index, value)
            if isinstance(expression, ast.Call):
                callee = self.evaluate(expression.callee)
                arguments = [self.evaluate(argument) for argument in expression.arguments]
                return self._call(callee, arguments, expression)
            if isinstance(expression, ast.ListLiteral):
                return [self.evaluate(element) for element in expression.elements]
            if isinstance(expression, ast.Index):
                return get_index(self.evaluate(expression.collection), self.evaluate(expression.index))
        except RuntimeSprigError:
            raise
        except (TypeError, ValueError) as error:
            raise self._runtime(expression, str(error)) from error
        raise AssertionError(f"unhandled expression {type(expression).__name__}")

    def _call(self, callee: Any, arguments: list[Any], node: ast.Node) -> Any:
        if not isinstance(callee, (UserFunction, NativeFunction)):
            raise self._runtime(node, "only functions can be called")
        if callee.arity is not None and len(arguments) != callee.arity:
            raise self._runtime(node, f"expected {callee.arity} arguments but got {len(arguments)}")
        try:
            return callee.call(arguments)
        except RuntimeSprigError:
            raise
        except (TypeError, ValueError) as error:
            raise self._runtime(node, str(error)) from error

    @staticmethod
    def _runtime(node: ast.Node, message: str) -> RuntimeSprigError:
        return RuntimeSprigError(message, line=node.line, column=node.column)
