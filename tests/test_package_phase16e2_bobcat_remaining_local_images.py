import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/package_phase16e2_bobcat_remaining_local_images.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("bobcat_package", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BobcatRemainingPackageTests(unittest.TestCase):
    def test_select_target_rows_uses_filtered_iloc_bounds(self):
        module = load_module()
        rows = []
        for i in range(8):
            rows.append(
                {
                    "candidate_id": f"p16e2_bobcat_{i + 1:05d}",
                    "target_quadrant": "urban_bobcat_high_confidence",
                    "source_mode": "url",
                    "image_uri": f"https://example.test/{i}.jpg",
                }
            )
        rows.insert(
            2,
            {
                "candidate_id": "other",
                "target_quadrant": "other",
                "source_mode": "url",
                "image_uri": "https://example.test/other.jpg",
            },
        )

        selected = module.select_target_rows(rows, start_index=2, end_index=5)

        self.assertEqual(
            [row["candidate_id"] for row in selected],
            ["p16e2_bobcat_00003", "p16e2_bobcat_00004", "p16e2_bobcat_00005"],
        )
        self.assertEqual([row["requested_position"] for row in selected], [2, 3, 4])

    def test_runner_ready_rows_rewrite_source_mode_and_keep_original_uri(self):
        module = load_module()
        rows = [
            {
                "candidate_id": "p16e2_bobcat_06001",
                "target_quadrant": "urban_bobcat_high_confidence",
                "source_mode": "url",
                "image_uri": "https://example.test/source.jpg",
                "prefilter_score": "1.25",
                "requested_position": 6000,
            }
        ]
        successes = {"p16e2_bobcat_06001"}

        ready = module.build_runner_ready_rows(rows, successes)

        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0]["source_mode"], "packaged_local")
        self.assertEqual(
            ready[0]["image_uri"],
            "/kaggle/working/extracted_images/images/bobcat/p16e2_bobcat_06001.jpg",
        )
        self.assertEqual(ready[0]["original_image_uri"], "https://example.test/source.jpg")
        self.assertEqual(ready[0]["prefilter_score"], "1.25")

    def test_zip_part_assignment_and_batch_manifest_outputs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images/bobcat"
            image_dir.mkdir(parents=True)
            for name, size in [
                ("p16e2_bobcat_06001", 4),
                ("p16e2_bobcat_06002", 4),
                ("p16e2_bobcat_10001", 4),
            ]:
                (image_dir / f"{name}.jpg").write_bytes(b"x" * size)
            rows = [
                {"candidate_id": "p16e2_bobcat_06001", "requested_position": 6000},
                {"candidate_id": "p16e2_bobcat_06002", "requested_position": 6001},
                {"candidate_id": "p16e2_bobcat_10001", "requested_position": 10000},
            ]

            zip_records = module.write_split_zips(
                rows=rows,
                image_dir=image_dir,
                zip_dir=root / "zips",
                zip_part_size_bytes=8,
            )
            batch_counts = module.write_batch_manifests(
                rows=rows,
                output_dir=root / "batch_manifests",
            )

            self.assertEqual([record["zip_part"] for record in zip_records], [1, 1, 2])
            self.assertEqual(
                sorted(path.name for path in (root / "zips").glob("*.zip")),
                [
                    "phase16e2_bobcat_remaining_images_part_001.zip",
                    "phase16e2_bobcat_remaining_images_part_002.zip",
                ],
            )
            self.assertEqual(batch_counts["bobcat_remaining_local_06000_09999.csv"], 2)
            self.assertEqual(batch_counts["bobcat_remaining_local_10000_13999.csv"], 1)
            with (root / "batch_manifests/bobcat_remaining_local_06000_09999.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 2)


if __name__ == "__main__":
    unittest.main()
