from dataclasses import dataclass, field


@dataclass
class Tenant:

    name: str = ""
    nric: str = ""
    address: str = ""


@dataclass
class FormData:

    agreement_date: str = ""

    tenant1: Tenant = field(default_factory=Tenant)
    tenant2: Tenant = field(default_factory=Tenant)
    tenant3: Tenant = field(default_factory=Tenant)
    tenant4: Tenant = field(default_factory=Tenant)

    property_address: str = ""

    lease_term: str = ""

    commission_term: str = ""

    renew_commission: str = ""

    additional_term: str = ""
