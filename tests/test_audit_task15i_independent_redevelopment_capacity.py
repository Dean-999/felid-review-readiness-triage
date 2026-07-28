import csv
from pathlib import Path
import tempfile
import unittest


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class CapacityAuditTests(unittest.TestCase):
    def test_audit_refuses_human_outcome_collection_when_a_new_image_pool_has_no_pair_graph(
        self,
    ):
        from scripts import audit_task15i_independent_redevelopment_capacity as module

        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            image = tmp_path / "candidate.jpg"
            image.write_bytes(b"independent candidate image")
            manifest = tmp_path / "candidate_images.csv"
            write_csv(
                manifest,
                ["source_candidate_id", "source_image_uri", "source_image_path", "species", "domain_label", "download_status"],
                [
                    {
                        "source_candidate_id": "new-1",
                        "source_image_uri": "https://example.test/new-1.jpg",
                        "source_image_path": str(image),
                        "species": "eurasian_lynx",
                        "domain_label": "external",
                        "download_status": "already_present",
                    }
                ],
            )

            audit = module.audit_capacity(
                candidate_image_manifest=manifest,
                existing_manifest_paths=[],
                requirements=module.CapacityRequirements(
                    component_target=1,
                    pair_target=1,
                    min_pairs_per_component=1,
                    max_pairs_per_component=8,
                    max_endpoint_degree=6,
                    outer_fold_count=1,
                    min_components_per_outer_fold=1,
                ),
            )

        self.assertEqual(audit["status"], "NOT_READY")
        self.assertEqual(audit["candidate_images"]["usable_image_count"], 1)
        self.assertEqual(audit["overlap_audit"]["image_overlap_count"], 0)
        self.assertIn("missing_candidate_pair_manifest", audit["blocking_reasons"])
        self.assertFalse(audit["human_outcome_collection_authorized"])

    def test_audit_accepts_a_disjoint_measured_and_stratified_pair_graph(self):
        from scripts import audit_task15i_independent_redevelopment_capacity as module

        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            image_rows = []
            pair_rows = []
            quality_rows = []
            local_rows = []
            for index in range(20):
                image = tmp_path / f"image-{index}.jpg"
                image.write_bytes(f"new candidate {index}".encode())
                image_id = f"candidate-image-{index}"
                image_rows.append(
                    {
                        "source_candidate_id": f"source-{index // 2}",
                        "source_image_uri": image_id,
                        "source_image_path": str(image),
                        "species": "eurasian_lynx",
                        "domain_label": "external",
                        "download_status": "already_present",
                    }
                )
                quality_rows.append(
                    {
                        "candidate_image_id": image_id,
                        "image_decode_status": "ok",
                        "native_pixel_count": str(1000 + index),
                        "sharpness_measure": str(0.1 + index),
                        "exposure_clipping_fraction": str(index / 100),
                    }
                )
            for index in range(10):
                pair_id = f"pair-{index}"
                pair_rows.append(
                    {
                        "candidate_pair_id": pair_id,
                        "endpoint_a_candidate_image_id": f"candidate-image-{index * 2}",
                        "endpoint_b_candidate_image_id": f"candidate-image-{index * 2 + 1}",
                        "descriptor_support_category": "both",
                        "best_rank_band": "rank_01_05",
                        "development_evidence_state": "ordinary",
                        "endpoint_quality_measurement_failure": "false",
                        "local_match_measurement_failure": "false",
                    }
                )
                local_rows.append(
                    {
                        "candidate_pair_id": pair_id,
                        "failure_code": "none",
                        "value_status": "not_missing",
                        "local_match_coverage_fraction": str(index / 100),
                    }
                )
            manifest = tmp_path / "candidate_images.csv"
            pairs = tmp_path / "candidate_pairs.csv"
            quality = tmp_path / "quality.csv"
            local = tmp_path / "local.csv"
            write_csv(manifest, list(image_rows[0]), image_rows)
            write_csv(pairs, list(pair_rows[0]), pair_rows)
            write_csv(quality, list(quality_rows[0]), quality_rows)
            write_csv(local, list(local_rows[0]), local_rows)

            audit = module.audit_capacity(
                candidate_image_manifest=manifest,
                existing_manifest_paths=[],
                candidate_pair_manifest=pairs,
                automatic_quality_manifest=quality,
                local_match_manifest=local,
                requirements=module.CapacityRequirements(
                    component_target=10,
                    pair_target=10,
                    min_pairs_per_component=1,
                    max_pairs_per_component=8,
                    max_endpoint_degree=6,
                    outer_fold_count=1,
                    min_components_per_outer_fold=10,
                ),
            )

        self.assertEqual(audit["status"], "READY_FOR_PRELABEL_AMENDMENT")
        self.assertEqual(audit["pair_graph_audit"]["component_count"], 10)
        self.assertTrue(audit["measurement_audit"]["automatic_quality"]["pass"])
        self.assertTrue(audit["measurement_audit"]["local_match"]["pass"])

    def test_freeze_preserves_the_audit_and_its_builder_snapshot(self):
        from scripts import audit_task15i_independent_redevelopment_capacity as module

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frozen-audit"
            module.freeze(output, {"status": "NOT_READY"})

            self.assertTrue((output / "capacity_audit.json").is_file())
            self.assertTrue((output / "audit_builder_snapshot.py").is_file())
            checksums = (output / "CHECKSUMS.sha256").read_text(encoding="utf-8")
            self.assertIn("capacity_audit.json", checksums)
            self.assertIn("audit_builder_snapshot.py", checksums)


if __name__ == "__main__":
    unittest.main()
