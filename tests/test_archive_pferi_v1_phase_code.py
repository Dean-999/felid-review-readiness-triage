from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import archive_pferi_v1_phase_code as archive


class ArchivePFERIV1PhaseCodeTests(unittest.TestCase):
    def test_selects_phase_7_through_17_but_not_phase_18_or_v2_schema_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            for name in (
                "build_phase7_example.py",
                "build_phase17a_example.py",
                "build_phase18_example.py",
                "build_v2_example.py",
            ):
                (root / "scripts" / name).write_text("# source\n", encoding="utf-8")
            (root / "tests/test_phase17.py").write_text(
                "from scripts.build_phase17a_example import build\n", encoding="utf-8"
            )
            (root / "tests/test_package_phase16e2.py").write_text(
                "# dynamically loads a historical file path\n", encoding="utf-8"
            )

            plan = archive.build_plan(root)
            sources = {move.source.name for move in plan}

            self.assertEqual(
                sources,
                {
                    "build_phase7_example.py",
                    "build_phase17a_example.py",
                    "test_phase17.py",
                    "test_package_phase16e2.py",
                },
            )

    def test_build_plan_refuses_an_existing_archive_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts/build_phase14_example.py").write_text("# source\n", encoding="utf-8")
            destination = root / "archive/pferi_v1/reproducibility/scripts/build_phase14_example.py"
            destination.parent.mkdir(parents=True)
            destination.write_text("# collision\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                archive.build_plan(root)


if __name__ == "__main__":
    unittest.main()
