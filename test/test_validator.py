"""Tests for required-field validation and normalization."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from validator import normalized_form_data, validate  # noqa: E402


class ValidatorTests(unittest.TestCase):
    def test_whitespace_only_required_values_are_missing(self):
        form_data = {
            "agreement_date": " ",
            "tenant1_name": "Test",
            "tenant1_nric": "ID",
            "property_address": "Address",
            "lease_term": "24",
            "commission_term": "1",
        }

        self.assertEqual(validate(form_data), ["agreement_date"])

    def test_normalization_blanks_none_and_trims_strings(self):
        self.assertEqual(
            normalized_form_data({"name": " Test ", "optional": None}),
            {"name": "Test", "optional": ""},
        )


if __name__ == "__main__":
    unittest.main()
