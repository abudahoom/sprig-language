from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spriglang.cli import main


ROOT = Path(__file__).resolve().parent.parent


class BuildCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'hello world.sprig'
        self.source.write_text('print("hello", 2 + 3)', encoding='utf-8')

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, '-m', 'spriglang', *args], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', timeout=10,
        )

    def test_build_defaults_to_sibling_python_file(self) -> None:
        result = self.cli('build', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Built ', result.stdout)
        self.assertNotIn('hello 5', result.stdout)
        output = self.source.with_suffix('.py')
        self.assertTrue(output.is_file())
        run = subprocess.run([sys.executable, '-I', str(output)], cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, 'hello 5\n')

    def test_output_flag_creates_parent_directories(self) -> None:
        output = self.root / 'new folder' / 'nested' / 'program.py'
        result = self.cli('build', str(self.source), '-o', str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())

    def test_semantic_failure_keeps_previous_build(self) -> None:
        output = self.root / 'program.py'
        output.write_text('previous successful build', encoding='utf-8')
        self.source.write_text('print(missing)', encoding='utf-8')
        result = self.cli('build', str(self.source), '-o', str(output))
        self.assertEqual(result.returncode, 1)
        self.assertIn('semantic error', result.stderr)
        self.assertIn(':1:7:', result.stderr)
        self.assertIn('^', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(output.read_text(encoding='utf-8'), 'previous successful build')

    def test_syntax_failure_creates_no_output(self) -> None:
        self.source.write_text('let = 1', encoding='utf-8')
        output = self.root / 'new' / 'program.py'
        result = self.cli('build', str(self.source), '-o', str(output))
        self.assertEqual(result.returncode, 1)
        self.assertIn('parse error', result.stderr)
        self.assertFalse(output.parent.exists())

    def test_source_cannot_be_overwritten(self) -> None:
        before = self.source.read_bytes()
        result = self.cli('build', str(self.source), '-o', str(self.source))
        self.assertEqual(result.returncode, 2)
        self.assertIn('different from the source', result.stderr)
        self.assertEqual(self.source.read_bytes(), before)

    def test_source_with_python_suffix_is_protected(self) -> None:
        source = self.source.with_suffix('.py')
        source.write_text('print(42)', encoding='utf-8')
        result = self.cli('build', str(source))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(source.read_text(encoding='utf-8'), 'print(42)')

    def test_hardlink_to_source_is_protected(self) -> None:
        output = self.root / 'alias.py'
        try:
            os.link(self.source, output)
        except OSError as error:
            self.skipTest(f'filesystem does not support hardlinks: {error}')
        result = self.cli('build', str(self.source), '-o', str(output))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_bytes(), self.source.read_bytes())

    def test_missing_and_non_utf8_source_are_file_errors(self) -> None:
        for path in (self.root / 'missing.sprig', self.source):
            with self.subTest(path=path):
                if path == self.source:
                    path.write_bytes(b'\xff\xfe')
                result = self.cli('build', str(path))
                self.assertEqual(result.returncode, 2)
                self.assertIn('could not build', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_output_directory_is_reported_cleanly(self) -> None:
        result = self.cli('build', str(self.source), '-o', str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn('could not build', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_failed_atomic_replace_keeps_previous_build_and_cleans_temp(self) -> None:
        output = self.root / 'program.py'
        output.write_text('old build', encoding='utf-8')
        stderr = io.StringIO()
        with patch('spriglang.cli.os.replace', side_effect=OSError('test write failure')):
            with contextlib.redirect_stderr(stderr):
                code = main(['build', str(self.source), '-o', str(output)])
        self.assertEqual(code, 2)
        self.assertIn('test write failure', stderr.getvalue())
        self.assertEqual(output.read_text(encoding='utf-8'), 'old build')
        self.assertEqual(set(self.root.iterdir()), {self.source, output})

    def test_help_and_invalid_arguments(self) -> None:
        result = self.cli('build', '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('standalone Python', result.stdout)
        self.assertEqual(self.cli('build').returncode, 2)
        self.assertEqual(self.cli('build', str(self.source), '--engine', 'tree').returncode, 2)

    def test_existing_run_and_inspection_flags_still_work(self) -> None:
        for flag, expected in [('--tokens', 'print'), ('--ast', 'Call'), ('--bytecode', 'CALL')]:
            with self.subTest(flag=flag):
                result = self.cli(flag, str(self.source))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
        result = self.cli('--engine', 'tree', str(self.source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'hello 5\n')


if __name__ == '__main__':
    unittest.main()
