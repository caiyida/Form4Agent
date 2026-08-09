from dataclasses import dataclass


@dataclass
class Tenant:

    name: str = ""
    nric: str = ""
    address: str = ""


@dataclass
class FormData:

    agreement_date: str = ""

    tenant1: Tenant = Tenant()
    tenant2: Tenant = Tenant()
    tenant3: Tenant = Tenant()
    tenant4: Tenant = Tenant()

    property_address: str = ""

    lease_term: str = ""

    commission_term: str = ""

    renew_commission: str = ""

    additional_term: str = ""