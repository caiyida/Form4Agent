"""Streamlit smoke tests for the simplified smart-upload workflow."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class AppWorkflowTests(unittest.TestCase):
    def test_single_primary_flow_and_compact_details_editor_render(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(app_path, default_timeout=20).run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(list(app.error), [])
        generate = [button for button in app.button if button.label == "Generate Form 4"]
        self.assertEqual(len(generate), 1)
        self.assertTrue(generate[0].disabled)
        self.assertEqual(
            len([item for item in app.text_input if item.label == "Property address"]),
            1,
        )
        self.assertFalse(any("Tenant 1" in item.label for item in app.text_input))
        self.assertFalse(any("authorize" in item.label.lower() for item in app.checkbox))
        self.assertFalse(
            any(button.label == "Add my signature and initials" for button in app.button)
        )

    def test_pdf_upload_is_accepted_and_enables_generation(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(app_path, default_timeout=20).run()
        app.get("file_uploader")[0].upload(
            "signed-form4.pdf", b"%PDF-1.4 synthetic", "application/pdf"
        )
        app.run()

        self.assertEqual(list(app.exception), [])
        generate = next(
            button for button in app.button if button.label == "Generate Form 4"
        )
        self.assertFalse(generate.disabled)
        self.assertTrue(any("file(s) ready" in item.value for item in app.caption))


if __name__ == "__main__":
    unittest.main()
