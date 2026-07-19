from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import cleanup_superseded_artifacts as cleanup


class CleanupSafetyTests(unittest.TestCase):
    def test_hash_guard_and_identical_retained_copy_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "duplicate.bin"
            retained = root / "canonical.bin"
            target.write_bytes(b"same")
            retained.write_bytes(b"same")
            expected = hashlib.sha256(b"same").hexdigest()
            item = cleanup.CleanupTarget(
                "duplicate.bin",
                "test duplicate",
                "canonical.bin",
                expected,
                True,
            )
            with patch.object(cleanup, "ROOT", root), patch.object(cleanup, "TARGETS", (item,)):
                rows, present = cleanup.inventory()
        self.assertEqual(present, [item])
        self.assertEqual(rows[0]["sha256"], expected)

    def test_hash_guard_refuses_changed_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "duplicate.bin").write_bytes(b"changed")
            (root / "canonical.bin").write_bytes(b"original")
            item = cleanup.CleanupTarget(
                "duplicate.bin",
                "test duplicate",
                "canonical.bin",
                hashlib.sha256(b"original").hexdigest(),
            )
            with patch.object(cleanup, "ROOT", root), patch.object(cleanup, "TARGETS", (item,)):
                with self.assertRaisesRegex(ValueError, "target hash changed"):
                    cleanup.inventory()

    def test_identical_guard_refuses_different_retained_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "duplicate.bin").write_bytes(b"duplicate")
            (root / "canonical.bin").write_bytes(b"different")
            item = cleanup.CleanupTarget(
                "duplicate.bin",
                "test duplicate",
                "canonical.bin",
                hashlib.sha256(b"duplicate").hexdigest(),
                True,
            )
            with patch.object(cleanup, "ROOT", root), patch.object(cleanup, "TARGETS", (item,)):
                with self.assertRaisesRegex(ValueError, "retained duplicate differs"):
                    cleanup.inventory()

    def test_identical_directory_guard_compares_relative_file_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "duplicate"
            retained = root / "canonical"
            (target / "nested").mkdir(parents=True)
            (retained / "nested").mkdir(parents=True)
            (target / "nested/result.csv").write_bytes(b"same result")
            (retained / "nested/result.csv").write_bytes(b"same result")
            item = cleanup.CleanupTarget(
                "duplicate", "test directory duplicate", "canonical", retained_must_match=True
            )
            with patch.object(cleanup, "ROOT", root), patch.object(cleanup, "TARGETS", (item,)):
                rows, present = cleanup.inventory()
        self.assertEqual(present, [item])
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
