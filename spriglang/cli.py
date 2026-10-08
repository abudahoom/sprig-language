from __future__ import annotations

import argparse
import pprint
import sys
from pathlib import Path

from .api import compile_source, parse_source, run_source
from .compiler import Compiler
from .errors import SprigError, enrich_error
from .interpreter import Interpreter
from .lexer import Lexer
from .vm import VirtualMachine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sprig",
        description="Run Sprig programs (bytecode VM by default).",
    )
    parser.add_argument("file", nargs="?", help="a .sprig source file; omit for the REPL")
    parser.add_argument("-c", "--code", help="run a source string instead of a file")
    parser.add_argument(
        "--engine",
        choices=("vm", "tree"),
        default="vm",
        help="execution engine (default: vm)",
    )
    inspect = parser.add_mutually_exclusive_group()
    inspect.add_argument("--tokens", action="store_true", help="print lexer tokens without running")
    inspect.add_argument("--ast", action="store_true", help="print the typed AST without running")
    inspect.add_argument("--bytecode", action="store_true", help="disassemble bytecode without running")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.code is not None and args.file is not None:
        print("sprig: choose either a file or --code, not both", file=sys.stderr)
        return 2
    if args.code is None and args.file is None:
        return repl(args.engine)

    if args.code is not None:
        source, filename = args.code, "<command>"
    else:
        path = Path(args.file)
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"sprig: could not read {path}: {error}", file=sys.stderr)
            return 2
        filename = str(path)

    try:
        if args.tokens:
            for token in Lexer(source, filename).scan_tokens():
                print(token)
        elif args.ast:
            pprint.pp(parse_source(source, filename), sort_dicts=False)
        elif args.bytecode:
            print(compile_source(source, filename).disassemble())
        else:
            run_source(source, engine=args.engine, filename=filename)
        return 0
    except SprigError as error:
        print(error, file=sys.stderr)
        return 1


def repl(engine: str = "vm") -> int:
    print("Sprig 1.0 — type expressions or statements; Ctrl-D to leave")
    runner = Interpreter() if engine == "tree" else VirtualMachine()
    while True:
        try:
            source = input("sprig> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not source.strip():
            continue
        try:
            source += "\n"
            program = parse_source(source, "<repl>")
            if isinstance(runner, Interpreter):
                runner.interpret(program)
            else:
                runner.run(Compiler().compile(program, "<repl>"))
        except SprigError as error:
            print(enrich_error(error, source, "<repl>"), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
