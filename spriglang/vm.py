from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .bytecode import CodeObject, Instruction, Op
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
class VMFunction:
    code: CodeObject
    closure: Environment

    @property
    def arity(self) -> int:
        return len(self.code.parameters)

    def __repr__(self) -> str:
        return f"<fn {self.code.name}>"


@dataclass
class Frame:
    code: CodeObject
    environment: Environment
    base: int
    ip: int = 0


class VirtualMachine:
    def __init__(self, output: Callable[[str], None] = print) -> None:
        self.globals = make_globals(output)
        self.stack: list[Any] = []
        self.frames: list[Frame] = []

    def run(self, code: CodeObject) -> Any:
        self.stack.clear()
        self.frames = [Frame(code, self.globals, 0)]
        while self.frames:
            frame = self.frames[-1]
            if frame.ip >= len(frame.code.instructions):
                raise RuntimeSprigError(f"function {frame.code.name!r} ended without RETURN")
            instruction = frame.code.instructions[frame.ip]
            frame.ip += 1
            try:
                result = self._execute(instruction, frame)
                if result is _HALT:
                    return self.stack.pop() if self.stack else None
            except RuntimeSprigError:
                raise
            except (TypeError, ValueError) as error:
                raise RuntimeSprigError(str(error), line=instruction.line, column=instruction.column) from error
        return None

    def _execute(self, instruction: Instruction, frame: Frame) -> object | None:
        op, arg = instruction.op, instruction.arg
        if op is Op.CONSTANT:
            self.stack.append(arg)
        elif op is Op.LOAD:
            self.stack.append(frame.environment.get(arg, instruction.line, instruction.column))
        elif op is Op.DEFINE:
            frame.environment.define(arg, self.stack.pop())
        elif op is Op.STORE:
            frame.environment.assign(arg, self.stack.pop(), instruction.line, instruction.column)
        elif op is Op.POP:
            self.stack.pop()
        elif op is Op.DUP:
            self.stack.append(self.stack[-1])
        elif op is Op.UNARY:
            self.stack.append(unary_operation(arg, self.stack.pop()))
        elif op is Op.BINARY:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(binary_operation(arg, left, right))
        elif op is Op.BUILD_LIST:
            values = self.stack[-arg:] if arg else []
            if arg:
                del self.stack[-arg:]
            self.stack.append(list(values))
        elif op is Op.GET_INDEX:
            index = self.stack.pop()
            collection = self.stack.pop()
            self.stack.append(get_index(collection, index))
        elif op is Op.SET_INDEX:
            value = self.stack.pop()
            index = self.stack.pop()
            collection = self.stack.pop()
            self.stack.append(set_index(collection, index, value))
        elif op is Op.JUMP:
            frame.ip = arg
        elif op is Op.JUMP_IF_FALSE:
            if not truthy(self.stack[-1]):
                frame.ip = arg
        elif op is Op.JUMP_IF_TRUE:
            if truthy(self.stack[-1]):
                frame.ip = arg
        elif op is Op.ENTER_SCOPE:
            frame.environment = Environment(frame.environment)
        elif op is Op.EXIT_SCOPE:
            if frame.environment.enclosing is None:
                raise ValueError("internal scope underflow")
            frame.environment = frame.environment.enclosing
        elif op is Op.ITER_INIT:
            try:
                self.stack.append(iter(self.stack.pop()))
            except TypeError as error:
                raise ValueError("for loops need an iterable value") from error
        elif op is Op.ITER_NEXT:
            iterator = self.stack[-1]
            try:
                self.stack.append(next(iterator))
            except StopIteration:
                self.stack.pop()
                frame.ip = arg
        elif op is Op.MAKE_FUNCTION:
            self.stack.append(VMFunction(arg, frame.environment))
        elif op is Op.CALL:
            self._call(arg, instruction)
        elif op is Op.RETURN:
            value = self.stack.pop()
            completed = self.frames.pop()
            del self.stack[completed.base:]
            self.stack.append(value)
            if not self.frames:
                return _HALT
        else:
            raise AssertionError(f"unhandled opcode {op}")
        return None

    def _call(self, argument_count: int, instruction: Instruction) -> None:
        arguments = self.stack[-argument_count:] if argument_count else []
        callee_index = len(self.stack) - argument_count - 1
        callee = self.stack[callee_index]
        del self.stack[callee_index:]
        if isinstance(callee, VMFunction):
            if argument_count != callee.arity:
                raise RuntimeSprigError(
                    f"expected {callee.arity} arguments but got {argument_count}",
                    line=instruction.line,
                    column=instruction.column,
                )
            environment = Environment(callee.closure)
            for name, value in zip(callee.code.parameters, arguments):
                environment.define(name, value)
            self.frames.append(Frame(callee.code, environment, len(self.stack)))
            return
        if isinstance(callee, NativeFunction):
            if callee.arity is not None and argument_count != callee.arity:
                raise RuntimeSprigError(
                    f"expected {callee.arity} arguments but got {argument_count}",
                    line=instruction.line,
                    column=instruction.column,
                )
            try:
                self.stack.append(callee.call(list(arguments)))
            except (TypeError, ValueError) as error:
                raise RuntimeSprigError(str(error), line=instruction.line, column=instruction.column) from error
            return
        raise RuntimeSprigError("only functions can be called", line=instruction.line, column=instruction.column)


_HALT = object()
