"""Hermetic tests for document-to-form mapping."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from json_builder import (  # noqa: E402
    analyze_uploaded_documents,
    empty_form_data,
    extract_uploaded_documents,
    form_data_from_identities,
)


class FormDataTests(unittest.TestCase):
    def test_form_uses_confirmed_defaults_without_property_or_tenants(self):
        form_data = empty_form_data()
        self.assertEqual(form_data["lease_term"], "12")
        self.assertEqual(form_data["commission_term"], "0.5")
        self.assertEqual(form_data["renew_commission"], "0.5")
        self.assertRegex(form_data["agreement_date"], r"^\d{2}/\d{2}/\d{4}$")
        for key in (
            "property_address",
            "additional_term",
            "tenant1_name",
            "tenant1_nric",
        ):
            self.assertEqual(form_data[key], "")

    def test_maps_up_to_four_identities(self):
        identities = [
            {"name": f"Tenant {index}", "id_number": f"ID{index}"}
            for index in range(1, 6)
        ]

        form_data = form_data_from_identities(identities)

        self.assertEqual(form_data["tenant1_name"], "Tenant 1")
        self.assertEqual(form_data["tenant4_nric"], "ID4")
        self.assertNotIn("Tenant 5", form_data.values())
        self.assertEqual(form_data["property_address"], "")

    def test_extracts_supported_images_without_network_calls(self):
        calls = []

        def fake_reader(content, mime_type):
            calls.append((content, mime_type))
            return {"document_type": "NRIC", "name": "Test", "id_number": "S000"}

        identities = extract_uploaded_documents(
            [("identity.png", b"synthetic-image")], reader=fake_reader
        )

        self.assertEqual(len(identities), 1)
        self.assertEqual(calls, [(b"synthetic-image", "image/png")])

    def test_rejects_unsupported_upload_types(self):
        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            extract_uploaded_documents([("identity.txt", b"not-an-image")])

    def test_smart_analysis_collects_identities_and_property(self):
        results = iter(
            [
                {
                    "document_type": "NRIC",
                    "name": "Synthetic Tenant",
                    "id_number": "TEST123",
                    "property_address": "",
                },
                {
                    "document_type": "Property",
                    "name": "",
                    "id_number": "",
                    "property_address": "1 Test Street, Singapore 000001",
                },
            ]
        )

        analysis = analyze_uploaded_documents(
            [("id.png", b"id"), ("address.jpg", b"address")],
            reader=lambda content, mime_type: next(results),
        )

        self.assertFalse(analysis["is_form4"])
        self.assertEqual(len(analysis["identities"]), 1)
        self.assertEqual(
            analysis["property_address"], "1 Test Street, Singapore 000001"
        )

    def test_only_one_recognised_form4_selects_signing_flow(self):
        analysis = analyze_uploaded_documents(
            [("complete.jpg", b"form")],
            reader=lambda content, mime_type: {
                "document_type": "Form4",
                "name": "",
                "id_number": "",
                "property_address": "",
            },
        )
        self.assertTrue(analysis["is_form4"])


if __name__ == "__main__":
    unittest.main()
