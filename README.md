# Sprig

Sprig is a small, beginner-friendly programming language implemented in Python.
It is designed to feel about as approachable as Python while exposing a little
more of the structure that most languages use: variables begin with `let`, and
blocks use braces. Sprig is a learning language, not a production language.

This repository is a complete implementation, not a syntax sketch. Source code
passes through a hand-written lexer, recursive-descent parser, typed AST, and
then one of:

1. a tree-walk interpreter, or
2. a bytecode compiler and stack-based virtual machine, or
3. a source-to-source compiler that builds standalone Python files.

The bytecode engine remains the default. Python builds use the same syntax,
AST, lexical environments, built-ins, and value operations.

## Try it

Sprig requires Python 3.9 or newer and has no third-party runtime dependencies.

```sh
python3 -m spriglang examples/hello.sprig
python3 -m spriglang examples/fibonacci.sprig
```

Run with the tree-walk interpreter instead:

```sh
python3 -m spriglang --engine tree examples/fibonacci.sprig
```

Run a short program directly:

```sh
python3 -m spriglang -c 'print("Hello from Sprig!")'
```

Or install the `sprig` command from this directory:

```sh
python3 -m pip install .
sprig examples/fizzbuzz.sprig
```

## Build a Python program

From the repository directory, compile an existing Sprig file:

```sh
python -m spriglang build examples/hello.sprig -o build/hello.py
python build/hello.py
```

If you installed the command, use `sprig build examples/hello.sprig -o build/hello.py`.
Without `-o`, the output is a `.py` file beside the input. Parent output folders
are created automatically. Building checks the program and writes Python; it
does not run the program. Failed builds preserve any previous output, and the
source file cannot be used as the output path.

The generated file runs with Python 3.9+ and the standard library alone. It
contains Python functions, loops, and conditions plus an embedded copy of
Sprig's shared runtime. No Sprig installation or original `.sprig` file is
needed to run it. See [the Python compiler guide](docs/PYTHON_COMPILER.md) for
semantic checks, errors, and implementation details.

## Learn Sprig

New to programming languages? Follow the free, self-paced
[Learn Sprig course](docs/LEARN_SPRIG.md). It explains what to write, why it
works, what to change, and what to build next. Every chapter has a runnable
program in the [`learn/`](learn/) folder.

Start here:

```sh
python3 -m spriglang learn/01_hello.sprig
```

Then work through the numbered files. When you are ready to write something of
your own, copy [`learn/08_mini_project.sprig`](learn/08_mini_project.sprig) and
replace its sample scores with your own data. The course ends with exercises
and complete solutions.

## A quick tour

```sprig
# Variables use `let`. Later assignments do not.
let greeting = "Hello"
let names = ["Ada", "Grace", "Linus"]
names[2] = "Guido"

fn welcome(name) {
    return greeting + ", " + name + "!"
}

for name in names {
    if len(name) > 4 {
        print(welcome(name))
    } else {
        print("Hi, " + name + "!")
    }
}
```

Newlines end statements. A semicolon can be used when putting multiple
statements on one line. Braces make block boundaries explicit, so indentation
is for readability rather than meaning.

## Language guide

### Values

Sprig has these value kinds:

- numbers: `10`, `-3`, `2.5`
- strings: `"hello"` or `'hello'`
- booleans: `true`, `false`
- the empty value: `none`
- lists: `[1, "two", true]`
- functions, including closures

Strings recognize `\n`, `\t`, `\r`, `\\`, `\"`, and `\'` escapes. Comments
start with `#` or `//` and continue to the end of the line.

### Variables and assignment

```sprig
let score = 10
score = score + 5

let colors = ["red", "green"]
colors[0] = "blue"
```

`let` creates a variable in the current lexical scope. Assignment updates the
nearest existing variable. Using or assigning an undefined name is an error.

### Operators

From tighter to looser precedence:

| Category | Operators |
| --- | --- |
| Unary | `not`, `!`, unary `-`, unary `+` |
| Multiply | `*`, `/`, `%` |
| Add | `+`, `-` |
| Compare | `<`, `<=`, `>`, `>=` |
| Equality | `==`, `!=` |
| Logic | `and`, `or` |
| Assignment | `=` |

`and` and `or` short-circuit and return one of their operands. `+` works with
two numbers, two strings, or two lists. Other mixed-type arithmetic is rejected
with a source-located error.

### Conditions and loops

```sprig
if temperature > 30 {
    print("hot")
} else if temperature < 10 {
    print("cold")
} else {
    print("comfortable")
}

let countdown = 3
while countdown > 0 {
    print(countdown)
    countdown = countdown - 1
}

for number in range(1, 5) {
    print(number)
}
```

`false`, `none`, zero, empty strings, and empty lists are false-like. Other
values are true-like.

### Functions and closures

```sprig
fn power(base, exponent) {
    let result = 1
    while exponent > 0 {
        result = result * base
        exponent = exponent - 1
    }
    return result
}

print(power(2, 8))
```

Functions are values, may be nested, and remember variables from the scope in
which they were created. See `examples/closures.sprig` for a working counter.
A function without an explicit `return` returns `none`.

### Built-in functions

| Function | Purpose | Example result |
| --- | --- | --- |
| `print(values...)` | Print values separated by spaces | `print("x", 3)` |
| `len(value)` | Length of a string or list | `len([1, 2])` → `2` |
| `range(stop)` | Integers from zero to `stop - 1` | `range(3)` → `[0, 1, 2]` |
| `range(start, stop, step)` | Integer sequence | `range(2, 7, 2)` → `[2, 4, 6]` |
| `str(value)` | Friendly string conversion | `str(true)` → `"true"` |
| `number(value)` | Convert a numeric string | `number("2.5")` → `2.5` |
| `type(value)` | Return a value's type name | `type([])` → `"list"` |

## Inspect the implementation

The CLI can show every important stage:

```sh
# Lexer output
python3 -m spriglang --tokens examples/hello.sprig

# Typed dataclass AST
python3 -m spriglang --ast examples/hello.sprig

# Recursive bytecode disassembly
python3 -m spriglang --bytecode examples/closures.sprig
```

The implementation is divided by responsibility:

| File | Responsibility |
| --- | --- |
| `lexer.py` | Converts characters to tokens and tracks source positions |
| `parser.py` | Recursive-descent/precedence parser |
| `ast_nodes.py` | Typed, immutable AST dataclasses |
| `interpreter.py` | Direct tree-walk execution |
| `compiler.py` | AST-to-bytecode compiler with jump patching |
| `semantics.py` | Conservative name and call checks for Python builds |
| `python_compiler.py` | AST-to-Python source compiler |
| `python_runtime.py` | Compiled-function adapters embedded in Python builds |
| `bytecode.py` | Opcodes, instructions, code objects, disassembler |
| `vm.py` | Stack VM, call frames, iteration, and lexical closures |
| `runtime.py` | Environments, built-ins, values, shared operations |
| `api.py` | Small embedding API |
| `cli.py` | File runner, REPL, and inspection commands |

For a deeper walkthrough, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Errors

Lexer, parser, semantic, and runtime errors include a filename, line, column, offending
source line, and caret:

```text
broken.sprig:1:7: runtime error: undefined variable 'answer'
  print(answer)
        ^
```

The CLI returns exit code `0` on success, `1` for a Sprig program error, and `2`
for command-line or file errors. Generated Python programs also return `1` for
Sprig runtime errors, with the original Sprig filename, source line, and caret.

## Tests

```sh
python3 -m unittest discover -v
```

The tests compare all examples and lessons across the interpreter, VM, and
Python backend. They also check semantic errors, evaluation order, standalone
execution without Sprig installed, CLI builds, atomic output writes, and
diagnostic messages, alongside the existing language tests.

## Embedding Sprig in Python

```python
from spriglang import compile_python, compile_source, parse_source, run_source

lines = []
run_source('print("hello")', engine="vm", output=lines.append)
assert lines == ["hello"]

program = parse_source("let x = 1 + 2")
bytecode = compile_source("let x = 1 + 2")
print(bytecode.disassemble())

python_source = compile_python('print("hello")', filename="hello.sprig")
# Save python_source to a .py file and run it with Python.
```

## Intentional limits

Sprig stays small enough to understand. It does not include classes, modules,
async work, static type checking, file I/O, a package manager, or optimizer.
Those are natural extension projects, but leaving them out keeps the complete
implementation readable from end to end.

Released under the MIT License.
