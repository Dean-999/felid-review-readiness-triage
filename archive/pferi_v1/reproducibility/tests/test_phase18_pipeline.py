import csv
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.build_phase18b_local_descriptor_control import build_phase18b
from scripts.build_phase18c_czechlynx_pair_contract import build_phase18c
from scripts.build_phase18d_pf_eri_pair_features import build_phase18d
from scripts.build_phase18e_review_router import build_phase18e
from scripts.build_phase18f_bobcat_transfer_readiness import build_phase18f
from scripts.build_phase18g_strong_baseline_claim_gate import build_phase18g
from scripts.build_phase18h_pair_level_failure_mechanism import build_phase18h_pair_level_failure_mechanism
from scripts.build_phase18i_reviewability_analysis import build_phase18i_reviewability_analysis
from scripts.build_phase18i_targeted_review_packet import build_phase18i_targeted_review_packet
from scripts.build_phase18j_full_queue_review_packet import sample_descriptor_rows
from scripts.build_phase18j_reviewer_agreement_analysis import build_phase18j_reviewer_agreement_analysis
from scripts.build_phase18k_adjudication_packet import build_phase18k_adjudication_packet
from scripts.build_phase18k_highest_goal_validation import build_phase18k_highest_goal_validation
from scripts.build_phase18k_uncertainty_concentration import build_phase18k_uncertainty_concentration
from scripts.build_phase18l_descriptor_controlled_analysis import build_phase18l_descriptor_controlled_analysis
from scripts.build_phase18l_descriptor_controlled_review_packet import build_descriptor_packet
from scripts.build_phase18m_identity_balanced_analysis import build_phase18m_identity_balanced_analysis
from scripts.build_phase18m_identity_balanced_review_packet import build_descriptor_identity_balanced_packet
from scripts.build_phase18n_confirmatory_review_packet import build_descriptor_confirmatory_packet
from scripts.receive_phase18_strong_baseline_artifacts import receive_phase18_strong_baseline_artifacts
from scripts.run_phase18_strong_descriptor_pipeline import run_phase18_strong_descriptor_pipeline


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Phase18PipelineTests(unittest.TestCase):
    def strong_artifact_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        phase18a = root / "phase18a.csv"
        rows = [
            {
                "phase18_image_id": "phase18a_bobcat_0001",
                "species": "bobcat",
                "freeze_rank": "1",
                "modeling_role": "bobcat_unlabeled_transfer",
                "train_eval_eligible": "no",
                "has_known_identity": "no",
                "identity_label": "",
                "frozen_image_path": "bobcat_1.jpg",
                "decode_width": "128",
                "decode_height": "96",
                "megapixels": "0.012",
                "min_dimension": "96",
                "max_dimension": "128",
                "aspect_ratio": "1.333333",
                "sha256": "hash_bobcat",
            },
            {
                "phase18_image_id": "phase18a_czechlynx_0001",
                "species": "czechlynx",
                "freeze_rank": "2",
                "modeling_role": "czechlynx_known_id",
                "train_eval_eligible": "yes",
                "has_known_identity": "yes",
                "identity_label": "lynx_a",
                "frozen_image_path": "czech_1.jpg",
                "decode_width": "128",
                "decode_height": "96",
                "megapixels": "0.012",
                "min_dimension": "96",
                "max_dimension": "128",
                "aspect_ratio": "1.333333",
                "sha256": "hash_czech_1",
            },
            {
                "phase18_image_id": "phase18a_czechlynx_0002",
                "species": "czechlynx",
                "freeze_rank": "3",
                "modeling_role": "czechlynx_known_id",
                "train_eval_eligible": "yes",
                "has_known_identity": "yes",
                "identity_label": "lynx_a",
                "frozen_image_path": "czech_2.jpg",
                "decode_width": "128",
                "decode_height": "96",
                "megapixels": "0.012",
                "min_dimension": "96",
                "max_dimension": "128",
                "aspect_ratio": "1.333333",
                "sha256": "hash_czech_2",
            },
            {
                "phase18_image_id": "phase18a_czechlynx_0003",
                "species": "czechlynx",
                "freeze_rank": "4",
                "modeling_role": "czechlynx_known_id",
                "train_eval_eligible": "yes",
                "has_known_identity": "yes",
                "identity_label": "lynx_b",
                "frozen_image_path": "czech_3.jpg",
                "decode_width": "128",
                "decode_height": "96",
                "megapixels": "0.012",
                "min_dimension": "96",
                "max_dimension": "128",
                "aspect_ratio": "1.333333",
                "sha256": "hash_czech_3",
            },
        ]
        write_csv(phase18a, rows, list(rows[0].keys()))
        embedding_manifest = root / "embedding_manifest.csv"
        embedding_rows = []
        for idx, row in enumerate(rows):
            embedding_rows.append(
                {
                    "phase18_image_id": row["phase18_image_id"],
                    "descriptor_name": "test_strong_descriptor",
                    "embedding_row": idx,
                    "embedding_dim": 3,
                    "sha256": row["sha256"],
                }
            )
        write_csv(embedding_manifest, embedding_rows, list(embedding_rows[0].keys()))
        embeddings = root / "embeddings.npy"
        matrix = np.asarray(
            [
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0],
                [0.9, 0.1, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
        matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
        np.save(embeddings, matrix)
        pair_scores = root / "pair_scores.csv"
        pair_rows = [
            {
                "query_image_id": "phase18a_czechlynx_0001",
                "candidate_image_id": "phase18a_czechlynx_0002",
                "descriptor_name": "test_strong_descriptor",
                "strong_descriptor_similarity": "0.99",
                "strong_descriptor_rank": "1",
            },
            {
                "query_image_id": "phase18a_czechlynx_0002",
                "candidate_image_id": "phase18a_czechlynx_0001",
                "descriptor_name": "test_strong_descriptor",
                "strong_descriptor_similarity": "0.99",
                "strong_descriptor_rank": "1",
            },
        ]
        write_csv(pair_scores, pair_rows, list(pair_rows[0].keys()))
        return phase18a, embedding_manifest, embeddings, pair_scores

    def test_phase18b_builds_local_descriptor_manifest_and_embeddings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "one.jpg"
            Image.new("RGB", (64, 48), color=(80, 100, 120)).save(image_path)
            input_csv = root / "phase18a.csv"
            write_csv(
                input_csv,
                [
                    {
                        "phase18_image_id": "phase18a_bobcat_0001",
                        "species": "bobcat",
                        "freeze_rank": "1",
                        "modeling_role": "bobcat_unlabeled_transfer",
                        "train_eval_eligible": "no",
                        "has_known_identity": "no",
                        "identity_label": "",
                        "frozen_image_path": str(image_path),
                        "decode_width": "64",
                        "decode_height": "48",
                        "megapixels": "0.003",
                        "min_dimension": "48",
                        "max_dimension": "64",
                        "aspect_ratio": "1.333333",
                        "sha256": "abc",
                    }
                ],
                [
                    "phase18_image_id",
                    "species",
                    "freeze_rank",
                    "modeling_role",
                    "train_eval_eligible",
                    "has_known_identity",
                    "identity_label",
                    "frozen_image_path",
                    "decode_width",
                    "decode_height",
                    "megapixels",
                    "min_dimension",
                    "max_dimension",
                    "aspect_ratio",
                    "sha256",
                ],
            )
            audit = build_phase18b(input_csv, root / "out")
            self.assertEqual(audit["row_count"], 1)
            self.assertEqual(audit["embedding_shape"][0], 1)
            self.assertTrue((root / "out/phase18b_local_descriptor_embeddings.npy").exists())

    def test_phase18c_to_e_builds_known_id_pair_features_and_router(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "phase18b_manifest.csv"
            embeddings = root / "embeddings.npy"
            rows = []
            vectors = []
            specs = [
                ("phase18a_czechlynx_0001", "lynx_a", [1.0, 0.0, 0.0]),
                ("phase18a_czechlynx_0002", "lynx_a", [0.9, 0.1, 0.0]),
                ("phase18a_czechlynx_0003", "lynx_b", [0.0, 1.0, 0.0]),
                ("phase18a_czechlynx_0004", "lynx_b", [0.0, 0.9, 0.1]),
            ]
            for idx, (image_id, identity, vector) in enumerate(specs):
                rows.append(
                    {
                        "embedding_row": idx,
                        "phase18_image_id": image_id,
                        "species": "czechlynx",
                        "freeze_rank": idx + 1,
                        "modeling_role": "czechlynx_known_id",
                        "train_eval_eligible": "yes",
                        "has_known_identity": "yes",
                        "identity_label": identity,
                        "frozen_image_path": f"{image_id}.jpg",
                        "decode_width": "128",
                        "decode_height": "96",
                        "megapixels": "0.012",
                        "min_dimension": "96",
                        "max_dimension": "128",
                        "aspect_ratio": "1.333333",
                        "sha256": "hash",
                        "descriptor_name": "test_descriptor",
                        "descriptor_dim": "3",
                        "descriptor_status": "test",
                        "claim_boundary": "test",
                    }
                )
                vectors.append(vector)
            write_csv(manifest, rows, list(rows[0].keys()))
            matrix = np.asarray(vectors, dtype=np.float32)
            matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
            np.save(embeddings, matrix)

            c_audit = build_phase18c(manifest, embeddings, root / "c", top_k=2)
            self.assertEqual(c_audit["pair_rows"], 8)
            self.assertGreaterEqual(c_audit["same_identity_pairs"], 4)

            d_audit = build_phase18d(root / "c/phase18c_czechlynx_known_id_pair_contract.csv", root / "d")
            self.assertEqual(d_audit["pair_rows"], 8)

            e_audit = build_phase18e(root / "d/phase18d_pf_eri_pair_features.csv", root / "e")
            self.assertEqual(e_audit["policy_count"], 5)
            self.assertTrue((root / "e/phase18e_review_router_metrics.csv").exists())

    def test_phase18f_builds_bobcat_transfer_readiness_without_identity_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "phase18b_manifest.csv"
            embeddings = root / "embeddings.npy"
            rows = []
            matrix = np.eye(3, dtype=np.float32)
            for idx in range(3):
                rows.append(
                    {
                        "embedding_row": idx,
                        "phase18_image_id": f"phase18a_bobcat_{idx + 1:04d}",
                        "species": "bobcat",
                        "freeze_rank": idx + 1,
                        "modeling_role": "bobcat_unlabeled_transfer",
                        "train_eval_eligible": "no",
                        "has_known_identity": "no",
                        "identity_label": "",
                        "frozen_image_path": f"bobcat_{idx}.jpg",
                        "decode_width": "128",
                        "decode_height": "96",
                        "megapixels": "0.012",
                        "min_dimension": "96",
                        "max_dimension": "128",
                        "aspect_ratio": "1.333333",
                        "sha256": "hash",
                        "descriptor_name": "test_descriptor",
                        "descriptor_dim": "3",
                        "descriptor_status": "test",
                        "claim_boundary": "test",
                    }
                )
            write_csv(manifest, rows, list(rows[0].keys()))
            np.save(embeddings, matrix)

            audit = build_phase18f(manifest, embeddings, root / "f", top_k=2)
            self.assertEqual(audit["bobcat_image_count"], 3)
            self.assertEqual(audit["pair_rows"], 6)
            self.assertIn("individual identity claim", audit["claim_boundary"].lower())

    def test_phase18g_blocks_claims_without_strong_baseline_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "phase18a.csv"
            rows = [
                {
                    "phase18_image_id": "phase18a_czechlynx_0001",
                    "species": "czechlynx",
                    "modeling_role": "czechlynx_known_id",
                    "train_eval_eligible": "yes",
                    "has_known_identity": "yes",
                    "identity_label": "lynx_a",
                    "frozen_image_path": "image_a.jpg",
                    "sha256": "hash_a",
                },
                {
                    "phase18_image_id": "phase18a_bobcat_0001",
                    "species": "bobcat",
                    "modeling_role": "bobcat_unlabeled_transfer",
                    "train_eval_eligible": "no",
                    "has_known_identity": "no",
                    "identity_label": "",
                    "frozen_image_path": "image_b.jpg",
                    "sha256": "hash_b",
                },
            ]
            write_csv(manifest, rows, list(rows[0].keys()))

            audit = build_phase18g(manifest, root / "g")

            self.assertEqual(audit["image_rows"], 2)
            self.assertEqual(audit["phase18g_status"], "BLOCKED_STRONG_BASELINE_NOT_RUN")
            self.assertTrue((root / "g/phase18g_strong_baseline_handoff_manifest.csv").exists())
            self.assertTrue((root / "g/phase18g_claim_gate.csv").exists())

    def test_phase18g_unlocks_with_external_strong_artifacts_without_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "phase18a.csv"
            rows = [
                {
                    "phase18_image_id": "phase18a_czechlynx_0001",
                    "species": "czechlynx",
                    "modeling_role": "czechlynx_known_id",
                    "train_eval_eligible": "yes",
                    "has_known_identity": "yes",
                    "identity_label": "lynx_a",
                    "frozen_image_path": "image_a.jpg",
                    "sha256": "hash_a",
                }
            ]
            write_csv(manifest, rows, list(rows[0].keys()))
            strong_manifest = root / "strong_manifest.csv"
            strong_scores = root / "strong_scores.csv"
            strong_manifest.write_text("phase18_image_id\nphase18a_czechlynx_0001\n", encoding="utf-8")
            strong_scores.write_text("query_image_id,candidate_image_id\nx,y\n", encoding="utf-8")

            audit = build_phase18g(manifest, root / "g", strong_manifest, strong_scores)

            self.assertEqual(audit["phase18g_status"], "READY_FOR_STRONG_BASELINE_EVALUATION")

    def test_strong_artifact_receiver_accepts_valid_external_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)

            audit = receive_phase18_strong_baseline_artifacts(
                descriptor_name="test_strong_descriptor",
                embedding_manifest=embedding_manifest,
                embeddings_npy=embeddings,
                pair_scores=pair_scores,
                output_dir=root / "strong",
                phase18a_manifest=phase18a,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["embedding_rows"], 4)
            self.assertTrue((root / "strong/phase18_strong_embedding_manifest.csv").exists())

    def test_strong_artifact_receiver_rejects_missing_embedding_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)
            with embedding_manifest.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))[:-1]
            write_csv(embedding_manifest, rows, list(rows[0].keys()))

            with self.assertRaisesRegex(ValueError, "coverage mismatch"):
                receive_phase18_strong_baseline_artifacts(
                    descriptor_name="test_strong_descriptor",
                    embedding_manifest=embedding_manifest,
                    embeddings_npy=embeddings,
                    pair_scores=pair_scores,
                    output_dir=root / "strong",
                    phase18a_manifest=phase18a,
                )

    def test_strong_artifact_receiver_rejects_duplicate_image_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)
            with embedding_manifest.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["phase18_image_id"] = rows[0]["phase18_image_id"]
            write_csv(embedding_manifest, rows, list(rows[0].keys()))

            with self.assertRaisesRegex(ValueError, "duplicate phase18_image_id"):
                receive_phase18_strong_baseline_artifacts(
                    descriptor_name="test_strong_descriptor",
                    embedding_manifest=embedding_manifest,
                    embeddings_npy=embeddings,
                    pair_scores=pair_scores,
                    output_dir=root / "strong",
                    phase18a_manifest=phase18a,
                )

    def test_strong_artifact_receiver_rejects_sha256_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)
            with embedding_manifest.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["sha256"] = "wrong"
            write_csv(embedding_manifest, rows, list(rows[0].keys()))

            with self.assertRaisesRegex(ValueError, "sha256 mismatch"):
                receive_phase18_strong_baseline_artifacts(
                    descriptor_name="test_strong_descriptor",
                    embedding_manifest=embedding_manifest,
                    embeddings_npy=embeddings,
                    pair_scores=pair_scores,
                    output_dir=root / "strong",
                    phase18a_manifest=phase18a,
                )

    def test_strong_artifact_receiver_rejects_bobcat_identity_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)
            with embedding_manifest.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["identity_label"] = "bobcat_a"
            write_csv(embedding_manifest, rows, list(rows[0].keys()) + ["identity_label"])

            with self.assertRaisesRegex(ValueError, "Bobcat strong artifact"):
                receive_phase18_strong_baseline_artifacts(
                    descriptor_name="test_strong_descriptor",
                    embedding_manifest=embedding_manifest,
                    embeddings_npy=embeddings,
                    pair_scores=pair_scores,
                    output_dir=root / "strong",
                    phase18a_manifest=phase18a,
                )

    def test_strong_descriptor_pipeline_outputs_confidence_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phase18a, embedding_manifest, embeddings, pair_scores = self.strong_artifact_fixture(root)
            receive_phase18_strong_baseline_artifacts(
                descriptor_name="test_strong_descriptor",
                embedding_manifest=embedding_manifest,
                embeddings_npy=embeddings,
                pair_scores=pair_scores,
                output_dir=root / "strong",
                phase18a_manifest=phase18a,
            )

            audit = run_phase18_strong_descriptor_pipeline(
                descriptor_name="test_strong_descriptor",
                manifest_csv=root / "strong/phase18_strong_embedding_manifest.csv",
                embeddings_npy=root / "strong/phase18_strong_embeddings.npy",
                output_root=root / "outputs",
                czech_top_k=2,
                bobcat_top_k=1,
                bootstrap_iterations=25,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["phase18e"]["metric_rows"], 10)
            confidence_csv = root / "outputs/phase18_review_utility_confidence/test_strong_descriptor/phase18_review_utility_bootstrap_confidence.csv"
            self.assertTrue(confidence_csv.exists())
            header = confidence_csv.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("ci_lower", header)
            self.assertIn("direction", header)

    def test_phase18h_builds_mechanism_tables_and_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            features = root / "features.csv"
            rows = []
            for split in ["calibration", "evaluation"]:
                for idx in range(12):
                    same = "yes" if idx % 4 == 0 else "no"
                    high = idx >= 8
                    rows.append(
                        {
                            "pair_id": f"{split}_{idx}",
                            "descriptor_name": "test_descriptor",
                            "query_image_id": f"query_{split}_{idx // 3}",
                            "candidate_image_id": f"candidate_{split}_{idx}",
                            "same_identity": same,
                            "candidate_rank_descriptor": idx + 1,
                            "descriptor_similarity": 0.9 if high else 0.4,
                            "descriptor_similarity_percentile": 0.95 if high else 0.2,
                            "query_split_role": split,
                            "split_id": 1,
                            "query_image_quality_score": 0.7,
                            "candidate_image_quality_score": 0.7,
                            "weakest_image_quality_score": 0.3 if high else 0.8,
                            "pair_size_compatibility_score": 0.7,
                            "pair_aspect_compatibility_score": 0.7,
                            "pair_geometry_score": 0.4 if high else 0.8,
                            "descriptor_evidence_conflict_score": 0.8 if high else 0.1,
                            "pf_eri_admissibility_score": 0.35 if high else 0.8,
                            "pf_eri_review_score": 0.45 if high else 0.7,
                            "pf_eri_route": "defer_low_evidence" if high else "review",
                            "claim_boundary": "test",
                        }
                    )
            write_csv(features, rows, list(rows[0].keys()))

            audit = build_phase18h_pair_level_failure_mechanism(
                descriptor_name="test_descriptor",
                input_features=features,
                output_dir=root / "h",
                sample_limit=3,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["enrichment_rows"], 12)
            self.assertEqual(audit["operating_rows"], 18)
            self.assertTrue((root / "h/phase18h_conflict_enrichment.csv").exists())
            self.assertTrue((root / "h/phase18h_fixed_positive_retention_operating_points.csv").exists())
            sample_header = (root / "h/phase18h_failure_case_sample.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("sample_group", sample_header)

    def test_phase18i_builds_blinded_review_packet_and_contact_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_a = root / "query.jpg"
            image_b = root / "candidate.jpg"
            Image.new("RGB", (80, 60), color=(120, 100, 80)).save(image_a)
            Image.new("RGB", (70, 90), color=(80, 120, 100)).save(image_b)
            phase18a = root / "phase18a.csv"
            manifest_rows = [
                {
                    "phase18_image_id": "phase18a_czechlynx_0001",
                    "species": "czechlynx",
                    "frozen_image_path": str(image_a),
                },
                {
                    "phase18_image_id": "phase18a_czechlynx_0002",
                    "species": "czechlynx",
                    "frozen_image_path": str(image_b),
                },
            ]
            write_csv(phase18a, manifest_rows, list(manifest_rows[0].keys()))
            sample_csv = root / "phase18h_failure_case_sample.csv"
            sample_rows = [
                {
                    "descriptor_name": "test_descriptor",
                    "sample_group": "high_similarity_false_high_conflict",
                    "pair_id": "pair_1",
                    "query_image_id": "phase18a_czechlynx_0001",
                    "candidate_image_id": "phase18a_czechlynx_0002",
                    "same_identity": "no",
                    "candidate_rank_descriptor": "1",
                    "descriptor_similarity": "0.91",
                    "descriptor_similarity_percentile": "0.95",
                    "descriptor_evidence_conflict_score": "0.8",
                    "pf_eri_admissibility_score": "0.35",
                    "pf_eri_review_score": "0.42",
                    "pf_eri_route": "defer_low_evidence",
                    "weakest_image_quality_score": "0.4",
                    "pair_geometry_score": "0.5",
                    "interpretation": "test sample",
                    "claim_boundary": "test",
                }
            ]
            write_csv(sample_csv, sample_rows, list(sample_rows[0].keys()))

            audit = build_phase18i_targeted_review_packet(
                descriptor_name="test_descriptor",
                phase18h_sample_csv=sample_csv,
                phase18a_manifest=phase18a,
                output_dir=root / "i",
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["review_pair_rows"], 1)
            self.assertTrue((root / "i/phase18i_contact_sheet.jpg").exists())
            review_header = (root / "i/phase18i_targeted_pair_review_packet.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("same_identity_known_id", review_header)
            blind_header = (root / "i/phase18i_blind_review_form.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("reviewability_label", blind_header)
            self.assertNotIn("same_identity", blind_header)
            self.assertNotIn("descriptor_similarity", blind_header)

    def test_phase18i_reviewability_analysis_outputs_contrasts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_csv = root / "full.csv"
            working_csv = root / "working.csv"
            full_rows = []
            working_rows = []
            for idx in range(6):
                pair_id = f"phase18i_test_blind_{idx:04d}"
                same = "yes" if idx < 3 else "no"
                label = "review_ready" if idx < 4 else "uncertain"
                full_rows.append(
                    {
                        "review_pair_id": pair_id,
                        "descriptor_name": "test_descriptor",
                        "sample_group": "high_similarity_same_identity_control"
                        if same == "yes"
                        else "high_similarity_false_high_conflict",
                        "query_image_id": f"query_{idx}",
                        "candidate_image_id": f"candidate_{idx}",
                        "query_image_path": f"query_{idx}.jpg",
                        "candidate_image_path": f"candidate_{idx}.jpg",
                        "same_identity_known_id": same,
                        "candidate_rank_descriptor": idx + 1,
                        "descriptor_similarity": 0.9,
                        "descriptor_similarity_percentile": 0.9,
                        "descriptor_evidence_conflict_score": 0.2 + idx * 0.01,
                        "pf_eri_admissibility_score": 0.8 if label == "review_ready" else 0.5,
                        "pf_eri_review_score": 0.8 if label == "review_ready" else 0.5,
                        "pf_eri_route": "review",
                        "weakest_image_quality_score": 0.7,
                        "pair_geometry_score": 0.8 if label == "review_ready" else 0.5,
                        "phase18h_interpretation": "test",
                        "reviewability_label": "",
                        "visibility_notes": "",
                        "reviewer_id": "",
                        "review_timestamp": "",
                        "claim_boundary": "test",
                    }
                )
                working_rows.append(
                    {
                        "review_pair_id": pair_id,
                        "query_image_path": f"query_{idx}.jpg",
                        "candidate_image_path": f"candidate_{idx}.jpg",
                        "reviewability_label": label,
                        "visibility_notes": "",
                        "reviewer_id": "tester",
                        "review_timestamp": "2026-07-02T00:00:00+00:00",
                        "descriptor_name": "test_descriptor",
                    }
                )
            write_csv(full_csv, full_rows, list(full_rows[0].keys()))
            write_csv(working_csv, working_rows, list(working_rows[0].keys()))

            audit = build_phase18i_reviewability_analysis(
                descriptor_name="test_descriptor",
                working_csv=working_csv,
                full_packet_csv=full_csv,
                output_dir=root / "analysis",
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["summary"]["review_ready_count"], 4)
            self.assertTrue((root / "analysis/phase18i_reviewability_binary_contrasts.csv").exists())
            score_header = (root / "analysis/phase18i_reviewability_score_contrasts.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("auc_higher_score_predicts_review_ready", score_header)

    def test_phase18j_full_queue_packet_builds_stratified_blind_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_a = root / "a.jpg"
            image_b = root / "b.jpg"
            Image.new("RGB", (80, 60), color=(120, 100, 80)).save(image_a)
            Image.new("RGB", (90, 70), color=(80, 120, 100)).save(image_b)
            phase18a = root / "phase18a.csv"
            manifest_rows = [
                {"phase18_image_id": "query_1", "frozen_image_path": str(image_a)},
                {"phase18_image_id": "candidate_1", "frozen_image_path": str(image_b)},
                {"phase18_image_id": "query_2", "frozen_image_path": str(image_a)},
                {"phase18_image_id": "candidate_2", "frozen_image_path": str(image_b)},
            ]
            write_csv(phase18a, manifest_rows, list(manifest_rows[0].keys()))
            features = root / "features.csv"
            feature_rows = []
            for idx in range(24):
                same = "yes" if idx % 2 == 0 else "no"
                rank = [1, 3, 8, 15][idx % 4]
                feature_rows.append(
                    {
                        "pair_id": f"pair_{idx}",
                        "descriptor_name": "test_descriptor",
                        "query_image_id": "query_1" if idx % 3 else "query_2",
                        "candidate_image_id": "candidate_1" if idx % 5 else "candidate_2",
                        "same_identity": same,
                        "candidate_rank_descriptor": rank,
                        "descriptor_similarity": 0.8,
                        "descriptor_similarity_percentile": 0.7,
                        "query_split_role": "evaluation",
                        "split_id": 1,
                        "query_image_quality_score": 0.7,
                        "candidate_image_quality_score": 0.7,
                        "weakest_image_quality_score": 0.7,
                        "pair_size_compatibility_score": 0.7,
                        "pair_aspect_compatibility_score": 0.7,
                        "pair_geometry_score": 0.7,
                        "descriptor_evidence_conflict_score": 0.2,
                        "pf_eri_admissibility_score": idx / 24,
                        "pf_eri_review_score": 0.7,
                        "pf_eri_route": "review",
                        "claim_boundary": "test",
                    }
                )
            write_csv(features, feature_rows, list(feature_rows[0].keys()))

            audit = sample_descriptor_rows(
                descriptor_name="test_descriptor",
                features_csv=features,
                phase18a_manifest=phase18a,
                output_dir=root / "packet",
                sample_size=12,
                random_seed=20260703,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["sample_rows"], 12)
            blind_header = (root / "packet/phase18j_blind_review_form.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("reviewability_decision", blind_header)
            self.assertIn("not_ready_reason", blind_header)
            self.assertNotIn("same_identity", blind_header)
            codebook = (root / "packet/phase18j_reviewability_codebook.csv").read_text(encoding="utf-8")
            self.assertIn("both_low_evidence_and_non_comparable", codebook)

    def test_phase18j_reviewer_agreement_analysis_outputs_kappa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_root = root / "packet"
            review_root = root / "reviews"
            for descriptor in ["megadescriptor_l_384", "dinov2_vitl14"]:
                full_rows = []
                for idx in range(4):
                    pair_id = f"phase18j_{descriptor}_blind_{idx:04d}"
                    full_rows.append(
                        {
                            "review_pair_id": pair_id,
                            "descriptor_name": descriptor,
                            "sample_scope": "test",
                            "stratum_id": "test",
                            "query_image_id": f"query_{idx}",
                            "candidate_image_id": f"candidate_{idx}",
                            "query_image_path": f"query_{idx}.jpg",
                            "candidate_image_path": f"candidate_{idx}.jpg",
                            "same_identity_known_id": "yes" if idx < 2 else "no",
                            "candidate_rank_descriptor": idx + 1,
                            "rank_bin": "rank_01",
                            "descriptor_similarity": 0.8,
                            "descriptor_similarity_percentile": 0.8,
                            "admissibility_tertile": "admissibility_high",
                            "descriptor_evidence_conflict_score": 0.2,
                            "pf_eri_admissibility_score": 0.8 if idx < 2 else 0.6,
                            "pf_eri_review_score": 0.8 if idx < 2 else 0.6,
                            "pf_eri_route": "review",
                            "weakest_image_quality_score": 0.7,
                            "pair_geometry_score": 0.8,
                            "query_split_role": "evaluation",
                            "reviewability_decision": "",
                            "not_ready_reason": "",
                            "secondary_reason": "",
                            "visibility_notes": "",
                            "reviewer_id": "",
                            "review_timestamp": "",
                            "claim_boundary": "test",
                        }
                    )
                packet_dir = packet_root / descriptor
                write_csv(packet_dir / "phase18j_full_queue_review_packet.csv", full_rows, list(full_rows[0].keys()))
                for reviewer in ["reviewer1", "reviewer2", "reviewer3"]:
                    working_rows = []
                    for idx, row in enumerate(full_rows):
                        decision = "review_ready" if idx < 2 else "uncertain"
                        if reviewer == "reviewer2" and idx == 2:
                            decision = "not_review_ready"
                        working_rows.append(
                            {
                                "review_pair_id": row["review_pair_id"],
                                "query_image_path": row["query_image_path"],
                                "candidate_image_path": row["candidate_image_path"],
                                "reviewability_decision": decision,
                                "not_ready_reason": "low_evidence" if decision == "not_review_ready" else "",
                                "secondary_reason": "",
                                "visibility_notes": "",
                                "reviewer_id": reviewer,
                                "review_timestamp": "2026-07-03T00:00:00+00:00",
                                "descriptor_name": descriptor,
                            }
                        )
                    review_dir = review_root / reviewer / descriptor
                    write_csv(review_dir / "phase18j_full_queue_review_working.csv", working_rows, list(working_rows[0].keys()))

            audit = build_phase18j_reviewer_agreement_analysis(
                packet_root=packet_root,
                review_root=review_root,
                output_dir=root / "analysis",
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["majority_pair_rows"], 8)
            agreement_header = (root / "analysis/phase18j_reviewer_agreement.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("cohen_kappa", agreement_header)
            majority_header = (root / "analysis/phase18j_pair_majority_labels.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("majority_decision", majority_header)

    def test_phase18k_highest_goal_validation_outputs_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis_dir = root / "analysis"
            packet_root = root / "packet"
            majority_rows = []
            for descriptor in ["megadescriptor_l_384", "dinov2_vitl14"]:
                packet_rows = []
                for idx in range(12):
                    ready = idx < 7
                    pair_id = f"phase18j_{descriptor}_blind_{idx:04d}"
                    rank_bin = "rank_01" if idx < 6 else "rank_02_05"
                    packet_rows.append(
                        {
                            "review_pair_id": pair_id,
                            "descriptor_name": descriptor,
                            "sample_scope": "test",
                            "stratum_id": "test",
                            "query_image_id": f"query_{idx % 6}",
                            "candidate_image_id": f"candidate_{idx}",
                            "query_image_path": f"query_{idx}.jpg",
                            "candidate_image_path": f"candidate_{idx}.jpg",
                            "same_identity_known_id": "yes" if idx % 3 == 0 else "no",
                            "candidate_rank_descriptor": idx + 1,
                            "rank_bin": rank_bin,
                            "descriptor_similarity": 0.5 + idx * 0.01,
                            "descriptor_similarity_percentile": 0.5 + idx * 0.01,
                            "admissibility_tertile": "admissibility_high" if ready else "admissibility_low",
                            "descriptor_evidence_conflict_score": 0.2,
                            "pf_eri_admissibility_score": 0.82 if ready else 0.35,
                            "pf_eri_review_score": 0.85 if ready else 0.30,
                            "pf_eri_route": "review" if ready else "defer_low_evidence",
                            "weakest_image_quality_score": 0.55,
                            "pair_geometry_score": 0.8 if ready else 0.4,
                            "query_split_role": "evaluation",
                            "reviewability_decision": "",
                            "not_ready_reason": "",
                            "secondary_reason": "",
                            "visibility_notes": "",
                            "reviewer_id": "",
                            "review_timestamp": "",
                            "claim_boundary": "test",
                        }
                    )
                    majority_rows.append(
                        {
                            "descriptor_name": descriptor,
                            "review_pair_id": pair_id,
                            "reviewer_count": 3,
                            "majority_decision": "review_ready" if ready else "uncertain",
                            "majority_binary_review_ready": "yes" if ready else "no",
                            "unanimous_decision": "yes",
                            "decision_votes": "review_ready:3" if ready else "uncertain:3",
                            "reason_votes": "",
                            "same_identity_known_id": "yes" if idx % 3 == 0 else "no",
                            "rank_bin": rank_bin,
                            "admissibility_tertile": "admissibility_high" if ready else "admissibility_low",
                            "candidate_rank_descriptor": idx + 1,
                            "descriptor_similarity_percentile": 0.5 + idx * 0.01,
                            "pf_eri_admissibility_score": 0.82 if ready else 0.35,
                            "pf_eri_review_score": 0.85 if ready else 0.30,
                            "weakest_image_quality_score": 0.55,
                            "pair_geometry_score": 0.8 if ready else 0.4,
                            "pf_eri_route": "review" if ready else "defer_low_evidence",
                        }
                    )
                packet_dir = packet_root / descriptor
                write_csv(packet_dir / "phase18j_full_queue_review_packet.csv", packet_rows, list(packet_rows[0].keys()))
            write_csv(analysis_dir / "phase18j_pair_majority_labels.csv", majority_rows, list(majority_rows[0].keys()))

            audit = build_phase18k_highest_goal_validation(
                analysis_dir=analysis_dir,
                packet_root=packet_root,
                output_dir=root / "phase18k",
            )

            self.assertIn(audit["status"], {"PASS", "NEEDS_MORE_EVIDENCE"})
            model_header = (root / "phase18k/phase18k_model_comparison.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("model_name", model_header)
            incremental = (root / "phase18k/phase18k_incremental_utility_summary.csv").read_text(
                encoding="utf-8"
            )
            self.assertIn("full_pf_eri_model_vs_descriptor_similarity_plus_quality", incremental)
            cluster_header = (root / "phase18k/phase18k_cluster_bootstrap.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("cluster_column", cluster_header)
            self.assertTrue((root / "phase18k/phase18k_review_utility_at_fixed_retention.csv").exists())

    def test_phase18k_adjudication_packet_includes_only_disagreements_and_blinds_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis_dir = root / "analysis"
            packet_root = root / "packet"
            rows = []
            packet_rows = []
            for idx in range(4):
                pair_id = f"phase18j_megadescriptor_l_384_blind_{idx:04d}"
                unanimous = idx % 2 == 0
                rows.append(
                    {
                        "descriptor_name": "megadescriptor_l_384",
                        "review_pair_id": pair_id,
                        "reviewer_count": 3,
                        "majority_decision": "review_ready",
                        "majority_binary_review_ready": "yes",
                        "unanimous_decision": "yes" if unanimous else "no",
                        "decision_votes": "review_ready:3" if unanimous else "review_ready:2;uncertain:1",
                        "reason_votes": "",
                        "same_identity_known_id": "yes",
                        "rank_bin": "rank_01",
                        "admissibility_tertile": "admissibility_high",
                        "candidate_rank_descriptor": idx + 1,
                        "descriptor_similarity_percentile": 0.8,
                        "pf_eri_admissibility_score": 0.8,
                        "pf_eri_review_score": 0.8,
                        "weakest_image_quality_score": 0.7,
                        "pair_geometry_score": 0.8,
                        "pf_eri_route": "review",
                    }
                )
                packet_rows.append(
                    {
                        "review_pair_id": pair_id,
                        "query_image_id": f"query_{idx}",
                        "candidate_image_id": f"candidate_{idx}",
                        "query_image_path": f"query_{idx}.jpg",
                        "candidate_image_path": f"candidate_{idx}.jpg",
                    }
                )
            write_csv(analysis_dir / "phase18j_pair_majority_labels.csv", rows, list(rows[0].keys()))
            write_csv(
                packet_root / "megadescriptor_l_384/phase18j_full_queue_review_packet.csv",
                packet_rows,
                list(packet_rows[0].keys()),
            )

            audit = build_phase18k_adjudication_packet(
                analysis_dir=analysis_dir,
                packet_root=packet_root,
                output_dir=root / "adjudication",
            )

            self.assertEqual(audit["disagreement_pair_count"], 2)
            blind_header = (root / "adjudication/phase18k_adjudication_blind_packet.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("adjudicated_reviewability_label", blind_header)
            self.assertNotIn("descriptor_name", blind_header)
            self.assertNotIn("pf_eri_review_score", blind_header)
            hidden_header = (root / "adjudication/phase18k_adjudication_hidden_audit.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("descriptor_name", hidden_header)

    def test_phase18k_uncertainty_concentration_outputs_enrichment_and_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis_dir = root / "analysis"
            packet_root = root / "packet"
            majority_rows = []
            packet_rows = []
            for idx in range(12):
                uncertain = idx >= 6
                pair_id = f"phase18j_megadescriptor_l_384_blind_{idx:04d}"
                majority_rows.append(
                    {
                        "descriptor_name": "megadescriptor_l_384",
                        "review_pair_id": pair_id,
                        "reviewer_count": 3,
                        "majority_decision": "uncertain" if uncertain else "review_ready",
                        "majority_binary_review_ready": "no" if uncertain else "yes",
                        "unanimous_decision": "yes",
                        "decision_votes": "uncertain:3" if uncertain else "review_ready:3",
                        "reason_votes": "",
                        "same_identity_known_id": "no" if uncertain else "yes",
                        "rank_bin": "rank_01" if idx < 6 else "rank_02_05",
                        "admissibility_tertile": "admissibility_low" if uncertain else "admissibility_high",
                        "candidate_rank_descriptor": idx + 1,
                        "descriptor_similarity_percentile": 0.8,
                        "pf_eri_admissibility_score": 0.2 if uncertain else 0.8,
                        "pf_eri_review_score": 0.3 if uncertain else 0.8,
                        "weakest_image_quality_score": 0.6,
                        "pair_geometry_score": 0.3 if uncertain else 0.9,
                        "pf_eri_route": "defer_low_evidence" if uncertain else "review",
                    }
                )
                packet_rows.append(
                    {
                        "review_pair_id": pair_id,
                        "query_image_id": f"query_{idx % 4}",
                        "candidate_image_id": f"candidate_{idx}",
                        "query_image_path": f"query_{idx}.jpg",
                        "candidate_image_path": f"candidate_{idx}.jpg",
                        "descriptor_similarity": 0.8,
                        "descriptor_evidence_conflict_score": 0.7 if uncertain else 0.1,
                    }
                )
            write_csv(analysis_dir / "phase18j_pair_majority_labels.csv", majority_rows, list(majority_rows[0].keys()))
            write_csv(
                packet_root / "megadescriptor_l_384/phase18j_full_queue_review_packet.csv",
                packet_rows,
                list(packet_rows[0].keys()),
            )

            audit = build_phase18k_uncertainty_concentration(
                analysis_dir=analysis_dir,
                packet_root=packet_root,
                output_dir=root / "uncertainty",
            )

            self.assertEqual(audit["status"], "PASS")
            contrast_text = (root / "uncertainty/phase18k_uncertainty_enrichment_contrasts.csv").read_text(
                encoding="utf-8"
            )
            self.assertIn("low_vs_high_admissibility", contrast_text)
            examples = (root / "uncertainty/phase18k_idealized_proof_examples.csv").read_text(encoding="utf-8")
            self.assertIn("High descriptor similarity, low PF-ERI admissibility", examples)

    def test_phase18l_descriptor_controlled_packet_matches_similarity_and_blinds_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_a = root / "a.jpg"
            image_b = root / "b.jpg"
            Image.new("RGB", (80, 60), color=(120, 100, 80)).save(image_a)
            Image.new("RGB", (90, 70), color=(80, 120, 100)).save(image_b)
            phase18a = root / "phase18a.csv"
            manifest_rows = [
                {"phase18_image_id": f"query_{idx}", "frozen_image_path": str(image_a)}
                for idx in range(8)
            ] + [
                {"phase18_image_id": f"candidate_{idx}", "frozen_image_path": str(image_b)}
                for idx in range(8)
            ]
            write_csv(phase18a, manifest_rows, list(manifest_rows[0].keys()))
            feature_rows = []
            for idx in range(80):
                high = idx % 2 == 0
                feature_rows.append(
                    {
                        "pair_id": f"pair_{idx}",
                        "descriptor_name": "test_descriptor",
                        "query_image_id": f"query_{idx % 8}",
                        "candidate_image_id": f"candidate_{idx % 8}",
                        "same_identity": "yes" if idx % 5 == 0 else "no",
                        "candidate_rank_descriptor": (idx % 10) + 1,
                        "descriptor_similarity": 0.8 + (idx % 20) * 0.001,
                        "descriptor_similarity_percentile": 0.8 + (idx % 20) * 0.001,
                        "query_split_role": "evaluation",
                        "split_id": 1,
                        "query_image_quality_score": 0.7,
                        "candidate_image_quality_score": 0.7,
                        "weakest_image_quality_score": 0.7,
                        "pair_size_compatibility_score": 0.7,
                        "pair_aspect_compatibility_score": 0.7,
                        "pair_geometry_score": 0.9 if high else 0.2,
                        "descriptor_evidence_conflict_score": 0.1 if high else 0.6,
                        "pf_eri_admissibility_score": 0.9 if high else 0.1,
                        "pf_eri_review_score": 0.9 if high else 0.1,
                        "pf_eri_route": "review" if high else "defer_low_evidence",
                        "claim_boundary": "test",
                    }
                )
            features = root / "features.csv"
            write_csv(features, feature_rows, list(feature_rows[0].keys()))

            audit = build_descriptor_packet(
                descriptor_name="test_descriptor",
                features_csv=features,
                phase18a_manifest=phase18a,
                output_dir=root / "packet",
                sample_size=20,
                random_seed=20260703,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["sample_rows"], 20)
            with (root / "packet/phase18l_descriptor_controlled_review_packet.csv").open(newline="", encoding="utf-8") as handle:
                full_rows = list(csv.DictReader(handle))
            self.assertEqual(sum(row["evidence_group"] == "high_admissibility" for row in full_rows), 10)
            self.assertEqual(sum(row["evidence_group"] == "low_admissibility" for row in full_rows), 10)
            blind_header = (root / "packet/phase18l_blind_review_form.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertNotIn("same_identity_known_id", blind_header)
            self.assertNotIn("pf_eri_admissibility_score", blind_header)
            self.assertNotIn("descriptor_similarity_percentile", blind_header)

    def test_phase18l_descriptor_controlled_analysis_outputs_majority_and_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_root = root / "packet"
            review_root = root / "review"
            for descriptor in ["megadescriptor_l_384", "dinov2_vitl14"]:
                full_rows = []
                for idx in range(4):
                    high = idx % 2 == 0
                    full_rows.append(
                        {
                            "review_pair_id": f"phase18l_{descriptor}_blind_{idx:04d}",
                            "descriptor_name": descriptor,
                            "sample_scope": "test",
                            "match_group_id": f"match_{idx // 2}",
                            "evidence_group": "high_admissibility" if high else "low_admissibility",
                            "query_image_id": f"query_{idx}",
                            "candidate_image_id": f"candidate_{idx}",
                            "query_image_path": f"query_{idx}.jpg",
                            "candidate_image_path": f"candidate_{idx}.jpg",
                            "same_identity_known_id": "yes" if high else "no",
                            "candidate_rank_descriptor": idx + 1,
                            "rank_bin": "rank_01",
                            "descriptor_similarity": 0.9,
                            "descriptor_similarity_percentile": 0.9,
                            "similarity_match_delta": 0.001,
                            "descriptor_evidence_conflict_score": 0.1,
                            "pf_eri_admissibility_score": 0.8 if high else 0.2,
                            "pf_eri_review_score": 0.8 if high else 0.2,
                            "pf_eri_route": "review",
                            "weakest_image_quality_score": 0.7,
                            "pair_geometry_score": 0.8 if high else 0.3,
                            "query_split_role": "evaluation",
                            "reviewability_decision": "",
                            "not_ready_reason": "",
                            "secondary_reason": "",
                            "visibility_notes": "",
                            "reviewer_id": "",
                            "review_timestamp": "",
                            "claim_boundary": "test",
                        }
                    )
                packet_dir = packet_root / descriptor
                write_csv(packet_dir / "phase18l_descriptor_controlled_review_packet.csv", full_rows, list(full_rows[0].keys()))
                for reviewer in ["reviewer1", "reviewer2", "reviewer3"]:
                    working_rows = []
                    for row in full_rows:
                        low = row["evidence_group"] == "low_admissibility"
                        decision = "uncertain" if low else "review_ready"
                        working_rows.append(
                            {
                                "review_pair_id": row["review_pair_id"],
                                "query_image_path": row["query_image_path"],
                                "candidate_image_path": row["candidate_image_path"],
                                "reviewability_decision": decision,
                                "not_ready_reason": "low_evidence" if decision == "not_review_ready" else "",
                                "secondary_reason": "",
                                "visibility_notes": "",
                                "reviewer_id": reviewer,
                                "review_timestamp": "2026-07-04T00:00:00+00:00",
                                "descriptor_name": descriptor,
                            }
                        )
                    review_dir = review_root / reviewer / descriptor
                    write_csv(
                        review_dir / "phase18l_descriptor_controlled_review_working.csv",
                        working_rows,
                        list(working_rows[0].keys()),
                    )

            audit = build_phase18l_descriptor_controlled_analysis(
                packet_root=packet_root,
                review_root=review_root,
                output_dir=root / "analysis",
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["majority_pair_rows"], 8)
            summary_header = (root / "analysis/phase18l_high_low_admissibility_summary.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("risk_difference_low_minus_high", summary_header)
            agreement_header = (root / "analysis/phase18l_reviewer_agreement.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("cohen_kappa", agreement_header)

    def test_phase18m_identity_balanced_packet_balances_identity_cells_and_blinds_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_a = root / "a.jpg"
            image_b = root / "b.jpg"
            Image.new("RGB", (80, 60), color=(120, 100, 80)).save(image_a)
            Image.new("RGB", (90, 70), color=(80, 120, 100)).save(image_b)
            phase18a = root / "phase18a.csv"
            manifest_rows = [
                {"phase18_image_id": f"query_{idx}", "frozen_image_path": str(image_a)}
                for idx in range(10)
            ] + [
                {"phase18_image_id": f"candidate_{idx}", "frozen_image_path": str(image_b)}
                for idx in range(10)
            ]
            write_csv(phase18a, manifest_rows, list(manifest_rows[0].keys()))
            feature_rows = []
            for idx in range(120):
                high = idx % 2 == 0
                same = "yes" if (idx // 2) % 2 == 0 else "no"
                feature_rows.append(
                    {
                        "pair_id": f"pair_{idx}",
                        "descriptor_name": "test_descriptor",
                        "query_image_id": f"query_{idx % 10}",
                        "candidate_image_id": f"candidate_{idx % 10}",
                        "same_identity": same,
                        "candidate_rank_descriptor": (idx % 10) + 1,
                        "descriptor_similarity": 0.8 + (idx % 20) * 0.001,
                        "descriptor_similarity_percentile": 0.8 + (idx % 20) * 0.001,
                        "query_split_role": "evaluation",
                        "split_id": 1,
                        "query_image_quality_score": 0.7,
                        "candidate_image_quality_score": 0.7,
                        "weakest_image_quality_score": 0.7,
                        "pair_size_compatibility_score": 0.7,
                        "pair_aspect_compatibility_score": 0.7,
                        "pair_geometry_score": 0.9 if high else 0.2,
                        "descriptor_evidence_conflict_score": 0.1 if high else 0.6,
                        "pf_eri_admissibility_score": 0.9 if high else 0.1,
                        "pf_eri_review_score": 0.9 if high else 0.1,
                        "pf_eri_route": "review" if high else "defer_low_evidence",
                        "claim_boundary": "test",
                    }
                )
            features = root / "features.csv"
            write_csv(features, feature_rows, list(feature_rows[0].keys()))

            audit = build_descriptor_identity_balanced_packet(
                descriptor_name="test_descriptor",
                features_csv=features,
                phase18a_manifest=phase18a,
                output_dir=root / "packet",
                pairs_per_identity_cell=5,
                random_seed=20260704,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["sample_rows"], 20)
            with (root / "packet/phase18m_identity_balanced_review_packet.csv").open(newline="", encoding="utf-8") as handle:
                full_rows = list(csv.DictReader(handle))
            counts = Counter((row["identity_stratum"], row["evidence_group"]) for row in full_rows)
            self.assertEqual(counts[("same_identity", "high_admissibility")], 5)
            self.assertEqual(counts[("same_identity", "low_admissibility")], 5)
            self.assertEqual(counts[("different_identity", "high_admissibility")], 5)
            self.assertEqual(counts[("different_identity", "low_admissibility")], 5)
            blind_header = (root / "packet/phase18m_blind_review_form.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertNotIn("same_identity_known_id", blind_header)
            self.assertNotIn("identity_stratum", blind_header)
            self.assertNotIn("pf_eri_admissibility_score", blind_header)

    def test_phase18m_identity_balanced_analysis_outputs_stratified_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_root = root / "packet"
            review_root = root / "review"
            for descriptor in ["megadescriptor_l_384", "dinov2_vitl14"]:
                full_rows = []
                idx = 0
                for identity_stratum, same in [("same_identity", "yes"), ("different_identity", "no")]:
                    for match_idx in range(4):
                        for evidence_group in ["high_admissibility", "low_admissibility"]:
                            high = evidence_group == "high_admissibility"
                            full_rows.append(
                                {
                                    "review_pair_id": f"phase18m_{descriptor}_blind_{idx:04d}",
                                    "descriptor_name": descriptor,
                                    "sample_scope": "test",
                                    "identity_stratum": identity_stratum,
                                    "evidence_group": evidence_group,
                                    "match_group_id": f"{identity_stratum}_match_{match_idx}",
                                    "query_image_id": f"query_{idx}",
                                    "candidate_image_id": f"candidate_{idx}",
                                    "query_image_path": f"query_{idx}.jpg",
                                    "candidate_image_path": f"candidate_{idx}.jpg",
                                    "same_identity_known_id": same,
                                    "candidate_rank_descriptor": idx + 1,
                                    "rank_bin": "rank_01",
                                    "descriptor_similarity": 0.9,
                                    "descriptor_similarity_percentile": 0.9,
                                    "similarity_match_delta": 0.001,
                                    "descriptor_evidence_conflict_score": 0.1,
                                    "pf_eri_admissibility_score": 0.8 if high else 0.2,
                                    "pf_eri_review_score": 0.8 if high else 0.2,
                                    "pf_eri_route": "review",
                                    "weakest_image_quality_score": 0.7,
                                    "pair_geometry_score": 0.8 if high else 0.3,
                                    "query_split_role": "evaluation",
                                    "reviewability_decision": "",
                                    "not_ready_reason": "",
                                    "secondary_reason": "",
                                    "visibility_notes": "",
                                    "reviewer_id": "",
                                    "review_timestamp": "",
                                    "claim_boundary": "test",
                                }
                            )
                            idx += 1
                packet_dir = packet_root / descriptor
                write_csv(packet_dir / "phase18m_identity_balanced_review_packet.csv", full_rows, list(full_rows[0].keys()))
                for reviewer in ["reviewer1", "reviewer2", "reviewer3"]:
                    working_rows = []
                    for row in full_rows:
                        low = row["evidence_group"] == "low_admissibility"
                        decision = "uncertain" if low else "review_ready"
                        working_rows.append(
                            {
                                "review_pair_id": row["review_pair_id"],
                                "query_image_path": row["query_image_path"],
                                "candidate_image_path": row["candidate_image_path"],
                                "reviewability_decision": decision,
                                "not_ready_reason": "",
                                "secondary_reason": "",
                                "visibility_notes": "",
                                "reviewer_id": reviewer,
                                "review_timestamp": "2026-07-04T00:00:00+00:00",
                                "descriptor_name": descriptor,
                            }
                        )
                    review_dir = review_root / reviewer / descriptor
                    write_csv(
                        review_dir / "phase18m_identity_balanced_review_working.csv",
                        working_rows,
                        list(working_rows[0].keys()),
                    )

            audit = build_phase18m_identity_balanced_analysis(
                packet_root=packet_root,
                review_root=review_root,
                output_dir=root / "analysis",
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["majority_pair_rows"], 32)
            summary_header = (root / "analysis/phase18m_identity_stratified_summary.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("identity_stratum", summary_header)
            gate_text = (root / "analysis/phase18m_claim_gate.csv").read_text(encoding="utf-8")
            self.assertIn("same_identity", gate_text)
            self.assertIn("different_identity", gate_text)

    def test_phase18n_confirmatory_packet_stratifies_and_blinds_review_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_a = root / "a.jpg"
            image_b = root / "b.jpg"
            Image.new("RGB", (80, 60), color=(120, 100, 80)).save(image_a)
            Image.new("RGB", (90, 70), color=(80, 120, 100)).save(image_b)
            phase18a = root / "phase18a.csv"
            manifest_rows = [
                {"phase18_image_id": f"query_{idx}", "frozen_image_path": str(image_a)}
                for idx in range(12)
            ] + [
                {"phase18_image_id": f"candidate_{idx}", "frozen_image_path": str(image_b)}
                for idx in range(12)
            ]
            write_csv(phase18a, manifest_rows, list(manifest_rows[0].keys()))
            feature_rows = []
            for idx in range(240):
                feature_rows.append(
                    {
                        "pair_id": f"pair_{idx}",
                        "descriptor_name": "test_descriptor",
                        "query_image_id": f"query_{idx % 12}",
                        "candidate_image_id": f"candidate_{(idx * 5) % 12}",
                        "same_identity": "yes" if idx % 3 == 0 else "no",
                        "candidate_rank_descriptor": (idx % 20) + 1,
                        "descriptor_similarity": 0.25 + (idx % 100) / 150.0,
                        "descriptor_similarity_percentile": (idx % 100) / 99.0,
                        "query_split_role": "evaluation",
                        "split_id": 1,
                        "query_image_quality_score": 0.3 + (idx % 7) / 10.0,
                        "candidate_image_quality_score": 0.35 + (idx % 5) / 10.0,
                        "weakest_image_quality_score": 0.25 + (idx % 9) / 12.0,
                        "pair_size_compatibility_score": 0.5,
                        "pair_aspect_compatibility_score": 0.6,
                        "pair_geometry_score": 0.2 + (idx % 11) / 12.0,
                        "descriptor_evidence_conflict_score": 0.1 + (idx % 13) / 20.0,
                        "pf_eri_admissibility_score": 0.1 + (idx % 17) / 20.0,
                        "pf_eri_review_score": 0.2 + (idx % 19) / 20.0,
                        "pf_eri_route": "review" if idx % 2 == 0 else "defer_low_evidence",
                        "claim_boundary": "test",
                    }
                )
            features = root / "features.csv"
            write_csv(features, feature_rows, list(feature_rows[0].keys()))

            audit = build_descriptor_confirmatory_packet(
                descriptor_name="test_descriptor",
                features_csv=features,
                phase18a_manifest=phase18a,
                output_dir=root / "packet",
                sample_size=60,
                reviewer_count=3,
                random_seed=20260710,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["sample_rows"], 60)
            self.assertGreater(audit["stratum_count"], 1)
            blind_header = (root / "packet/phase18n_blind_review_form.csv").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            self.assertIn("reviewability_decision", blind_header)
            self.assertIn("review_confidence", blind_header)
            self.assertNotIn("descriptor_name", blind_header)
            self.assertNotIn("same_identity_known_id", blind_header)
            self.assertNotIn("pf_eri_admissibility_score", blind_header)
            for reviewer_idx in range(1, 4):
                reviewer_path = root / f"packet/reviewer_{reviewer_idx}_blind_review_form.csv"
                self.assertTrue(reviewer_path.exists())
                with reviewer_path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(rows[0]["reviewer_id"], f"reviewer_{reviewer_idx}")


if __name__ == "__main__":
    unittest.main()
