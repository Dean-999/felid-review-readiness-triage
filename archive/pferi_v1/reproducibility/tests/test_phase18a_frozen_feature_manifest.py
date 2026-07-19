import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.build_phase18a_frozen_feature_manifest import build_phase18a


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


class Phase18AFrozenFeatureManifestTests(unittest.TestCase):
    def test_build_phase18a_preserves_roles_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            image_dir.mkdir()
            bobcat = image_dir / "bobcat.jpg"
            czech = image_dir / "czech.jpg"
            Image.new("RGB", (80, 60), color=(20, 40, 60)).save(bobcat)
            Image.new("RGB", (64, 64), color=(80, 100, 120)).save(czech)

            input_csv = root / "frozen.csv"
            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "species",
                        "freeze_rank",
                        "source_manifest",
                        "source_candidate_id",
                        "source_status",
                        "source_quality_gate",
                        "source_identity_label",
                        "license",
                        "attribution",
                        "frozen_image_path",
                        "frozen_file_name",
                        "decode_status",
                        "image_width",
                        "image_height",
                        "sha256",
                        "bytes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "species": "bobcat",
                        "freeze_rank": "1",
                        "source_manifest": "source.csv",
                        "source_candidate_id": "b1",
                        "source_status": "human_confirmed_clear_seed",
                        "source_quality_gate": "human_confirmed_clear",
                        "source_identity_label": "",
                        "license": "cc-by",
                        "attribution": "tester",
                        "frozen_image_path": str(bobcat),
                        "frozen_file_name": bobcat.name,
                        "decode_status": "ok",
                        "image_width": "80",
                        "image_height": "60",
                        "sha256": sha256_file(bobcat),
                        "bytes": str(bobcat.stat().st_size),
                    }
                )
                writer.writerow(
                    {
                        "species": "czechlynx",
                        "freeze_rank": "2",
                        "source_manifest": "source.csv",
                        "source_candidate_id": "c1",
                        "source_status": "human_clear_augmented_ready_for_freeze",
                        "source_quality_gate": "yes",
                        "source_identity_label": "lynx_001",
                        "license": "",
                        "attribution": "",
                        "frozen_image_path": str(czech),
                        "frozen_file_name": czech.name,
                        "decode_status": "ok",
                        "image_width": "64",
                        "image_height": "64",
                        "sha256": sha256_file(czech),
                        "bytes": str(czech.stat().st_size),
                    }
                )

            output_dir = root / "out"
            audit = build_phase18a(input_csv, output_dir)

            self.assertEqual(audit["output_rows"], 2)
            self.assertEqual(audit["failed_algorithm_entry_count"], 0)
            self.assertEqual(audit["modeling_role_counts"]["bobcat_unlabeled_transfer"], 1)
            self.assertEqual(audit["modeling_role_counts"]["czechlynx_known_id"], 1)

            with (output_dir / "phase18a_frozen_image_feature_manifest.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["train_eval_eligible"], "no")
            self.assertEqual(rows[1]["train_eval_eligible"], "yes")
            self.assertEqual(rows[0]["sha256_verified"], "yes")
            self.assertEqual(rows[1]["decode_status"], "ok")


if __name__ == "__main__":
    unittest.main()
