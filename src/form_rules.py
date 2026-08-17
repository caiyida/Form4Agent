from datetime import datetime
from decimal import Decimal
from math import ceil
from zoneinfo import ZoneInfo


SINGAPORE_TIMEZONE = ZoneInfo("Asia/Singapore")


def singapore_today(now=None):
    """Return the agreement-date default in Singapore local time."""

    current = now or datetime.now(SINGAPORE_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=SINGAPORE_TIMEZONE)
    return current.astimezone(SINGAPORE_TIMEZONE).strftime("%d/%m/%Y")


def commission_months(lease_months):
    """Calculate the default stepped commission in months of rent."""

    try:
        months = int(str(lease_months).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("Lease term must be a whole number of months.") from exc
    if months < 1:
        raise ValueError("Lease term must be at least one month.")
    return Decimal(ceil(months / 12)) * Decimal("0.5")


def format_months(value):
    return format(Decimal(value).normalize(), "f")


def default_commission(lease_months):
    return format_months(commission_months(lease_months))
