from __future__ import annotations

import argparse
import os
import pprint
import sys
import tempfile
from pathlib import Path

from .api import compile_python, compile_source, parse_source, run_source
from .compiler import Compiler
from .errors import SprigError, enrich_error
from .interpreter import Interpreter
from .lexer import Lexer
from .vm import VirtualMachine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sprig",
        description="Run Sprig programs (bytecode VM by default).",
        epilog="Build standalone Python: sprig build SOURCE.sprig [-o OUTPUT.py]",
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
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "build":
        return build(argv[1:])
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


def build(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sprig build", description="Compile Sprig to standalone Python without running it.")
    parser.add_argument("file", help="Sprig source file")
    parser.add_argument("-o", "--output", help="output path (default: source path with .py extension)")
    args = parser.parse_args(argv)
    source_path = Path(args.file)
    output_path = Path(args.output) if args.output else source_path.with_suffix(".py")
    temporary: str | None = None
    try:
        if source_path.resolve() == output_path.resolve() or (
            output_path.exists() and source_path.exists() and source_path.samefile(output_path)
        ):
            print("sprig: output must be different from the source file", file=sys.stderr)
            return 2
        source = source_path.read_text(encoding="utf-8")
        python_source = compile_python(source, str(source_path))
        # Compile completely before touching the destination; replace atomically
        # so failed checks or writes cannot truncate a previous successful build.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output_path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(python_source)
        os.replace(temporary, output_path)
        temporary = None
    except SprigError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(f"sprig: could not build {source_path}: {error}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    print(f"Built {source_path} -> {output_path}")
    return 0


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
