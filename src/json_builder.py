from pathlib import Path
from document_reader import read_document
from pdf_helper import pdf_to_images


def build_form_data():

    input_dir = Path("input")

    identities = []

    for file in input_dir.iterdir():

        suffix = file.suffix.lower()

        # Image
        if suffix in [".jpg", ".jpeg", ".png"]:

            doc = read_document(str(file))
            print(doc)

            if doc["document_type"] in ["Passport", "NRIC", "FIN"]:
                identities.append(doc)

        # PDF
        elif suffix == ".pdf":

            pages = pdf_to_images(file)

            for page in pages:

                doc = read_document(str(page))
                print(doc)

                if doc["document_type"] in ["Passport", "NRIC", "FIN"]:
                    identities.append(doc)

    return {

        "agreement_date": "30/07/2026",

        "tenant1_name": identities[0]["name"] if len(identities) >= 1 else "",
        "tenant1_nric": identities[0]["id_number"] if len(identities) >= 1 else "",

        "tenant2_name": identities[1]["name"] if len(identities) >= 2 else "",
        "tenant2_nric": identities[1]["id_number"] if len(identities) >= 2 else "",

        "tenant3_name": identities[2]["name"] if len(identities) >= 3 else "",
        "tenant3_nric": identities[2]["id_number"] if len(identities) >= 3 else "",

        "tenant4_name": identities[3]["name"] if len(identities) >= 4 else "",
        "tenant4_nric": identities[3]["id_number"] if len(identities) >= 4 else "",

        "property_address": "123 Main Street",

        "lease_term": "24",

        "commission_term": "1",

        "renew_commission": "0.5",

        "additional_term": ""
    }