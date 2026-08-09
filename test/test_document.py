from ..src.document_reader import read_document

doc = read_document("input/passport.jpg")

form_data = {
    "agreement_date": "30/07/2026",

    "tenant1_name": doc["name"],
    "tenant1_nric": doc["id_number"],

    "tenant2_name": "",
    "tenant2_nric": "",

    "tenant3_name": "",
    "tenant3_nric": "",

    "tenant4_name": "",
    "tenant4_nric": "",

    "property_address": "",
    "lease_term": "",
    "commission_term": "",
    "renew_commission": "",
    "additional_term": ""
}

print(form_data)