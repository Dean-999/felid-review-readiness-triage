from __future__ import annotations
import unittest
from scripts import build_v2_descriptor_execution_manifest as manifest

class DescriptorExecutionManifestTests(unittest.TestCase):
    def test_rejects_unavailable_source_image(self) -> None:
        with self.assertRaises(ValueError):
            manifest.build([{"species":"czechlynx", "final_freeze_image_exists":"no", "decode_status":"ok"}])

if __name__ == "__main__":
    unittest.main()
