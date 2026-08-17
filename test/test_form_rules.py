from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from form_rules import default_commission, singapore_today  # noqa: E402


class FormRulesTests(unittest.TestCase):
    def test_commission_uses_twelve_month_steps(self):
        expected = {1: "0.5", 12: "0.5", 13: "1", 24: "1", 25: "1.5"}
        for months, commission in expected.items():
            with self.subTest(months=months):
                self.assertEqual(default_commission(months), commission)

    def test_commission_rejects_invalid_terms(self):
        for value in ("", "12.5", 0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    default_commission(value)

    def test_today_uses_singapore_timezone(self):
        utc_time = datetime(2026, 8, 17, 16, 30, tzinfo=timezone.utc)
        self.assertEqual(singapore_today(utc_time), "18/08/2026")


if __name__ == "__main__":
    unittest.main()
