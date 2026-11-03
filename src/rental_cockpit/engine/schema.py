# Copyright © 2026 Vincent Fournet
"""Registry layout, built-in categories and labels.

The registry is one JSON-serialisable dictionary. Its ``schema`` number is
bumped for every incompatible change and each change gets a migration (see
``migrations.py``). Identifiers are stable strings and never reused.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .dates import utc_now_iso

SCHEMA_VERSION = 2  # 2: booking channel on stays, cancellation keeps the amounts before it
CURRENCY = "EUR"

# How a category counts in the results.
#   operating_income   rental and other income of the activity
#   operating_expense  costs of running the rental (cleaning, repairs, fees…)
#   investment         equipment and one-off improvements, never a recurring charge
#   financing          loan repayments (principal, interest, insurance)
#   tax                taxes, shown apart from the operating balance
#   information        kept for reference, excluded from every total
TREATMENTS = ("operating_income", "operating_expense", "investment", "financing", "tax", "information")
INCOME_TREATMENTS = {"operating_income", "information"}
EXPENSE_TREATMENTS = {"operating_expense", "investment", "financing", "tax", "information"}

# Built-in categories (DON 03). Users can rename, archive or add their own;
# the identifier and the treatment of a built-in category stay stable.
DEFAULT_CATEGORIES: tuple[dict[str, Any], ...] = (
    {"id": "accommodation", "kind": "income", "treatment": "operating_income", "fr": "Recettes d'hébergement", "en": "Accommodation revenue", "icon": "home"},
    {"id": "other_income", "kind": "income", "treatment": "operating_income", "fr": "Autres recettes", "en": "Other income", "icon": "plus"},
    {"id": "platform_compensation", "kind": "income", "treatment": "operating_income", "fr": "Indemnisation (dommages, résolution)", "en": "Compensation (damage, resolution)", "icon": "shield"},
    {"id": "platform_credit", "kind": "income", "treatment": "operating_income", "fr": "Prime ou crédit de la plateforme", "en": "Platform bonus or credit", "icon": "coins"},
    {"id": "maintenance", "kind": "expense", "treatment": "operating_expense", "fr": "Entretien et réparation", "en": "Maintenance and repairs", "icon": "wrench"},
    {"id": "cleaning", "kind": "expense", "treatment": "operating_expense", "fr": "Ménage", "en": "Cleaning", "icon": "spray"},
    {"id": "linen", "kind": "expense", "treatment": "operating_expense", "fr": "Linge", "en": "Linen", "icon": "linen"},
    {"id": "travel", "kind": "expense", "treatment": "operating_expense", "fr": "Déplacement", "en": "Travel", "icon": "car"},
    {"id": "energy", "kind": "expense", "treatment": "operating_expense", "fr": "Énergie", "en": "Energy", "icon": "bolt"},
    {"id": "insurance", "kind": "expense", "treatment": "operating_expense", "fr": "Assurance", "en": "Insurance", "icon": "shield"},
    {"id": "subscription", "kind": "expense", "treatment": "operating_expense", "fr": "Abonnement", "en": "Subscription", "icon": "repeat"},
    {"id": "platform_fees", "kind": "expense", "treatment": "operating_expense", "fr": "Frais de plateforme", "en": "Platform fees", "icon": "percent"},
    {"id": "guest_refund", "kind": "expense", "treatment": "operating_expense", "fr": "Remboursement à un voyageur", "en": "Refund to a guest", "icon": "repeat"},
    {"id": "other_expense", "kind": "expense", "treatment": "operating_expense", "fr": "Autre dépense", "en": "Other expense", "icon": "dots"},
    {"id": "equipment", "kind": "expense", "treatment": "investment", "fr": "Équipement", "en": "Equipment", "icon": "sofa"},
    {"id": "loan", "kind": "expense", "treatment": "financing", "fr": "Remboursement d'emprunt", "en": "Loan repayment", "icon": "bank"},
    {"id": "taxes", "kind": "expense", "treatment": "tax", "fr": "Impôts et taxes", "en": "Taxes", "icon": "receipt"},
)

STAY_STATUSES = ("provisional", "confirmed", "cancelled", "completed")
STAY_SOURCES = ("manual", "airbnb", "csv", "demo")
# Where the booking was made (independent of how it was recorded: ``source``).
CHANNELS = ("airbnb", "abritel", "booking", "direct", "other")
PAYMENT_DECLARED = ("unknown", "unpaid")
SERVICE_KINDS = ("cleaning", "linen", "travel", "other", "discount", "tax", "adjustment")
SERVICE_UNITS = ("hour", "flat", "set", "unit", "km", "trip")
SERVICE_KIND_LABELS = {
    "cleaning": ("Ménage", "Cleaning"), "linen": ("Linge", "Linen"), "travel": ("Déplacement", "Travel"), "other": ("Autre", "Other"),
    "discount": ("Remise", "Discount"), "tax": ("Taxe", "Tax"), "adjustment": ("Ajustement", "Adjustment"),
}

LABELS: dict[str, dict[str, tuple[str, str]]] = {
    "stay_status": {
        "provisional": ("Provisoire", "Provisional"),
        "confirmed": ("Confirmé", "Confirmed"),
        "cancelled": ("Annulé", "Cancelled"),
        "completed": ("Terminé", "Completed"),
    },
    "payment_status": {
        "unknown": ("Inconnu", "Unknown"),
        "unpaid": ("Non payé", "Unpaid"),
        "partial": ("Partiellement payé", "Partly paid"),
        "paid": ("Payé", "Paid"),
    },
    "treatment": {
        "operating_income": ("Recette d'exploitation", "Operating income"),
        "operating_expense": ("Dépense d'exploitation", "Operating expense"),
        "investment": ("Investissement", "Investment"),
        "financing": ("Financement", "Financing"),
        "tax": ("Impôts et taxes", "Taxes"),
        "information": ("Information seulement", "Information only"),
    },
    "channel": {
        "airbnb": ("Airbnb", "Airbnb"),
        "abritel": ("Abritel", "Abritel"),
        "booking": ("Booking.com", "Booking.com"),
        "direct": ("En direct", "Direct"),
        "other": ("Autre", "Other"),
    },
    "mode": {
        "activity": ("Par nuit occupée", "Per night occupied"),
        "invoice": ("Par date de séjour ou de facture", "By stay or invoice date"),
        "cash": ("Par date de paiement", "By payment date"),
    },
}


def label(group: str, key: str, lang: str = "fr") -> str:
    fr, en = LABELS.get(group, {}).get(key, (key, key))
    return fr if lang == "fr" else en


def category_label(category: dict[str, Any] | None, lang: str = "fr") -> str:
    if not category:
        return "—"
    custom = (category.get("label") or "").strip()
    if custom:
        return custom
    return category.get("fr" if lang == "fr" else "en") or category.get("id", "—")


def default_categories() -> dict[str, dict[str, Any]]:
    return {item["id"]: {**deepcopy(item), "builtin": True, "archived": False, "label": ""} for item in DEFAULT_CATEGORIES}


def empty_registry() -> dict[str, Any]:
    """A brand new registry: no property, no amount, nothing personal (CAD 02)."""
    now = utc_now_iso()
    return {
        "schema": SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "settings": {
            "currency": CURRENCY,
            "first_choice": None,          # "own_data" or "demo" once chosen
            "onboarding": {"property": False, "first_record": False, "dashboard": False, "backup": False},
            "guest_retention_months": 0,   # 0 = keep guest labels; otherwise anonymise after N months
            "listing_aliases": {},          # listing name in an import file → property id, remembered after an import
        },
        "properties": {},
        "suppliers": {},
        "categories": default_categories(),
        "stays": {},
        "entries": {},
        "payments": {},
        "documents": {},
        "imports": {},
        "csv_profiles": {},
        "permissions": {},
        "audit": [],
        "ops": {},
    }


COLLECTIONS = ("properties", "suppliers", "categories", "stays", "entries", "payments", "documents", "imports", "csv_profiles", "permissions")
