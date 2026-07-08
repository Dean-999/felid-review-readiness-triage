from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_online_reason_label_supplement as supplement


class OnlineReasonLabelSupplementTests(unittest.TestCase):
    def test_normalize_inat_photo_url_uses_large_image(self) -> None:
        self.assertEqual(
            supplement.normalize_inat_photo_url({"url": "https://static.inaturalist.org/photos/1/square.jpg"}),
            "https://static.inaturalist.org/photos/1/large.jpg",
        )

    def test_build_pairs_requires_successfully_downloaded_images(self) -> None:
        rows = [
            {
                "online_image_id": f"img_{idx}",
                "online_source_slice": "bobcat_inat_research_cc",
                "species": "bobcat",
                "domain_label": "heterogeneous_handheld_external",
                "source_image_path": f"data/img_{idx}.jpg",
                "source_image_uri": f"https://example.test/img_{idx}.jpg",
                "source_record_uri": f"https://example.test/obs/{idx}",
                "license": "cc-by-nc",
                "attribution": "tester",
                "source_candidate_id": f"candidate_{idx}",
                "download_status": "ok" if idx < 4 else "failed",
            }
            for idx in range(6)
        ]

        pairs = supplement.build_pairs(rows, {"bobcat_inat_research_cc": 3})

        self.assertEqual(len(pairs), 2)
        self.assertTrue(all("not identity-labeled" in row["claim_boundary"] for row in pairs))

    def test_build_inat_rows_filters_non_cc_photo_license(self) -> None:
        fake_response = {
            "total_results": 1,
            "results": [
                {
                    "id": 11,
                    "photos": [
                        {"id": 1, "url": "https://static.inaturalist.org/photos/1/square.jpg", "license_code": "cc-by"},
                        {"id": 2, "url": "https://static.inaturalist.org/photos/2/square.jpg", "license_code": "all-rights-reserved"},
                    ],
                }
            ],
        }

        with patch.object(supplement, "request_json", return_value=fake_response):
            rows = supplement.build_inat_rows(
                online_source_slice="bobcat_inat_research_cc",
                taxon_id=41976,
                species="bobcat",
                domain_label="heterogeneous_handheld_external",
                quality_grade="research",
                limit_images=10,
                selection_basis="test",
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["license"], "cc-by")
        self.assertEqual(rows[0]["source_record_uri"], "https://www.inaturalist.org/observations/11")

    def test_build_writes_separate_outputs_with_mocked_sources(self) -> None:
        fake_rows = [
            {
                "online_image_id": f"bobcat_inat_research_cc_{idx:05d}",
                "online_source_slice": "bobcat_inat_research_cc",
                "species": "bobcat",
                "domain_label": "heterogeneous_handheld_external",
                "source_dataset": "iNaturalist",
                "source_platform": "iNaturalist",
                "source_candidate_id": f"candidate_{idx}",
                "source_record_uri": f"https://example.test/obs/{idx}",
                "source_image_uri": f"https://example.test/img_{idx}.jpg",
                "source_image_path": f"data/img_{idx}.jpg",
                "license": "cc-by-nc",
                "attribution": "tester",
                "selection_basis": "test",
                "download_status": "ok",
                "bytes": "1234",
                "download_error": "",
            }
            for idx in range(4)
        ]
        args = argparse.Namespace(
            bobcat_inat_pairs=2,
            wsu_pairs=0,
            eurasian_lynx_inat_pairs=0,
            challenge_pairs=0,
            workers=1,
            metadata_only=False,
            skip_wsu=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(supplement, "OUTPUT_DIR", Path(tmp) / "outputs"):
                with patch.object(supplement, "build_source_rows", return_value=fake_rows):
                    with patch.object(supplement, "download_rows", return_value=fake_rows):
                        audit = supplement.build(args)

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["review_pair_rows"], 2)
            self.assertTrue((Path(tmp) / "outputs" / "online_reason_label_review_queue.csv").exists())


if __name__ == "__main__":
    unittest.main()
