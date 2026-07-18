from __future__ import annotations

import tempfile
import unittest
import csv
from pathlib import Path

from scripts import migrate_pferi_v1_v2_layout as migration


class PFERILayoutMigrationTests(unittest.TestCase):
    def test_relocate_path_separates_scientific_generations(self) -> None:
        self.assertEqual(
            migration.relocate_path("outputs/final_freeze/bobcat-wild/images/a.jpg"),
            "data/frozen/pferi_v2/bobcat-wild/images/a.jpg",
        )
        self.assertEqual(
            migration.relocate_path("outputs/modeling-validation/result.csv"),
            "archive/pferi_v1/outputs/modeling-validation/result.csv",
        )
        self.assertEqual(
            migration.relocate_path("outputs/v2_candidate_reservoir/dual_sample_confirmation/result.csv"),
            "outputs/pferi_v2/dual_sample_confirmation/result.csv",
        )

    def test_specific_execution_package_mapping_wins_over_v2_result_root(self) -> None:
        self.assertEqual(
            migration.relocate_path(
                "outputs/v2_candidate_reservoir/v2_descriptor_execution_package/images/a.jpg"
            ),
            "work/pferi_v2/descriptor_execution_package/images/a.jpg",
        )
        self.assertEqual(
            migration.relocate_path(
                "outputs/v2_candidate_reservoir/full_frame_local_match_execution/2026-07-16_v1/"
                "PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip"
            ),
            "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
        )

    def test_build_plan_is_collision_checked_and_preserves_outputs_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs/final_freeze/bobcat-wild").mkdir(parents=True)
            (root / "outputs/final_freeze/bobcat-wild/a.jpg").write_bytes(b"image")
            (root / "outputs/modeling-validation").mkdir(parents=True)
            (root / "outputs/modeling-validation/result.csv").write_text("x\n", encoding="utf-8")
            (root / "outputs/v2_candidate_reservoir").mkdir(parents=True)
            (root / "outputs/v2_candidate_reservoir/result.json").write_text("{}\n", encoding="utf-8")
            (root / "outputs/README.md").write_text("# Outputs\n", encoding="utf-8")

            plan = migration.build_plan(root)
            destinations = {move.destination.relative_to(root).as_posix() for move in plan}

            self.assertEqual(len(plan), 3)
            self.assertIn("data/frozen/pferi_v2/bobcat-wild/a.jpg", destinations)
            self.assertIn("archive/pferi_v1/outputs/modeling-validation/result.csv", destinations)
            self.assertIn("outputs/pferi_v2/result.json", destinations)
            self.assertNotIn("outputs/README.md", {move.source.relative_to(root).as_posix() for move in plan})

    def test_rewrite_text_uses_longest_mapping_and_leaves_version_tokens_alone(self) -> None:
        text = (
            "outputs/v2_candidate_reservoir/v2_descriptor_execution_package/images/a.jpg\n"
            "schemas/pferi_v2/canonical_pair_contract_v1.json\n"
        )

        rewritten = migration.rewrite_text(text)

        self.assertIn("work/pferi_v2/descriptor_execution_package/images/a.jpg", rewritten)
        self.assertIn("schemas/pferi_v2/canonical_pair_contract_v1.json", rewritten)
        self.assertEqual(migration.rewrite_text(rewritten), rewritten)

    def test_original_path_inverts_specific_and_legacy_destinations(self) -> None:
        self.assertEqual(
            migration.original_path("archive/pferi_v1/outputs/modeling-validation/result.csv"),
            "outputs/modeling-validation/result.csv",
        )
        self.assertEqual(
            migration.original_path("work/pferi_v2/descriptor_execution_package/images/a.jpg"),
            "outputs/v2_candidate_reservoir/v2_descriptor_execution_package/images/a.jpg",
        )

    def test_manifest_rows_use_raw_sha256_not_analysis_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "outputs/final_freeze/example.jpg"
            destination = root / "data/frozen/pferi_v2/example.jpg"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"raw-image-bytes")
            fingerprint = root / ".ua/outputs-analysis/fingerprints.json"
            fingerprint.parent.mkdir(parents=True)
            fingerprint.write_text(
                '{"files":{"final_freeze/example.jpg":{"contentHash":"not-a-raw-sha"}}}',
                encoding="utf-8",
            )

            rows = migration.manifest_rows(root, [migration.Move(source, destination)])

            self.assertEqual(rows[0]["sha256"], migration.sha256(source))
            self.assertNotEqual(rows[0]["sha256"], "not-a-raw-sha")

    def test_reconcile_accepts_an_exact_cleanup_manifest_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "relocation.csv"
            cleanup = root / "cleanup.csv"
            digest = migration.hashlib.sha256(b"removed").hexdigest()
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["source_path", "destination_path", "size_bytes", "sha256"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_path": "outputs/old.txt",
                        "destination_path": "archive/pferi_v1/old.txt",
                        "size_bytes": 7,
                        "sha256": digest,
                    }
                )
            with cleanup.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["removed_path", "size_bytes", "sha256", "reason", "retained_path"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "removed_path": "archive/pferi_v1/old.txt",
                        "size_bytes": 7,
                        "sha256": digest,
                        "reason": "superseded",
                        "retained_path": "README.md",
                    }
                )

            report = migration.reconcile_manifest(
                manifest,
                dedup_manifest=root / "missing-dedup.csv",
                cleanup_manifest=cleanup,
                root=root,
            )

            self.assertEqual(report["cleanedDestinationCount"], 1)


if __name__ == "__main__":
    unittest.main()
