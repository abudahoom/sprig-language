from __future__ import annotations

import unittest

from spriglang import SemanticError, SprigError, compile_python
from tests.python_support import run_python


class SemanticTests(unittest.TestCase):
    def assert_error(self, source: str, message: str) -> None:
        with self.assertRaises(SemanticError) as caught:
            compile_python(source, 'broken.sprig')
        text = str(caught.exception)
        self.assertIn('broken.sprig:', text)
        self.assertIn('semantic error:', text)
        self.assertIn(message, text)
        self.assertIn('^', text)

    def test_undefined_read_has_exact_source_location(self) -> None:
        self.assert_error('print(missing)', "broken.sprig:1:7: semantic error: undefined variable 'missing'")

    def test_undefined_assignment(self) -> None:
        self.assert_error('missing = 1', "cannot assign to undefined variable 'missing'")

    def test_eager_forward_read_and_self_initializer(self) -> None:
        for source in ('print(x); let x = 1', 'let x = x', 'fn f() { let x = x }; f()'):
            with self.subTest(source=source):
                self.assert_error(source, "undefined variable 'x'")

    def test_block_and_loop_bindings_do_not_leak(self) -> None:
        for source in ('{ let x = 1 }; print(x)', 'for x in [1] {}; print(x)', 'if true { let x = 1 }; print(x)'):
            with self.subTest(source=source):
                self.assert_error(source, "undefined variable 'x'")

    def test_unresolved_function_body_reference(self) -> None:
        self.assert_error('fn f() { return missing }', "undefined variable 'missing'")

    def test_static_function_and_builtin_arity(self) -> None:
        for source in ('fn f(a) {}; f()', 'len()', 'fn outer() { fn f(a) {}; f() }; outer()'):
            with self.subTest(source=source):
                self.assert_error(source, 'expected 1 arguments but got 0')

    def test_literal_cannot_be_called(self) -> None:
        for source in ('3()', '"hello"()', '[1]()'):
            with self.subTest(source=source):
                self.assert_error(source, 'only functions can be called')

    def test_constant_dead_branches_and_short_circuit_remain_valid(self) -> None:
        source = '''
if false { print(missing) } else { print("ok") }
while false { missing() }
for n in [] { missing() }
print(false and missing, true or missing, [] and missing, !false or missing)
fn f() { return 1; print(missing) }
print(f())
'''
        self.assertEqual(run_python(source), ['ok', 'false true [] true', '1'])

    def test_outer_read_before_local_declaration(self) -> None:
        source = 'let x = 1; fn f() { print(x); let x = 2; print(x) }; f()'
        self.assertEqual(run_python(source), ['1', '2'])

    def test_deferred_closure_checks_do_not_hoist_runtime_bindings(self) -> None:
        source = 'fn f() { return x }; let x = 3; print(f())'
        self.assertEqual(run_python(source), ['3'])

    def test_rebound_functions_and_builtins_have_runtime_arity(self) -> None:
        source = '''
fn noargs() { return 7 }
fn replace() { len = noargs }
replace()
print(len())
fn f(a) { return a }; f = noargs; print(f())
fn apply(f) { return f() }; print(apply(noargs))
'''
        self.assertEqual(run_python(source), ['7', '7', '7'])

    def test_existing_syntax_errors_are_preserved(self) -> None:
        for source, message in [('let = 1', 'expected a variable name'), ('return 1', "'return' can only"), ('1 = 2', 'assignment target'), ('@', 'unexpected character')]:
            with self.subTest(source=source):
                with self.assertRaises(SprigError) as caught:
                    compile_python(source, 'syntax.sprig')
                self.assertIn('syntax.sprig:', str(caught.exception))
                self.assertIn(message, str(caught.exception))


if __name__ == '__main__':
    unittest.main()
