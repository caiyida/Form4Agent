import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()


def read_document(image_path: str):
    """
    Read identity document and return structured JSON.
    """

    image_path = Path(image_path)

    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    # Detect image type
    suffix = image_path.suffix.lower()

    if suffix == ".png":
        mime_type = "image/png"
    else:
        mime_type = "image/jpeg"

    response = client.responses.create(
        model="gpt-5.5",
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
                    }
                ]
            }
        ]
    )

    return json.loads(response.output_text)