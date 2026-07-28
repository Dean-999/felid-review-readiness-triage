from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import build_task15i_independent_browser_audit_delivery as builder


class Task15IIndependentBrowserAuditDeliveryTests(unittest.TestCase):
    def test_blank_checklist_covers_every_required_browser_check(self) -> None:
        rows = builder.blank_checklist_rows()
        self.assertEqual([row["required_check"] for row in rows], builder.REQUIRED_CHECKS)
        self.assertTrue(all(row["status"] == "not_started" for row in rows))

    def test_package_rows_rejects_tampered_candidate_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_dir = root / "candidate_reviewer_packages"
            package_dir.mkdir()
            packages = {}
            for alias in ["reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D"]:
                path = package_dir / f"PAIR_REVIEW_{alias}.zip"
                path.write_bytes(alias.encode("utf-8"))
                packages[alias] = {
                    "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "first_pass_task_count": 800,
                    "static_status": "PASS",
                }
            audit = {"status": "PASS_CANDIDATE_NOT_RELEASED", "conflict_attestations_complete": True, "reviewer_packages": packages}
            self.assertEqual(len(builder.package_rows(audit, root)), 4)
            (package_dir / "PAIR_REVIEW_reviewer_A.zip").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                builder.package_rows(audit, root)


if __name__ == "__main__":
    unittest.main()
