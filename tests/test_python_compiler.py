from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from spriglang import compile_python, run_source
from tests.python_support import run_python


ROOT = Path(__file__).resolve().parent.parent


class PythonCompilerTests(unittest.TestCase):
    def assert_program(self, source: str, expected: list[str]) -> None:
        self.assertEqual(run_python(source), expected)
        for engine in ("tree", "vm"):
            with self.subTest(engine=engine):
                output: list[str] = []
                run_source(source, engine=engine, output=output.append)
                self.assertEqual(output, expected)

    def standalone(self, source: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.py"
            path.write_text(compile_python(source, "original.sprig"), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-I", str(path)], cwd=directory,
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )

    def test_all_examples_and_lessons_match_both_engines(self) -> None:
        files = sorted((ROOT / "examples").glob("*.sprig")) + sorted((ROOT / "learn").glob("*.sprig"))
        self.assertGreaterEqual(len(files), 15)
        for path in files:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                expected: list[str] = []
                run_source(source, engine="tree", output=expected.append)
                self.assert_program(source, expected)

    def test_standalone_file_needs_no_sprig_installation(self) -> None:
        result = self.standalone('fn twice(n) { return n * 2 }; print(twice(21))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "42\n")

    def test_empty_program_and_blocks(self) -> None:
        self.assert_program('', [])
        self.assert_program('if true {} else {}; while false {}; for n in [] {}; fn empty() {}; print(empty())', ['none'])

    def test_block_shadowing_and_nearest_assignment(self) -> None:
        self.assert_program('let x = 1; { let x = x + 1; { x = x + 10 }; print(x) }; print(x)', ['12', '1'])

    def test_late_bound_closure_and_mutual_recursion(self) -> None:
        self.assert_program('''
fn even(n) { if n == 0 { return true }; return odd(n - 1) }
fn odd(n) { if n == 0 { return false }; return even(n - 1) }
fn read() { return later }
let later = 42
print(even(10), odd(10), read())
''', ['true false 42'])

    def test_closure_observes_later_declaration_in_same_scope(self) -> None:
        self.assert_program('''
let value = "outer"
{ fn read() { return value }; print(read()); let value = "inner"; print(read()) }
''', ['outer', 'inner'])

    def test_each_iteration_gets_its_own_closure(self) -> None:
        self.assert_program('''
let functions = []
for n in range(3) { fn read() { return n }; functions = functions + [read] }
let i = 0
while i < 2 { let n = i + 10; fn read() { return n }; functions = functions + [read]; i = i + 1 }
for f in functions { print(f()) }
''', ['0', '1', '2', '10', '11'])

    def test_return_inside_nested_scopes_and_loops(self) -> None:
        self.assert_program('''
fn find() { for n in range(5) { while true { { if n == 3 { return n }; return n + 10 } } }; return -1 }
fn bare() { return }
print(find(), bare())
''', ['10 none'])

    def test_assignment_expression_and_order(self) -> None:
        self.assert_program('''
let a = 0; let b = 0
print(a = b = 3, a, b)
let log = ""; let items = [0]
fn collection() { log = log + "C"; return items }
fn index() { log = log + "I"; return 0 }
fn value() { log = log + "V"; return 7 }
print(collection()[index()] = value(), items, log)
''', ['3 3 3', '7 [7] CIV'])

    def test_call_argument_order_and_single_evaluation(self) -> None:
        self.assert_program('''
let log = ""
fn arg(n) { log = log + str(n); return n }
fn sum(a, b) { return a + b }
fn callee() { log = log + "C"; return sum }
print(callee()(arg(1), arg(2)), log)
''', ['3 C12'])

    def test_short_circuit_preserves_operands_and_skips_side_effects(self) -> None:
        self.assert_program('''
let n = 0
print(false and missing, true or missing, 0 or 7, "yes" and 9)
print([] and (n = 1), [2] or (n = 2), n)
''', ['false true 7 9', '[] [2] 0'])

    def test_literals_lists_escapes_and_python_identifier_collisions(self) -> None:
        self.assert_program('''
let class = "a\\n'b\\t\\\\"; let _env = 4; let main = 5; let Environment = 6
let café = 7; let _sp_call = 8
print(class, _env + main + Environment + café + _sp_call)
let xs = [true, none, [1, 2]]; xs[-1][0] = 9
print(xs, "abc"[-1], !false, +3, -2, 5 / 2, 5 % 2)
''', ["a\n'b\t\\ 30", '[true, none, [9, 2]] c true 3 -2 2.5 1'])

    def test_redeclarations_duplicate_parameters_and_function_reassignment(self) -> None:
        self.assert_program('''
let x = 1; let x = x + 1
fn last(a, a) { return a }
fn f(a) { return a }
fn g() { return 9 }
f = g
let len = f
print(x, last(3, 4), f(), len())
''', ['2 4 9 9'])

    def test_functions_have_sprig_display_and_type(self) -> None:
        # The existing VM reports VMFunction here; the Python backend follows
        # the shared runtime's documented function type and tree interpreter.
        source = 'fn f() {}; print(f, type(f), type(print), str(f))'
        self.assertEqual(run_python(source), ['<fn f> function function <fn f>'])
        output: list[str] = []
        run_source(source, engine="tree", output=output.append)
        self.assertEqual(run_python(source), output)

    def test_runtime_diagnostics_match_original_source(self) -> None:
        cases = [
            ('print(10 / 0)', 'division by zero'),
            ('print(10 % 0)', 'remainder by zero'),
            ('print(true + 1)', "'+' needs two numbers"),
            ('print(-true)', "needs numbers"),
            ('print([1][true])', 'indexes must be integers'),
            ('print([1][5])', 'out of range'),
            ('let s = "x"; s[0] = "y"', 'only lists can be changed'),
            ('for x in 3 {}', 'for loops need an iterable'),
            ('let n = 3; n()', 'only functions can be called'),
            ('fn f(a) {}; let alias = f; alias()', 'expected 1 arguments but got 0'),
            ('print(range())', 'range expects one to three integer arguments'),
            ('print(number(true))', 'number expects a numeric value'),
            ('fn f() { return later }; f(); let later = 2', "undefined variable 'later'"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                result = self.standalone(source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('original.sprig:1:', result.stderr)
                self.assertIn('runtime error:', result.stderr)
                self.assertIn(message, result.stderr)
                self.assertIn(source, result.stderr)
                self.assertIn('^', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_nested_runtime_error_keeps_inner_location(self) -> None:
        result = self.standalone('fn f() {\n  return 1 / 0\n}\nf()\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('original.sprig:2:12:', result.stderr)

    def test_recursion_limit_has_a_sprig_diagnostic(self) -> None:
        result = self.standalone('fn recurse() { return recurse() }; recurse()')
        self.assertEqual(result.returncode, 1)
        self.assertIn('maximum function call depth exceeded', result.stderr)
        self.assertIn('original.sprig:1:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_import_has_no_side_effects_and_main_starts_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'program.py'
            path.write_text(compile_python('let n = 0; n = n + 1; print(n)'), encoding='utf-8')
            command = 'import runpy, sys; main = runpy.run_path(sys.argv[1])["main"]; print("loaded"); main(); main()'
            result = subprocess.run([sys.executable, '-I', '-c', command, str(path)], cwd=directory, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'loaded\n1\n1\n')

    def test_runtime_license_is_included(self) -> None:
        source = compile_python('')
        for line in (ROOT / 'LICENSE').read_text(encoding='utf-8').splitlines():
            if line:
                self.assertIn('# ' + line, source)

    def test_python_output_is_actual_lowered_control_flow(self) -> None:
        source = 'fn f(n) { while n > 0 { n = n - 1 }; return n }; for n in [1] { if n { print(f(n)) } }'
        text = compile_python(source)
        tree = ast.parse(text)
        nodes = list(ast.walk(tree))
        for kind in (ast.FunctionDef, ast.While, ast.For, ast.If, ast.Return):
            self.assertTrue(any(isinstance(node, kind) for node in nodes))
        self.assertFalse(any(isinstance(node, ast.ImportFrom) and node.level for node in nodes))
        for name in ('parse_source', 'run_source', 'VirtualMachine', 'Interpreter', 'eval', 'exec'):
            self.assertFalse(any(isinstance(node, ast.Name) and node.id == name for node in nodes), name)

    def test_build_does_not_run_source_and_is_deterministic(self) -> None:
        source = 'while true { print("must not run") }'
        self.assertEqual(compile_python(source), compile_python(source))

    def test_nonfinite_float_literal_emits_valid_python(self) -> None:
        self.assert_program('print(' + '9' * 400 + '.0)', ['inf'])

    def test_original_filename_is_quoted_safely(self) -> None:
        text = compile_python('print("safe")', "line\n'\\name.sprig")
        compile(text, '<generated>', 'exec')


if __name__ == '__main__':
    unittest.main()
