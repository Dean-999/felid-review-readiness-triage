from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


HAS_STREAMLIT_DEPS = importlib.util.find_spec("pandas") is not None and importlib.util.find_spec("streamlit") is not None


if HAS_STREAMLIT_DEPS:
    import pandas as pd

    from scripts.streamlit_pair_review_common import PairReviewConfig, completed_mask, next_pending_id, resolve_path


@unittest.skipUnless(HAS_STREAMLIT_DEPS, "streamlit/pandas not installed in this Python environment")
class StreamlitPairReviewCommonTests(unittest.TestCase):
    def config(self, source: Path, working: Path) -> "PairReviewConfig":
        return PairReviewConfig(
            title="test",
            source_csv=source,
            working_csv=working,
            id_column="row_id",
            query_image_column="query",
            candidate_image_column="candidate",
            status_column="decision",
            decision_columns=("reason", "secondary", "notes"),
            decision_options=("", "yes", "no", "uncertain"),
            reason_column="reason",
            secondary_reason_column="secondary",
            notes_column="notes",
            standards=("standard",),
            reason_options=("", "reason_a"),
            metadata_columns=(),
        )

    def test_completed_mask_uses_nonblank_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self.config(Path(tmp) / "source.csv", Path(tmp) / "working.csv")
            frame = pd.DataFrame({"decision": ["", "yes", "no", "uncertain", "defer"]})

            self.assertEqual(completed_mask(cfg, frame).tolist(), [False, True, True, True, False])

    def test_next_pending_id_advances_within_filtered_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self.config(Path(tmp) / "source.csv", Path(tmp) / "working.csv")
            frame = pd.DataFrame({"row_id": ["a", "b", "c"], "decision": ["yes", "", ""]})

            self.assertEqual(next_pending_id(cfg, frame, ["a", "b", "c"], "a"), "b")
            self.assertEqual(next_pending_id(cfg, frame, ["a", "b", "c"], "b"), "c")

    def test_resolve_path_keeps_absolute_paths(self) -> None:
        path = Path("/tmp/example.jpg")
        self.assertEqual(resolve_path(str(path)), path)


if __name__ == "__main__":
    unittest.main()
