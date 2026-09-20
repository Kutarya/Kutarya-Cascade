import unittest
from pathlib import Path

from kutarya_cascade.cli import DEFAULT_DATASET


ROOT = Path(__file__).parents[1]
ACKNOWLEDGEMENT = "This product includes software developed by Kutarya."


class PublicationTests(unittest.TestCase):
    def test_license_requires_kutarya_attribution(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("BSD 4-Clause", license_text)
        self.assertIn(ACKNOWLEDGEMENT, license_text)

    def test_notice_repeats_exact_acknowledgement(self):
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertIn(ACKNOWLEDGEMENT, notice)

    def test_default_dataset_is_packaged(self):
        self.assertTrue(DEFAULT_DATASET.is_file(), DEFAULT_DATASET)
        self.assertEqual(len(DEFAULT_DATASET.read_text(encoding="utf-8").splitlines()), 30)

    def test_public_text_does_not_expose_windows_user_profile(self):
        public_files = [
            ROOT / "README.md",
            ROOT / "README_EN.md",
            ROOT / "TEST_REPORT.md",
            ROOT / "results" / "environment_status.json",
        ]
        for path in public_files:
            self.assertNotIn("C:\\Users\\", path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
