REQUIRED_FIELDS = [
    "agreement_date",
    "tenant1_name",
    "tenant1_nric",
    "property_address",
    "lease_term",
    "commission_term"
]


def validate(form_data):

    missing = []

    for field in REQUIRED_FIELDS:

        value = form_data.get(field, "")

        if value is None or str(value).strip() == "":
            missing.append(field)

    return missing