import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_phase16g_pair_feature_schema import build_schema, write_schema


class Phase16GPairFeatureSchemaTest(unittest.TestCase):
    def test_schema_contains_required_groups_and_columns(self):
        schema = build_schema()
        groups = {group["name"]: group for group in schema["column_groups"]}

        self.assertIn("image_evidence_features", groups)
        self.assertIn("pair_comparability_features", groups)
        self.assertIn("descriptor_features", groups)
        self.assertIn("conflict_features", groups)
        self.assertIn("label_fields", groups)
        self.assertIn("split_fields", groups)

        all_columns = {
            column
            for group in schema["column_groups"]
            for column in group["columns"]
        }
        for required in [
            "pair_id",
            "query_image_id",
            "candidate_image_id",
            "descriptor_similarity",
            "descriptor_evidence_conflict_flag",
            "same_identity_label",
            "label_allowed_for_modeling",
            "split_group",
        ]:
            self.assertIn(required, all_columns)

    def test_write_schema_outputs_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "schema.json"
            write_schema(output)
            loaded = json.loads(output.read_text())
            self.assertEqual(loaded["phase"], "Phase16G")
            self.assertEqual(loaded["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
