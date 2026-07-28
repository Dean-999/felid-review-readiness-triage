from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_pferi_v2_manuscript_source_manifest as manifest


class ManuscriptSourceManifestTest(unittest.TestCase):
    def test_builds_hash_bound_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "pferi_v2"
            audit = manifest.build(output_directory=output)
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["source_count"], 26)
            self.assertEqual(audit["claim_count"], 11)
            self.assertTrue((output / "CHECKSUMS.sha256").is_file())

            rows = manifest.read_csv(output / "evidence_source_manifest.csv")
            by_id = {row["source_id"]: row for row in rows}
            self.assertEqual(by_id["TASK15I_PAIR_LABELS"]["data_row_count"], "1600")
            self.assertEqual(by_id["TASK15M_SUPPORTED_PAIRS"]["data_row_count"], "252")
            self.assertEqual(by_id["TASK15M_UNSUPPORTED_PAIRS"]["data_row_count"], "637")
            self.assertTrue(all(row["hash_match"] == "true" for row in rows))

    def test_rejects_hash_drift(self) -> None:
        contract = manifest.read_json(manifest.CONTRACT)
        contract["sources"][0]["expected_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            contract_path = temporary_path / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "sha256:PROJECT_RULES"):
                manifest.build(contract_path=contract_path, output_directory=temporary_path / "output")

    def test_rejects_unknown_claim_evidence(self) -> None:
        contract = manifest.read_json(manifest.CONTRACT)
        contract["claims"][0]["evidence_ids"].append("MISSING_EVIDENCE")
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            contract_path = temporary_path / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unknown_evidence_id:MISSING_EVIDENCE"):
                manifest.build(contract_path=contract_path, output_directory=temporary_path / "output")


if __name__ == "__main__":
    unittest.main()
