from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Op(Enum):
    CONSTANT = auto()
    LOAD = auto()
    DEFINE = auto()
    STORE = auto()
    POP = auto()
    DUP = auto()
    UNARY = auto()
    BINARY = auto()
    BUILD_LIST = auto()
    GET_INDEX = auto()
    SET_INDEX = auto()
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    JUMP_IF_TRUE = auto()
    ENTER_SCOPE = auto()
    EXIT_SCOPE = auto()
    ITER_INIT = auto()
    ITER_NEXT = auto()
    MAKE_FUNCTION = auto()
    CALL = auto()
    RETURN = auto()


@dataclass
class Instruction:
    op: Op
    arg: Any = None
    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        if self.arg is None:
            return self.op.name
        if isinstance(self.arg, CodeObject):
            return f"{self.op.name} <code {self.arg.name}>"
        return f"{self.op.name} {self.arg!r}"


@dataclass
class CodeObject:
    name: str
    parameters: tuple[str, ...] = ()
    instructions: list[Instruction] = field(default_factory=list)

    def disassemble(self, recursive: bool = True) -> str:
        lines = [f"== {self.name}({', '.join(self.parameters)}) =="]
        nested: list[CodeObject] = []
        for index, instruction in enumerate(self.instructions):
            lines.append(f"{index:04d}  {instruction.line:>3}:{instruction.column:<3}  {instruction}")
            if isinstance(instruction.arg, CodeObject):
                nested.append(instruction.arg)
        if recursive:
            for code in nested:
                lines.extend(("", code.disassemble(recursive=True)))
        return "\n".join(lines)
