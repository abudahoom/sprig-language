from __future__ import annotations

import unittest

from spriglang import SprigError, compile_source, parse_source, run_source
from spriglang.ast_nodes import FunctionStmt, LetStmt
from spriglang.lexer import Lexer
from spriglang.tokens import TokenType
from tests.python_support import run_python


class LanguageTests(unittest.TestCase):
    def run_program(self, source: str, engine: str) -> list[str]:
        output: list[str] = []
        run_source(source, engine=engine, output=output.append)
        return output

    def assert_engines(self, source: str, expected: list[str]) -> None:
        for engine in ("tree", "vm"):
            with self.subTest(engine=engine):
                self.assertEqual(self.run_program(source, engine), expected)
        with self.subTest(engine="python"):
            self.assertEqual(run_python(source), expected)

    def test_lexer_handles_literals_comments_and_keywords(self) -> None:
        tokens = Lexer('let answer = 41 + 1 # yes\nprint("ok")\n').scan_tokens()
        types = [token.type for token in tokens]
        self.assertIn(TokenType.LET, types)
        self.assertIn(TokenType.NUMBER, types)
        self.assertIn(TokenType.STRING, types)
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_parser_builds_typed_ast(self) -> None:
        program = parse_source("let x = 3\nfn twice(n) { return n * 2 }\n")
        self.assertIsInstance(program[0], LetStmt)
        self.assertIsInstance(program[1], FunctionStmt)
        self.assertEqual(program[1].parameters, ("n",))

    def test_arithmetic_variables_and_strings(self) -> None:
        self.assert_engines(
            'let x = 4\nx = x * 3 + 1\nprint("answer", x)\n',
            ["answer 13"],
        )

    def test_control_flow_and_lists(self) -> None:
        self.assert_engines(
            """
let values = [1, 2, 3, 4]
let total = 0
for value in values {
    if value % 2 == 0 {
        total = total + value
    }
}
values[0] = total
print(values, values[0])
""",
            ["[6, 2, 3, 4] 6"],
        )

    def test_recursion(self) -> None:
        self.assert_engines(
            """
fn fact(n) {
    if n <= 1 { return 1 }
    return n * fact(n - 1)
}
print(fact(6))
""",
            ["720"],
        )

    def test_closures_and_short_circuiting(self) -> None:
        self.assert_engines(
            """
fn counter(start) {
    let n = start
    fn next() { n = n + 1; return n }
    return next
}
let c = counter(2)
print(c(), c(), false and missing, true or missing)
""",
            ["3 4 false true"],
        )

    def test_while_and_builtins(self) -> None:
        self.assert_engines(
            "let n = 3\nwhile n > 0 { print(str(n)); n = n - 1 }\nprint(type(n))\n",
            ["3", "2", "1", "number"],
        )

    def test_bytecode_is_real_and_inspectable(self) -> None:
        text = compile_source("let x = 1 + 2\nprint(x)\n").disassemble()
        self.assertIn("BINARY '+'", text)
        self.assertIn("CALL 1", text)
        self.assertIn("RETURN", text)

    def test_meaningful_parse_error(self) -> None:
        with self.assertRaises(SprigError) as caught:
            run_source("let = 3\n", filename="broken.sprig")
        text = str(caught.exception)
        self.assertIn("broken.sprig:1:5", text)
        self.assertIn("expected a variable name", text)
        self.assertIn("^", text)

    def test_meaningful_runtime_error_in_both_engines(self) -> None:
        for engine in ("tree", "vm"):
            with self.subTest(engine=engine):
                with self.assertRaises(SprigError) as caught:
                    run_source("print(10 / 0)\n", engine=engine, filename="oops.sprig")
                self.assertIn("division by zero", str(caught.exception))
                self.assertIn("oops.sprig:1", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

