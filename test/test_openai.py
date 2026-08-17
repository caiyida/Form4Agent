"""Hermetic tests for OpenAI response normalization."""

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from document_reader import (  # noqa: E402
    DocumentExtractionError,
    ExtractedIdentity,
    read_document_bytes,
)


class FakeResponses:
    def __init__(self, output_parsed=None, error=None):
        self.output_parsed = output_parsed
        self.error = error

    def parse(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(output_parsed=self.output_parsed)


class DocumentReaderTests(unittest.TestCase):
    def fake_client(self, output_parsed=None, error=None):
        return SimpleNamespace(responses=FakeResponses(output_parsed, error))

    def test_normalizes_valid_structured_response(self):
        client = self.fake_client(
            ExtractedIdentity(
                document_type="Passport", name=" Test User ", id_number=" P123 "
            )
        )

        result = read_document_bytes(b"synthetic", "image/jpeg", client=client)

        self.assertEqual(
            result,
            {"document_type": "Passport", "name": "Test User", "id_number": "P123"},
        )

    def test_unknown_classification_is_preserved(self):
        client = self.fake_client(
            ExtractedIdentity(
                document_type="Unknown", name="Test", id_number="123"
            )
        )

        result = read_document_bytes(b"synthetic", "image/png", client=client)

        self.assertEqual(result["document_type"], "Unknown")

    def test_missing_parsed_output_raises_safe_error(self):
        client = self.fake_client(None)

        with self.assertRaises(DocumentExtractionError):
            read_document_bytes(b"synthetic", "image/jpeg", client=client)

    def test_api_error_does_not_leak_provider_details(self):
        client = self.fake_client(error=RuntimeError("secret provider response"))

        with self.assertRaisesRegex(
            DocumentExtractionError, "could not process this document"
        ) as raised:
            read_document_bytes(b"synthetic", "image/jpeg", client=client)
        self.assertNotIn("secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
