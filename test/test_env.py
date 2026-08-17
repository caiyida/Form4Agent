"""Configuration tests that never read or print credentials."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import config  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_project_paths_are_rooted_in_repository(self):
        self.assertEqual(config.PROJECT_ROOT, PROJECT_ROOT)
        self.assertEqual(config.FORM4_TEMPLATE.parent, PROJECT_ROOT / "templates")
        self.assertEqual(config.INPUT_DIR, PROJECT_ROOT / "input")
        self.assertEqual(config.OUTPUT_DIR, PROJECT_ROOT / "output")


if __name__ == "__main__":
    unittest.main()
