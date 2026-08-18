from io import BytesIO
from pathlib import Path
import sys
import unittest

import pymupdf as fitz
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pdf_helper import (  # noqa: E402
    images_to_pdf_bytes,
    pdf_first_page_image_bytes,
    signed_upload_to_pdf,
    stamp_agent_marks,
)


def synthetic_image(width=600, height=900):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, "PNG")
    return output.getvalue()


class PdfHelperTests(unittest.TestCase):
    def test_classification_renders_only_the_first_pdf_page(self):
        source = images_to_pdf_bytes([synthetic_image(), synthetic_image()])
        first_page = pdf_first_page_image_bytes(source)
        with Image.open(BytesIO(first_page)) as image:
            self.assertGreater(image.width, 0)
            self.assertGreater(image.height, 0)

    def test_ordered_images_become_complete_seven_page_pdf(self):
        pages = [(f"page-{number}.png", synthetic_image()) for number in range(7)]
        result = signed_upload_to_pdf(pages, expected_pages=7)
        with fitz.open(stream=result, filetype="pdf") as document:
            self.assertEqual(document.page_count, 7)
            self.assertAlmostEqual(document[0].rect.width, 595)

    def test_rejects_incomplete_pdf(self):
        result = images_to_pdf_bytes([synthetic_image()])
        with self.assertRaisesRegex(ValueError, "must have 7 pages"):
            signed_upload_to_pdf([("signed.pdf", result)], expected_pages=7)

    def test_rejects_mixed_uploads(self):
        with self.assertRaisesRegex(ValueError, "one PDF or an ordered set"):
            signed_upload_to_pdf(
                [("signed.pdf", b"not-a-pdf"), ("page.png", synthetic_image())]
            )

    def test_signing_does_not_require_an_exact_page_count(self):
        result = images_to_pdf_bytes([synthetic_image()])
        self.assertEqual(signed_upload_to_pdf([("signed.pdf", result)]), result)

    def test_stamps_explicitly_verified_placements(self):
        source = images_to_pdf_bytes([synthetic_image()])
        placements = [
            ("initials", 0, fitz.Rect(480, 45, 520, 65)),
            ("signature", 0, fitz.Rect(170, 600, 260, 635)),
        ]
        result = stamp_agent_marks(source, placements=placements)
        with fitz.open(stream=result, filetype="pdf") as document:
            self.assertGreaterEqual(len(document[0].get_images()), 3)


if __name__ == "__main__":
    unittest.main()
