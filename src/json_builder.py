from pathlib import Path

from document_reader import analyze_document_bytes, read_document, read_document_bytes
from form_rules import default_commission, singapore_today
from pdf_helper import pdf_to_image_bytes


FORM_FIELDS = (
    "agreement_date",
    "tenant1_name",
    "tenant1_nric",
    "tenant2_name",
    "tenant2_nric",
    "tenant3_name",
    "tenant3_nric",
    "tenant4_name",
    "tenant4_nric",
    "property_address",
    "lease_term",
    "commission_term",
    "renew_commission",
    "additional_term",
)
IDENTITY_TYPES = {"Passport", "NRIC", "FIN"}


def empty_form_data():
    form_data = {field: "" for field in FORM_FIELDS}
    form_data.update(
        agreement_date=singapore_today(),
        lease_term="12",
        commission_term=default_commission(12),
        renew_commission="0.5",
    )
    return form_data


def form_data_from_identities(identities):
    """Map up to four extracted identities to an otherwise blank form."""

    form_data = empty_form_data()
    for index, identity in enumerate(identities[:4], start=1):
        form_data[f"tenant{index}_name"] = identity.get("name", "")
        form_data[f"tenant{index}_nric"] = identity.get("id_number", "")
    return form_data


def extract_uploaded_documents(documents, reader=read_document_bytes):
    """Extract identities from in-memory `(name, bytes)` upload tuples."""

    identities = []
    for name, content in documents:
        suffix = Path(name).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png"}:
            mime_type = "image/png" if suffix == ".png" else "image/jpeg"
            results = [reader(content, mime_type)]
        elif suffix == ".pdf":
            results = [reader(page, "image/png") for page in pdf_to_image_bytes(content)]
        else:
            raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

        identities.extend(
            result for result in results if result.get("document_type") in IDENTITY_TYPES
        )

    return identities


def analyze_uploaded_documents(documents, reader=analyze_document_bytes):
    """Classify uploads and collect tenants, an address, or a signed Form 4."""

    analyses = []
    for name, content in documents:
        suffix = Path(name).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png"}:
            mime_type = "image/png" if suffix == ".png" else "image/jpeg"
            page = content
        elif suffix == ".pdf":
            pages = pdf_to_image_bytes(content)
            if not pages:
                raise ValueError("The PDF has no readable pages.")
            page = pages[0]
            mime_type = "image/png"
        else:
            raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
        analyses.append(reader(page, mime_type))

    is_form4 = len(documents) == 1 and analyses[0]["document_type"] == "Form4"
    identities = [
        item for item in analyses if item["document_type"] in IDENTITY_TYPES
    ][:4]
    property_address = next(
        (item["property_address"] for item in analyses if item["property_address"]),
        "",
    )
    return {
        "is_form4": is_form4,
        "identities": identities,
        "property_address": property_address,
    }


def build_form_data(input_dir="input"):
    """Legacy local-file workflow used by the CLI, with no hard-coded values."""

    identities = []
    directory = Path(input_dir)
    if not directory.exists():
        return empty_form_data()

    for file in sorted(directory.iterdir()):
        suffix = file.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png"}:
            results = [read_document(str(file))]
        elif suffix == ".pdf":
            results = [
                read_document_bytes(page, "image/png")
                for page in pdf_to_image_bytes(file.read_bytes())
            ]
        else:
            continue

        identities.extend(
            result for result in results if result.get("document_type") in IDENTITY_TYPES
        )

    return form_data_from_identities(identities)
