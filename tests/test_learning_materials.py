from __future__ import annotations

import unittest
from pathlib import Path

from spriglang import run_source


ROOT = Path(__file__).parent.parent


class LearningMaterialTests(unittest.TestCase):
    def test_every_lesson_runs_in_both_engines(self) -> None:
        lesson_files = sorted((ROOT / "learn").glob("*.sprig"))
        self.assertGreaterEqual(len(lesson_files), 10)

        for path in lesson_files:
            source = path.read_text(encoding="utf-8")
            for engine in ("tree", "vm"):
                with self.subTest(lesson=path.name, engine=engine):
                    output: list[str] = []
                    run_source(source, engine=engine, filename=str(path), output=output.append)
                    self.assertTrue(output, f"{path.name} should show the learner something")


if __name__ == "__main__":
    unittest.main()

