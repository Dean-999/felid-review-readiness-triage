from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts import build_v2_pre_sampling_exclusion_register as exclusions


def write_source(path: Path, pair_ids: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["canonical_pair_id"])
        writer.writeheader()
        writer.writerows({"canonical_pair_id": pair_id} for pair_id in pair_ids)


class PreSamplingExclusionRegisterTests(unittest.TestCase):
    def test_union_preserves_reasons_and_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory(dir=exclusions.ROOT) as directory:
            root = Path(directory)
            first = root / "first.csv"
            second = root / "second.csv"
            write_source(first, ["pair_a", "pair_b"])
            write_source(second, ["pair_b", "pair_c"])
            rows, audit = exclusions.build_exclusion_rows(
                [
                    exclusions.ExclusionSource("pilot", first),
                    exclusions.ExclusionSource("rehearsal", second),
                ],
                valid_canonical_pair_ids={"pair_a", "pair_b", "pair_c"},
            )
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["excluded_unique_pair_count"], 3)
        pair_b = next(row for row in rows if row["canonical_pair_id"] == "pair_b")
        self.assertEqual(pair_b["exclusion_reason_codes"], "pilot;rehearsal")
        self.assertEqual(pair_b["source_artifact_count"], 2)

    def test_repeated_version_rows_are_not_double_counted(self) -> None:
        with tempfile.TemporaryDirectory(dir=exclusions.ROOT) as directory:
            source = Path(directory) / "source.csv"
            write_source(source, ["pair_a", "pair_a"])
            rows, audit = exclusions.build_exclusion_rows(
                [exclusions.ExclusionSource("dry_run", source)],
                valid_canonical_pair_ids={"pair_a"},
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(audit["duplicate_or_repeated_source_occurrence_count"], 1)

    def test_unknown_pair_forces_fail(self) -> None:
        with tempfile.TemporaryDirectory(dir=exclusions.ROOT) as directory:
            source = Path(directory) / "source.csv"
            write_source(source, ["pair_unknown"])
            _, audit = exclusions.build_exclusion_rows(
                [exclusions.ExclusionSource("pilot", source)],
                valid_canonical_pair_ids={"pair_known"},
            )
        self.assertEqual(audit["status"], "FAIL")
        self.assertEqual(audit["missing_from_canonical_pair_manifest"], ["pair_unknown"])


if __name__ == "__main__":
    unittest.main()
