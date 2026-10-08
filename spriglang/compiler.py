from __future__ import annotations

from . import ast_nodes as ast
from .bytecode import CodeObject, Instruction, Op


class Compiler:
    """Translate a Sprig AST into stack-machine bytecode."""

    def compile(self, program: ast.Program, name: str = "<script>") -> CodeObject:
        self.code = CodeObject(name)
        for statement in program:
            self._statement(statement)
        self._emit(Op.CONSTANT, None, 1, 1)
        self._emit(Op.RETURN, None, 1, 1)
        return self.code

    def _statement(self, statement: ast.Stmt) -> None:
        if isinstance(statement, ast.ExpressionStmt):
            self._expression(statement.expression)
            self._emit_node(Op.POP, None, statement)
        elif isinstance(statement, ast.LetStmt):
            self._expression(statement.initializer)
            self._emit_node(Op.DEFINE, statement.name, statement)
        elif isinstance(statement, ast.BlockStmt):
            self._block(statement)
        elif isinstance(statement, ast.IfStmt):
            self._expression(statement.condition)
            false_jump = self._emit_node(Op.JUMP_IF_FALSE, None, statement.condition)
            self._emit_node(Op.POP, None, statement.condition)
            self._block(statement.then_branch)
            end_jump = self._emit_node(Op.JUMP, None, statement)
            self._patch(false_jump)
            self._emit_node(Op.POP, None, statement.condition)
            if statement.else_branch is not None:
                self._statement(statement.else_branch)
            self._patch(end_jump)
        elif isinstance(statement, ast.WhileStmt):
            loop_start = len(self.code.instructions)
            self._expression(statement.condition)
            exit_jump = self._emit_node(Op.JUMP_IF_FALSE, None, statement.condition)
            self._emit_node(Op.POP, None, statement.condition)
            self._block(statement.body)
            self._emit_node(Op.JUMP, loop_start, statement)
            self._patch(exit_jump)
            self._emit_node(Op.POP, None, statement.condition)
        elif isinstance(statement, ast.ForStmt):
            self._expression(statement.iterable)
            self._emit_node(Op.ITER_INIT, None, statement)
            loop_start = len(self.code.instructions)
            exit_jump = self._emit_node(Op.ITER_NEXT, None, statement)
            self._emit_node(Op.ENTER_SCOPE, None, statement.body)
            self._emit_node(Op.DEFINE, statement.name, statement)
            for child in statement.body.statements:
                self._statement(child)
            self._emit_node(Op.EXIT_SCOPE, None, statement.body)
            self._emit_node(Op.JUMP, loop_start, statement)
            self._patch(exit_jump)
        elif isinstance(statement, ast.FunctionStmt):
            function_compiler = Compiler()
            function_compiler.code = CodeObject(statement.name, statement.parameters)
            for child in statement.body.statements:
                function_compiler._statement(child)
            function_compiler._emit(Op.CONSTANT, None, statement.line, statement.column)
            function_compiler._emit(Op.RETURN, None, statement.line, statement.column)
            self._emit_node(Op.MAKE_FUNCTION, function_compiler.code, statement)
            self._emit_node(Op.DEFINE, statement.name, statement)
        elif isinstance(statement, ast.ReturnStmt):
            self._expression(statement.value)
            self._emit_node(Op.RETURN, None, statement)
        else:
            raise AssertionError(f"unhandled statement {type(statement).__name__}")

    def _block(self, block: ast.BlockStmt) -> None:
        self._emit_node(Op.ENTER_SCOPE, None, block)
        for statement in block.statements:
            self._statement(statement)
        self._emit_node(Op.EXIT_SCOPE, None, block)

    def _expression(self, expression: ast.Expr) -> None:
        if isinstance(expression, ast.Literal):
            self._emit_node(Op.CONSTANT, expression.value, expression)
        elif isinstance(expression, ast.Variable):
            self._emit_node(Op.LOAD, expression.name, expression)
        elif isinstance(expression, ast.Unary):
            self._expression(expression.operand)
            self._emit_node(Op.UNARY, expression.operator, expression)
        elif isinstance(expression, ast.Binary):
            self._expression(expression.left)
            self._expression(expression.right)
            self._emit_node(Op.BINARY, expression.operator, expression)
        elif isinstance(expression, ast.Logical):
            self._expression(expression.left)
            jump_op = Op.JUMP_IF_TRUE if expression.operator == "or" else Op.JUMP_IF_FALSE
            jump = self._emit_node(jump_op, None, expression)
            self._emit_node(Op.POP, None, expression)
            self._expression(expression.right)
            self._patch(jump)
        elif isinstance(expression, ast.Assignment):
            if isinstance(expression.target, ast.Variable):
                self._expression(expression.value)
                self._emit_node(Op.DUP, None, expression)
                self._emit_node(Op.STORE, expression.target.name, expression)
            elif isinstance(expression.target, ast.Index):
                self._expression(expression.target.collection)
                self._expression(expression.target.index)
                self._expression(expression.value)
                self._emit_node(Op.SET_INDEX, None, expression)
            else:
                raise AssertionError("parser allowed an invalid assignment")
        elif isinstance(expression, ast.Call):
            self._expression(expression.callee)
            for argument in expression.arguments:
                self._expression(argument)
            self._emit_node(Op.CALL, len(expression.arguments), expression)
        elif isinstance(expression, ast.ListLiteral):
            for element in expression.elements:
                self._expression(element)
            self._emit_node(Op.BUILD_LIST, len(expression.elements), expression)
        elif isinstance(expression, ast.Index):
            self._expression(expression.collection)
            self._expression(expression.index)
            self._emit_node(Op.GET_INDEX, None, expression)
        else:
            raise AssertionError(f"unhandled expression {type(expression).__name__}")

    def _emit_node(self, op: Op, arg: object, node: ast.Node) -> int:
        return self._emit(op, arg, node.line, node.column)

    def _emit(self, op: Op, arg: object, line: int, column: int) -> int:
        self.code.instructions.append(Instruction(op, arg, line, column))
        return len(self.code.instructions) - 1

    def _patch(self, instruction_index: int) -> None:
        self.code.instructions[instruction_index].arg = len(self.code.instructions)

