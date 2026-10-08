# Sprig

Sprig is a small, beginner-friendly programming language implemented in Python.
It is designed to feel about as approachable as Python while exposing a little
more of the structure that most languages use: variables begin with `let`, and
blocks use braces. Sprig is a learning language, not a production language.

This repository is a complete implementation, not a syntax sketch. Source code
passes through a hand-written lexer, recursive-descent parser, typed AST, and
then either:

1. a tree-walk interpreter, or
2. a bytecode compiler and stack-based virtual machine.

The bytecode engine is the default. Both engines implement the same language.

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
| `bytecode.py` | Opcodes, instructions, code objects, disassembler |
| `vm.py` | Stack VM, call frames, iteration, and lexical closures |
| `runtime.py` | Environments, built-ins, values, shared operations |
| `api.py` | Small embedding API |
| `cli.py` | File runner, REPL, and inspection commands |

For a deeper walkthrough, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Errors

Lexer, parser, and runtime errors include a filename, line, column, offending
source line, and caret:

```text
broken.sprig:1:7: runtime error: undefined variable 'answer'
  print(answer)
        ^
```

The CLI returns exit code `0` on success, `1` for a Sprig program error, and `2`
for command-line or file-reading errors.

## Tests

```sh
python3 -m unittest discover -v
```

The tests run programs through both engines, checking arithmetic, parsing,
lists, control flow, recursion, closures, short-circuiting, built-ins, CLI exit
codes, bytecode generation, and diagnostic messages.

## Embedding Sprig in Python

```python
from spriglang import compile_source, parse_source, run_source

lines = []
run_source('print("hello")', engine="vm", output=lines.append)
assert lines == ["hello"]

program = parse_source("let x = 1 + 2")
bytecode = compile_source("let x = 1 + 2")
print(bytecode.disassemble())
```

## Intentional limits

Sprig stays small enough to understand. It does not include classes, modules,
async work, static type checking, file I/O, a package manager, or optimizer.
Those are natural extension projects, but leaving them out keeps the complete
implementation readable from end to end.

Released under the MIT License.

