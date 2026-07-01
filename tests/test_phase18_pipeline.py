import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.build_phase18b_local_descriptor_control import build_phase18b
from scripts.build_phase18c_czechlynx_pair_contract import build_phase18c
from scripts.build_phase18d_pf_eri_pair_features import build_phase18d
from scripts.build_phase18e_review_router import build_phase18e
from scripts.build_phase18f_bobcat_transfer_readiness import build_phase18f
from scripts.build_phase18g_strong_baseline_claim_gate import build_phase18g


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Phase18PipelineTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
