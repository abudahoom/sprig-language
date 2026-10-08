from __future__ import annotations

import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def test_module_cli(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "spriglang", "-c", 'print("hello", 2 + 3)'],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "hello 5\n")

    def test_bad_program_has_nonzero_exit(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "spriglang", "-c", "print(nope)"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("undefined variable 'nope'", result.stderr)


if __name__ == "__main__":
    unittest.main()

