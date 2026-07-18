from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import deduplicate_pferi_v2_work_images as dedup
from scripts import materialize_pferi_v2_work_images as materialize


class PFERIWorkImageDedupTests(unittest.TestCase):
    def test_materializer_cli_is_directly_runnable(self) -> None:
        script = Path(materialize.__file__).resolve()
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=script.parents[1],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Restore deduplicated PF-ERI v2 work images", result.stdout)

    def test_unique_canonical_hash_can_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / "data/frozen/pferi_v2/lynx-wild/images/a.jpg"
            work = root / "work/pferi_v2/package/images/asset.jpg"
            frozen.parent.mkdir(parents=True)
            work.parent.mkdir(parents=True)
            frozen.write_bytes(b"same-image")
            work.write_bytes(b"same-image")

            rows = dedup.find_duplicates(root)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].work_path, "work/pferi_v2/package/images/asset.jpg")
            dedup.apply_duplicates(root, rows)
            self.assertFalse(work.exists())
            materialize.restore_rows(root, rows, apply=True)
            self.assertEqual(work.read_bytes(), frozen.read_bytes())

    def test_ambiguous_cross_label_canonical_hash_is_not_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for scope in ("bobcat-urban", "bobcat-wild"):
                path = root / f"data/frozen/pferi_v2/{scope}/images/{scope}.jpg"
                path.parent.mkdir(parents=True)
                path.write_bytes(b"ambiguous-image")
            work = root / "work/pferi_v2/package/images/asset.jpg"
            work.parent.mkdir(parents=True)
            work.write_bytes(b"ambiguous-image")

            rows = dedup.find_duplicates(root)

            self.assertEqual(rows, [])
            self.assertTrue(work.exists())

    def test_manifest_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.csv"
            row = dedup.Duplicate(
                work_path="work/pferi_v2/a.jpg",
                canonical_path="data/frozen/pferi_v2/a.jpg",
                size_bytes=3,
                sha256="0" * 64,
            )

            dedup.write_manifest(path, [row])
            loaded = materialize.read_manifest(path)

            self.assertEqual(loaded, [row])
            with path.open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 1)


if __name__ == "__main__":
    unittest.main()
