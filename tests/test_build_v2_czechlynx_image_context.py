from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_v2_czechlynx_image_context as context


def source_row(sha: str = "a" * 64, exists: str = "yes", decode: str = "ok") -> dict[str, str]:
    return {
        "species": "czechlynx",
        "source_identity_label": "restricted_identity",
        "decode_status": decode,
        "final_freeze_image_exists": exists,
        "final_freeze_sha256": sha,
        "final_freeze_image_path": "data/frozen/pferi_v2/lynx-wild/images/opaque.jpg",
    }


class BuildV2CzechlynxImageContextTests(unittest.TestCase):
    def test_builds_neutral_context_without_identity_or_paths(self) -> None:
        rows, audit = context.build_context([source_row(), source_row("b" * 64)])

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0]), set(context.OUTPUT_COLUMNS))
        self.assertTrue(all("identity" not in " ".join(row).lower() for row in rows))
        self.assertTrue(all("path" not in " ".join(row).lower() for row in rows))

    def test_rejects_duplicate_image_content_hash(self) -> None:
        with self.assertRaises(ValueError):
            context.build_context([source_row(), source_row()])

    def test_rejects_non_czechlynx_or_missing_file(self) -> None:
        row = source_row(exists="no")
        with self.assertRaises(ValueError):
            context.build_context([row])

    def test_cli_writes_context_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "source.csv"
            output_path = root / "context.csv"
            audit_path = root / "audit.json"
            with source_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(source_row()))
                writer.writeheader()
                writer.writerows([source_row(), source_row("b" * 64)])

            exit_code = context.main(["--source-manifest", str(source_path), "--output-csv", str(output_path), "--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            with output_path.open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 2)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
