import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_v2_formal_pair_samples.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_v2_formal_pair_samples", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FormalValidatorTests(unittest.TestCase):
    def test_probability_must_equal_quota_over_capacity(self):
        module = load_module()
        module.validate_probability("2", "4", "0.500000000000")
        with self.assertRaisesRegex(ValueError, "probability mismatch"):
            module.validate_probability("2", "4", "0.400000000000")

    def test_checksum_manifest_detects_changed_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload.txt"
            payload.write_text("original", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            (root / "CHECKSUMS.sha256").write_text(f"{digest}  payload.txt\n", encoding="utf-8")
            module.verify_checksum_manifest(root)
            payload.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                module.verify_checksum_manifest(root)


if __name__ == "__main__":
    unittest.main()
