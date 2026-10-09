# How Sprig works

Sprig has one front end, two existing execution engines, and a Python source
compiler. The existing engines follow this path:

```text
source text
    │
    ▼
  lexer ──────► tokens
                  │
                  ▼
                parser ──────► typed AST
                                  │
                        ┌─────────┴─────────┐
                        ▼                   ▼
                  tree interpreter      compiler
                                            │
                                            ▼
                                         bytecode
                                            │
                                            ▼
                                      stack-based VM
```

## Front end

The lexer scans one character at a time. Every token stores its starting line
and column, which later stages carry into AST nodes and bytecode instructions.
Newlines are tokens because Sprig uses them as statement separators.

The parser is hand-written recursive descent. Statements are parsed by grammar
functions such as `_if_statement`; expressions use one function per precedence
level, from assignment down to primary expressions. Assignment is
right-associative. Calls and indexes are postfix operations, so expressions like
`items[0]` and `make_adder(2)(3)` work naturally.

AST nodes are frozen Python dataclasses with explicit type annotations. This
makes the tree easy to inspect with `--ast` and gives both back ends a shared,
well-defined input.

## Tree-walk interpreter

The interpreter recursively visits AST nodes. An `Environment` maps names to
values and points to an optional enclosing environment. A function captures the
environment where it is declared; this is the closure that lets a nested
function keep using surrounding variables after its outer function returns.

Blocks create child environments. Assignment walks outward to update the
nearest existing binding. `return` uses a private control-flow signal that
unwinds nested interpreter visits to the current function call.

## Compiler

The compiler emits instructions for a stack machine. For example:

```sprig
let answer = 6 * 7
print(answer)
```

roughly becomes:

```text
CONSTANT 6
CONSTANT 7
BINARY '*'
DEFINE 'answer'
LOAD 'print'
LOAD 'answer'
CALL 1
POP
CONSTANT none
RETURN
```

Control flow uses absolute jump targets. The compiler first emits a jump with
an empty target, compiles the branch body, and patches the target afterward.
`and` and `or` compile to conditional jumps, preserving short-circuit behavior.

Each function is compiled into a nested `CodeObject`. `--bytecode` recursively
disassembles those objects, including source locations for every instruction.

## Virtual machine

The VM has a value stack and a stack of call frames. A frame stores a code
object, instruction pointer, stack base, and current lexical environment.

`CALL` either invokes a native built-in immediately or pushes a new frame for a
Sprig function. `RETURN` removes that frame, discards its temporary stack data,
and leaves one result for its caller. A VM function captures an `Environment`,
so closures have the same semantics in both execution engines.

The VM has dedicated iteration instructions. `ITER_INIT` converts a value into
an iterator; `ITER_NEXT` either pushes the next item or removes the exhausted
iterator and jumps past the loop body.

## Shared runtime

Both back ends use the operations in `runtime.py` for truthiness, arithmetic,
indexing, string conversion, environments, and built-ins. Centralizing those
rules prevents subtle differences between interpreted and compiled programs.

## Python source compiler

The additional path is `AST -> semantic checks -> Python source -> Python`.
`semantics.py` checks lexical visibility and stable call signatures without
changing how closures resolve names. `python_compiler.py` lowers every AST
statement and expression to Python source. Generated functions use captured
`Environment` objects; loops and conditions use native Python control flow.

The compiler embeds `errors.py`, `runtime.py`, and the small function adapters
in `python_runtime.py`, removing only package-relative and duplicate future
imports. This shares the existing value rules while producing a standalone
file. The source text and filename are embedded for diagnostics, not execution.
See [PYTHON_COMPILER.md](PYTHON_COMPILER.md) for checks, compatibility details,
and runtime limits.

## Extending Sprig

A typical new feature touches these areas in order:

1. add token kinds and lexer rules if new syntax is needed;
2. add typed AST nodes;
3. parse the new construct;
4. implement it in the tree interpreter;
5. add opcodes and compiler/VM behavior when needed;
6. add tests that run through both engines;
7. document the syntax and semantics.

A useful first extension is `break` and `continue`. The compiler can maintain a
stack of current loop targets and patch jumps when each loop finishes.

