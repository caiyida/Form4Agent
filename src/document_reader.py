import base64
from typing import Literal
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png"}


class DocumentExtractionError(RuntimeError):
    """Raised when an identity document cannot be extracted safely."""


class ExtractedIdentity(BaseModel):
    document_type: Literal["Passport", "NRIC", "FIN", "Unknown"]
    name: str
    id_number: str


class UploadedDocumentAnalysis(BaseModel):
    document_type: Literal["Passport", "NRIC", "FIN", "Property", "Form4", "Unknown"]
    name: str
    id_number: str
    property_address: str


def read_document_bytes(content: bytes, mime_type: str, client=None):
    """
    Read one identity-document image and return normalized structured data.
    """

    if not content:
        raise DocumentExtractionError("The document image is empty.")
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise DocumentExtractionError(f"Unsupported image type: {mime_type}")

    image_base64 = base64.b64encode(content).decode("utf-8")
    api_client = client or OpenAI()

    try:
        response = api_client.responses.parse(
            model="gpt-5.5",
            text_format=ExtractedIdentity,
            store=False,
            timeout=60,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": """
Extract information from this document.

First determine the document type.

Supported document types:

- Passport
- Singapore NRIC
- Singapore FIN (including digital ICA / MOM passes)
- Unknown

Return ONLY valid JSON.

{
    "document_type": "",
    "name": "",
    "id_number": ""
}

Classification Rules:

1. Passport
- Any country's passport.
- document_type = "Passport"

2. Singapore NRIC
- Pink or blue NRIC.
- document_type = "NRIC"

3. Singapore FIN

This includes ANY Singapore immigration pass containing a FIN number, including:

- Employment Pass
- S Pass
- Work Permit
- Student Pass
- Dependant's Pass
- Long-Term Visit Pass (LTVP)

The document may be:

- Physical card
- ICA e-Pass screenshot
- ICA mobile app screenshot
- MOM app screenshot

If you see any of these titles:

- LONG TERM VISIT PASS
- DEPENDANT'S PASS
- STUDENT PASS
- EMPLOYMENT PASS
- S PASS
- WORK PERMIT

Then:

document_type = "FIN"

For Passport / NRIC / FIN:

name = Full name

id_number = Passport / NRIC / FIN number

If this is NOT an identity document:

document_type = "Unknown"

name = ""

id_number = ""

Return empty string if you are not confident.

Only return valid JSON.

Do not explain.

Do not use markdown.
"""
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_base64}",
                        },
                    ],
                }
            ],
        )
    except Exception as exc:
        raise DocumentExtractionError(
            "The extraction service could not process this document."
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise DocumentExtractionError("The extraction service returned no usable data.")

    return {
        "document_type": parsed.document_type,
        "name": parsed.name.strip(),
        "id_number": parsed.id_number.strip(),
    }


def analyze_document_bytes(content: bytes, mime_type: str, client=None):
    """Classify an upload and extract only fields needed by the Form 4 flow."""

    if not content:
        raise DocumentExtractionError("The uploaded image is empty.")
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise DocumentExtractionError(f"Unsupported image type: {mime_type}")

    image_base64 = base64.b64encode(content).decode("utf-8")
    api_client = client or OpenAI()
    try:
        response = api_client.responses.parse(
            model="gpt-5.5",
            text_format=UploadedDocumentAnalysis,
            store=False,
            timeout=60,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Classify this image as Passport, Singapore NRIC, "
                                "Singapore FIN/pass, Property, Form4, or Unknown. "
                                "Use Form4 only when the content is recognisably a CEA "
                                "Form 4 estate agency agreement. For an identity document, "
                                "extract the full name and identity number. For a property "
                                "listing, tenancy screenshot, message, document, or Form 4, "
                                "extract the complete Singapore property address when clearly "
                                "visible. Return empty strings for fields that are absent or "
                                "uncertain. Do not infer or invent any value."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_base64}",
                        },
                    ],
                }
            ],
        )
    except Exception as exc:
        raise DocumentExtractionError(
            "The extraction service could not analyse this upload."
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise DocumentExtractionError("The extraction service returned no usable data.")
    return {
        "document_type": parsed.document_type,
        "name": parsed.name.strip(),
        "id_number": parsed.id_number.strip(),
        "property_address": parsed.property_address.strip(),
    }


def read_document(image_path: str, client=None):
    """Read an identity document image from a local path."""

    path = Path(image_path)
    mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

    try:
        content = path.read_bytes()
    except OSError as exc:
        raise DocumentExtractionError("The document image could not be read.") from exc

    return read_document_bytes(content, mime_type, client=client)
