# Building Sprig programs as Python

The Python backend reuses the existing lexer, parser, and immutable AST. The
existing bytecode compiler, VM, interpreter, REPL, and inspection commands
remain available. No language syntax has been added or changed.

## Commands

```sh
python -m spriglang build examples/fibonacci.sprig -o build/fibonacci.py
python build/fibonacci.py
python -m spriglang build --help
python -m unittest discover -v
```

Use `python3` instead of `python` on systems that use that command name.
Python 3.9 or later is required. The installed console command is equivalent:
`sprig build INPUT.sprig [-o OUTPUT.py]`.

The default destination is the input path with its extension changed to `.py`.
Builds never execute Sprig code. They complete parsing, semantic analysis, and
code generation before creating output directories or replacing the destination.
An existing output is replaced atomically after the new file has been written.
The compiler rejects outputs that resolve to the source or are hardlinks to it.

Exit codes are `0` for success, `1` for a Sprig diagnostic, and `2` for incorrect
command arguments or file errors (including invalid UTF-8).

## Compile from Python

```python
from pathlib import Path
from spriglang import compile_python, SemanticError, SprigError

source = 'fn double(n) { return n * 2 }; print(double(21))'
generated = compile_python(source, filename="example.sprig")
Path("example.py").write_text(generated, encoding="utf-8")
```

`compile_python` returns Python source text and raises `SprigError` subclasses
for source problems. `SemanticError` distinguishes build-time semantic errors.
The existing `compile_source` API still returns bytecode. The generated file
exposes `main(output=print)` for embedding; importing it does not run the Sprig
program, and each call to `main` creates fresh global state.

## Semantic checks

Python builds check undefined reads and assignments, eager reads before a
declaration, and block or loop variables used outside their scope. They also
check argument counts for direct calls to functions or fixed-arity built-ins
whose bindings are known to be stable, and reject calling literal values.
The existing parser continues to reject invalid assignment targets and
`return` outside a function.

```text
broken.sprig:1:7: semantic error: undefined variable 'answer'
  print(answer)
        ^
```

Sprig is dynamically typed. Names can be shadowed or reassigned, functions are
values, and closures observe their captured environment as it changes. The
checker therefore allows references to later declarations in enclosing scopes
of a function. It leaves calls through aliases, parameters, and potentially
rebound functions to runtime checks. It does not reject same-scope
redeclarations or duplicate parameters that the existing implementation accepts.

Unresolved names in function bodies are checked even if the function is never
called. Expressions skipped by a literal short-circuit condition, literal dead
branches, and statements after a direct return are not checked. For example,
`false and missing` remains valid. This is conservative analysis, not a proof
that a program will run successfully: it does not infer arbitrary values or
function effects, or prove reachability for computed conditions. Calling a
closure before a required later declaration still fails at runtime.

## How generated code preserves Sprig behavior

Statements become Python functions, `if`, `while`, `for`, and `return`.
There is no embedded parser, tree interpreter, bytecode VM, `eval`, or `exec`.
The original Sprig text is stored only to display error excerpts.

Sprig names live in the existing `Environment` implementation rather than
Python local variables. This preserves block scope, assignment to the nearest
binding, late-bound closures, and a separate environment for each loop
iteration. Python keywords and runtime helper names remain valid Sprig names.

Arithmetic, indexing, truthiness, output formatting, and built-ins use the
actual shared runtime source embedded during compilation. There are no runtime
imports from `spriglang` and no third-party dependencies. String and filename
literals are quoted safely. Build output is deterministic for the same source,
filename, and compiler version.

Arguments and binary operands evaluate left to right, once each. Indexed
assignment evaluates the collection, index, then value, matching the default
VM. A small interpreter fix aligns its previous right-hand-side-first behavior
with this order; a regression test checks observable side effects across all
three backends. Short-circuit operators return the selected operand.

Errors in generated code retain the original Sprig location, including inside
nested functions, and the command-line runner prints a diagnostic without a
Python traceback. Value types, indexing bounds, dynamic argument counts, and
division by zero are checked at runtime.

## Limits

The compiler is a Python source target, not a native executable generator or
optimizer. Generated programs require Python. They use Python's call stack,
so deep recursion is limited; the bytecode VM remains useful for programs that
need its explicit frame stack. Static analysis does not add static types.

One pre-existing backend difference remains: `type(user_function)` in the VM
reports `VMFunction`, while the interpreter and Python backend return the
documented `function`. This change does not alter the VM's type reporting.

The generated file includes Sprig runtime code and its MIT license notice.
Keep that notice when redistributing builds.
