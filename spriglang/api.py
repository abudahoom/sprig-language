from __future__ import annotations

from typing import Any, Callable, Literal

from .ast_nodes import Program
from .bytecode import CodeObject
from .compiler import Compiler
from .errors import SprigError, enrich_error
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser
from .python_compiler import PythonCompiler
from .vm import VirtualMachine

Engine = Literal["vm", "tree"]


def parse_source(source: str, filename: str = "<source>") -> Program:
    """Lex and parse source code into a typed Sprig AST."""
    tokens = Lexer(source, filename).scan_tokens()
    return Parser(tokens, source, filename).parse()


def compile_source(source: str, filename: str = "<source>") -> CodeObject:
    """Compile source code into Sprig bytecode."""
    return Compiler().compile(parse_source(source, filename), filename)


def compile_python(source: str, filename: str = "<source>") -> str:
    """Check and compile Sprig into standalone Python source code."""
    try:
        return PythonCompiler().compile(parse_source(source, filename), source, filename)
    except SprigError as error:
        raise enrich_error(error, source, filename)


def run_source(
    source: str,
    *,
    engine: Engine = "vm",
    filename: str = "<source>",
    output: Callable[[str], None] = print,
) -> Any:
    """Run Sprig source with the bytecode VM (default) or tree interpreter."""
    try:
        program = parse_source(source, filename)
        if engine == "tree":
            return Interpreter(output).interpret(program)
        if engine == "vm":
            return VirtualMachine(output).run(Compiler().compile(program, filename))
        raise ValueError(f"unknown engine {engine!r}; choose 'vm' or 'tree'")
    except SprigError as error:
        raise enrich_error(error, source, filename)

