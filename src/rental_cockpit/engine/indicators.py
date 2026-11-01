# Copyright © 2026 Vincent Fournet
"""Indicators and their explanations.

Three readings of the same registry, never mixed (FIN 02):

``activity``  What the rental produced during the period. Stay revenue and
              platform commission are spread night by night over the stay;
              an expense counts on its date, or day by day over its coverage
              period when it has one (an annual insurance, for example).
``invoice``   Documents by their own date: an expense on its invoice date,
              a stay on its arrival date, a correction on its date.
``cash``      Money that actually moved: payments received and paid, on
              their payment date. Nothing is assumed paid (FIN 05, FIN 06).

Every indicator comes with the rule used, what it includes and excludes, and
the exact lines behind it (UX 05). A value that cannot be known is ``None``,
never a misleading zero (FIN 05).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

from .dates import nights as count_nights
from .dates import parse_date
from .money import allocate, format_cents
from .schema import category_label

MODES = ("activity", "invoice", "cash")
BUCKETS = ("revenue", "operating_expense", "investment", "tax", "financing")
TREATMENT_BUCKET = {
    "operating_income": "revenue",
    "operating_expense": "operating_expense",
    "investment": "investment",
    "tax": "tax",
    "financing": "financing",
}
LINE_KIND_CATEGORY = {"cleaning": "cleaning", "linen": "linen", "travel": "travel"}


@dataclass
class Movement:
    """One amount (or the part of it) that belongs to the period."""

    bucket: str
    ref_type: str            # stay | stay_commission | adjustment | entry | payment
    ref_id: str
    property_id: str
    label: str
    date: str                # reference date shown to the user
    total: int               # full amount of the source item
    share: int               # part counted in this period
    category_id: str
    rule: str                # short code of the rule that placed it here
    extra: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- periods

def month_period(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return start, end


def previous_period(start: date, end: date) -> tuple[date, date]:
    """Calendar month → previous month; calendar year → previous year; else same length before."""
    if start.day == 1 and end == month_period(start.year, start.month)[1]:
        prev_month = start - timedelta(days=1)
        return month_period(prev_month.year, prev_month.month)
    if start.month == 1 and start.day == 1 and end == date(start.year + 1, 1, 1):
        return date(start.year - 1, 1, 1), start
    length = end - start
    return start - length, start


# --------------------------------------------------------------------------- spreading

def _slice_share(total: int, first: date, last: date, period_start: date, period_end: date) -> int:
    """Part of ``total`` spread evenly over the days of ``[first, last)`` that fall in the period.

    The split is done once for the whole span (largest remainder), so the
    shares of consecutive periods always add up to the total, to the cent.
    """
    days = count_nights(first, last)
    if days <= 0:
        return 0
    lo = max(0, (period_start - first).days)
    hi = min(days, (period_end - first).days)
    if hi <= lo:
        return 0
    if lo == 0 and hi == days:
        return total
    return sum(allocate(total, [1] * days)[lo:hi])


def _in(day: str, start: date, end: date) -> bool:
    return bool(day) and start <= parse_date(day) < end


# --------------------------------------------------------------------------- collection

class _Collector:
    def __init__(self, data: dict[str, Any], property_ids: set[str], start: date, end: date, mode: str, lang: str) -> None:
        self.data, self.pids, self.start, self.end, self.mode, self.lang = data, property_ids, start, end, mode, lang
        self.movements: list[Movement] = []
        self.missing: list[dict[str, Any]] = []
        self.categories = data.get("categories", {})

    def label_of_stay(self, stay: dict[str, Any]) -> str:
        prop = self.data["properties"].get(stay["property_id"], {})
        guest = stay.get("guest_label") or stay.get("external_ref") or ("Séjour" if self.lang == "fr" else "Stay")
        return f"{guest} · {prop.get('name', '—')}"

    def bucket_of(self, category_id: str) -> str | None:
        category = self.categories.get(category_id) or {}
        return TREATMENT_BUCKET.get(category.get("treatment", ""))

    def stays(self) -> Iterable[dict[str, Any]]:
        return (s for s in self.data.get("stays", {}).values() if s["property_id"] in self.pids)

    def entries(self) -> Iterable[dict[str, Any]]:
        return (e for e in self.data.get("entries", {}).values()
                if e["property_id"] in self.pids and not e.get("archived") and not e.get("superseded_by"))

    def add(self, **kwargs: Any) -> None:
        if kwargs["share"]:
            self.movements.append(Movement(**kwargs))

    # Activity and invoice readings ------------------------------------------

    def collect_accrual(self) -> None:
        by_night = self.mode == "activity"
        for stay in self.stays():
            start, end = parse_date(stay["start"]), parse_date(stay["end"])
            amounts = stay.get("amounts") or {}
            cancelled = stay["status"] == "cancelled"
            label = self.label_of_stay(stay)
            touches = (start < self.end and self.start < end) if by_night else (self.start <= start < self.end)
            if cancelled:
                # A cancellation can leave a retained amount; it counts once, on the arrival date.
                touches = self.start <= start < self.end
            for key, bucket, ref_type, category in (("gross", "revenue", "stay", "accommodation"),
                                                    ("commission", "operating_expense", "stay_commission", "platform_fees")):
                total = amounts.get(key)
                if total is None:
                    if key == "gross" and touches and not cancelled:
                        self.missing.append({"type": "stay", "id": stay["id"], "label": label, "reason": "gross_unknown"})
                    continue
                if not touches:
                    continue
                if by_night and not cancelled:
                    share, rule = _slice_share(total, start, end, self.start, self.end), "per_night"
                else:
                    share, rule = total, ("arrival_cancelled" if cancelled else "arrival_date")
                self.add(bucket=bucket, ref_type=ref_type, ref_id=stay["id"], property_id=stay["property_id"], label=label,
                         date=stay["start"], total=total, share=share, category_id=category, rule=rule,
                         extra={"end": stay["end"], "nights": count_nights(start, end), "status": stay["status"]})
            for adj in stay.get("adjustments", []):
                if _in(adj["date"], self.start, self.end):
                    self.add(bucket="revenue", ref_type="adjustment", ref_id=adj["id"], property_id=stay["property_id"],
                             label=f"{label} · {adj.get('note', '')}", date=adj["date"], total=adj["amount"], share=adj["amount"],
                             category_id="accommodation", rule="own_date", extra={"stay_id": stay["id"]})
        for entry in self.entries():
            bucket = self.bucket_of(entry["category_id"])
            if bucket is None:
                continue
            if entry["kind"] == "income":
                bucket = "revenue"
            if by_night and entry.get("period_start"):
                share = _slice_share(entry["amount"], parse_date(entry["period_start"]), parse_date(entry["period_end"]), self.start, self.end)
                rule = "per_day_coverage"
            elif _in(entry["date"], self.start, self.end):
                share, rule = entry["amount"], "own_date"
            else:
                continue
            self.add(bucket=bucket, ref_type="entry", ref_id=entry["id"], property_id=entry["property_id"], label=entry["label"],
                     date=entry["date"], total=entry["amount"], share=share, category_id=entry["category_id"], rule=rule,
                     extra={"lines": entry.get("lines") or [], "loan_split": entry.get("loan_split")})

    # Cash reading -------------------------------------------------------------

    def collect_cash(self) -> None:
        entries = self.data.get("entries", {})
        for payment in self.data.get("payments", {}).values():
            if payment["property_id"] not in self.pids or not _in(payment["date"], self.start, self.end):
                continue
            for link in payment["links"]:
                if link["type"] == "stay":
                    stay = self.data["stays"].get(link["id"])
                    if not stay:
                        continue
                    self.add(bucket="revenue", ref_type="payment", ref_id=payment["id"], property_id=payment["property_id"],
                             label=self.label_of_stay(stay), date=payment["date"], total=payment["amount"], share=link["amount"],
                             category_id="accommodation", rule="payment_date", extra={"stay_id": stay["id"], "direction": "in"})
                    continue
                entry = entries.get(link["id"])
                if not entry or entry.get("archived"):
                    continue
                bucket = "revenue" if entry["kind"] == "income" else self.bucket_of(entry["category_id"])
                if bucket is None:
                    continue
                self.add(bucket=bucket, ref_type="payment", ref_id=payment["id"], property_id=payment["property_id"],
                         label=entry["label"], date=payment["date"], total=entry["amount"], share=link["amount"],
                         category_id=entry["category_id"], rule="payment_date",
                         extra={"entry_id": entry["id"], "direction": payment["direction"], "loan_split": entry.get("loan_split"), "lines": entry.get("lines") or []})


# --------------------------------------------------------------------------- explanations

TEXT = {
    "revenue": {
        "label": ("Recettes", "Revenue"),
        "cash_label": ("Sommes reçues", "Money received"),
        "formula": ("Recettes des séjours + ajustements + autres recettes", "Stay revenue + adjustments + other income"),
        "cash_formula": ("Somme des versements reçus pendant la période", "Sum of payments received during the period"),
        "excludes": ("Taxes collectées pour un tiers, dépôts de garantie, versements nets déjà comptés (pas de double comptage).",
                     "Taxes collected for a third party, security deposits, net payouts already counted (no double counting)."),
    },
    "operating_expenses": {
        "label": ("Dépenses", "Expenses"),
        "formula": ("Commissions des plateformes + dépenses d'exploitation", "Platform commissions + operating expenses"),
        "cash_formula": ("Paiements effectués pour des dépenses d'exploitation", "Payments made for operating expenses"),
        "excludes": ("Remboursements d'emprunt, impôts et taxes, équipements (investissement), écritures « information seulement ».",
                     "Loan repayments, taxes, equipment (investment), \"information only\" entries."),
        "cash_excludes": ("Commissions prélevées à la source par la plateforme : elles sont déjà déduites des sommes reçues. Dépenses non payées (voir « À payer »).",
                          "Commissions withheld by the platform: already deducted from money received. Unpaid expenses (see \"To pay\")."),
    },
    "operating_balance": {
        "label": ("Solde avant financement", "Balance before financing"),
        "formula": ("Recettes − Dépenses", "Revenue − Expenses"),
        "excludes": ("Financement, impôts et dépenses d'investissement. Ce n'est pas un bénéfice fiscal.",
                     "Financing, taxes and investment spending. This is not a taxable profit."),
    },
    "investment": {"label": ("Investissements", "Investments"), "formula": ("Équipements et dépenses ponctuelles d'investissement", "Equipment and one-off investment spending"),
                   "excludes": ("Jamais transformés automatiquement en charge récurrente.", "Never turned automatically into a recurring charge.")},
    "taxes": {"label": ("Impôts et taxes", "Taxes"), "formula": ("Écritures de la catégorie Impôts et taxes", "Entries in the Taxes category"),
              "excludes": ("Taxes de séjour collectées pour un tiers.", "Tourist taxes collected for a third party.")},
    "financing": {"label": ("Financement", "Financing"), "formula": ("Remboursements d'emprunt (capital + intérêts + assurance)", "Loan repayments (principal + interest + insurance)"),
                  "excludes": ("Une mensualité et ses composants ne sont jamais comptés deux fois.", "An instalment and its components are never counted twice.")},
    "balance_after_financing": {
        "label": ("Solde après financement", "Balance after financing"),
        "cash_label": ("Trésorerie après financement", "Cash after financing"),
        "formula": ("Solde avant financement − Financement", "Balance before financing − Financing"),
        "cash_formula": ("Sommes reçues − tous les paiements effectués (dépenses, investissements, impôts, financement)",
                         "Money received − every payment made (expenses, investments, taxes, financing)"),
        "excludes": ("Ce résultat ne constitue pas un bénéfice fiscal.", "This result is not a taxable profit."),
    },
    "nights": {"label": ("Nuitées", "Nights"), "formula": ("Nuits des séjours non annulés comprises dans la période", "Nights of non-cancelled stays inside the period"),
               "excludes": ("Le jour du départ n'est pas une nuit. Séjours annulés.", "The departure day is not a night. Cancelled stays.")},
    "occupancy": {"label": ("Taux d'occupation", "Occupancy"), "formula": ("Nuitées ÷ nuits disponibles", "Nights ÷ available nights"),
                  "excludes": ("Les périodes d'indisponibilité et les jours avant le début d'activité ne sont pas disponibles.",
                               "Unavailable periods and days before the activity start are not available.")},
    "average_night": {"label": ("Revenu moyen par nuit", "Average revenue per night"), "formula": ("Recettes des séjours ÷ nuitées", "Stay revenue ÷ nights"),
                      "excludes": ("Ajustements et autres recettes.", "Adjustments and other income.")},
    "to_pay": {"label": ("À payer", "To pay"), "formula": ("Montant des dépenses − paiements déjà enregistrés", "Expense amounts − payments already recorded"),
               "excludes": ("Une échéance, la mention « paiement comptant » ou la présence d'un PDF ne valent pas paiement.",
                            "A due date, a \"paid in cash\" mention or an attached PDF are not a payment.")},
    "to_receive": {"label": ("À recevoir", "To receive"), "formula": ("Versement attendu des séjours et recettes hors séjours − sommes déjà reçues", "Expected payout of stays and income outside stays − money already received"),
                   "excludes": ("Séjours dont le montant est inconnu : listés dans « Données à vérifier ».", "Stays whose amount is unknown: listed in \"Data to check\".")},
}

RULES = {
    "per_night": ("Réparti nuit par nuit sur le séjour", "Spread night by night over the stay"),
    "per_day_coverage": ("Réparti jour par jour sur la période couverte", "Spread day by day over the covered period"),
    "own_date": ("Compté à sa date", "Counted on its date"),
    "arrival_date": ("Compté à la date d'arrivée", "Counted on the arrival date"),
    "arrival_cancelled": ("Séjour annulé : montant conservé compté à la date d'arrivée", "Cancelled stay: retained amount counted on the arrival date"),
    "payment_date": ("Compté à la date du paiement", "Counted on the payment date"),
}

MODE_RULES = {
    "activity": ("Lecture « Activité » : ce que la location a produit pendant la période. Les recettes et commissions d'un séjour sont réparties par nuit ; une dépense compte à sa date ou sur sa période couverte.",
                 "\"Activity\" reading: what the rental produced during the period. Stay revenue and commissions are spread per night; an expense counts on its date or over its covered period."),
    "invoice": ("Lecture « Factures » : chaque document à sa propre date (facture à sa date, séjour à sa date d'arrivée).",
                "\"Invoices\" reading: each document on its own date (invoice on its date, stay on its arrival date)."),
    "cash": ("Lecture « Trésorerie » : uniquement l'argent réellement reçu ou payé, à la date du paiement.",
             "\"Cash\" reading: only money actually received or paid, on the payment date."),
}


def _t(pair: tuple[str, str], lang: str) -> str:
    return pair[0] if lang == "fr" else pair[1]


def explain(indicator_id: str, mode: str, lang: str) -> dict[str, str]:
    text = TEXT.get(indicator_id, {})
    cash = mode == "cash"
    label = text.get("cash_label") if cash and "cash_label" in text else text.get("label", (indicator_id, indicator_id))
    formula = text.get("cash_formula") if cash and "cash_formula" in text else text.get("formula", ("", ""))
    excludes = text.get("cash_excludes") if cash and "cash_excludes" in text else text.get("excludes", ("", ""))
    return {"label": _t(label, lang), "formula": _t(formula, lang), "excludes": _t(excludes, lang), "reading": _t(MODE_RULES[mode], lang)}


# --------------------------------------------------------------------------- computation

def compute(data: dict[str, Any], *, property_ids: Iterable[str], start: date, end: date, mode: str = "activity",
            lang: str = "fr", today: date | None = None, compare: bool = True, with_lines: bool = False) -> dict[str, Any]:
    """Compute every indicator for the selected properties and period."""
    if mode not in MODES:
        raise ValueError("mode")
    if end <= start:
        raise ValueError("period")
    pids = {pid for pid in property_ids if pid in data.get("properties", {})}
    today = today or date.today()
    collector = _Collector(data, pids, start, end, mode, lang)
    if mode == "cash":
        collector.collect_cash()
    else:
        collector.collect_accrual()
    movements = collector.movements

    sums: dict[str, int] = defaultdict(int)
    per_property: dict[str, dict[str, int]] = {pid: defaultdict(int) for pid in pids}
    for m in movements:
        sums[m.bucket] += m.share
        per_property[m.property_id][m.bucket] += m.share

    complete_revenue = not collector.missing
    nights_total, available_total, stay_revenue = _nights(data, pids, start, end)
    financing_split = _financing_split(movements)

    def ind(indicator_id: str, value: Any, unit: str = "money", complete: bool = True, lines: list[Movement] | None = None, **extra: Any) -> dict[str, Any]:
        item = {"id": indicator_id, "value": value, "unit": unit, "complete": complete, **explain(indicator_id, mode, lang), **extra}
        if lines is not None:
            item["count"] = len(lines)
        if with_lines and lines is not None:
            item["lines"] = [_line(m, data, lang) for m in sorted(lines, key=lambda m: (m.date, m.label))]
        return item

    by_bucket = lambda *names: [m for m in movements if m.bucket in names]  # noqa: E731
    revenue = sums["revenue"]
    op_exp = sums["operating_expense"]
    operating_balance = revenue - op_exp
    if mode == "cash":
        after = revenue - op_exp - sums["investment"] - sums["tax"] - sums["financing"]
    else:
        after = operating_balance - sums["financing"]

    indicators = {
        "revenue": ind("revenue", revenue, complete=complete_revenue, lines=by_bucket("revenue"), missing=collector.missing),
        "operating_expenses": ind("operating_expenses", op_exp, lines=by_bucket("operating_expense")),
        "operating_balance": ind("operating_balance", operating_balance, complete=complete_revenue, lines=by_bucket("revenue", "operating_expense")),
        "investment": ind("investment", sums["investment"], lines=by_bucket("investment")),
        "taxes": ind("taxes", sums["tax"], lines=by_bucket("tax")),
        "financing": ind("financing", sums["financing"], lines=by_bucket("financing"), split=financing_split),
        "balance_after_financing": ind("balance_after_financing", after, complete=complete_revenue,
                                       lines=by_bucket(*(BUCKETS if mode == "cash" else ("revenue", "operating_expense", "financing")))),
        "nights": ind("nights", nights_total, unit="nights"),
        "occupancy": ind("occupancy", round(nights_total / available_total, 4) if available_total else None, unit="ratio",
                         complete=bool(available_total), available_nights=available_total),
    }
    if mode == "activity":
        indicators["average_night"] = ind("average_night", (stay_revenue // nights_total) if nights_total else None,
                                          complete=bool(nights_total) and complete_revenue)

    pending = _pending(data, pids, end, lang)
    indicators["to_pay"] = ind("to_pay", pending["to_pay"], count=pending["to_pay_count"])
    indicators["to_receive"] = ind("to_receive", pending["to_receive"], count=pending["to_receive_count"],
                                   stays=pending["to_receive_stays"], entries=pending["to_receive_entries"])

    result: dict[str, Any] = {
        "mode": mode,
        "reading": _t(MODE_RULES[mode], lang),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "property_ids": sorted(pids),
        "indicators": indicators,
        "by_property": {
            pid: {
                "revenue": values["revenue"],
                "expenses": values["operating_expense"],
                "balance": values["revenue"] - values["operating_expense"],
            }
            for pid, values in per_property.items()
        },
        "by_category": _by_category(movements, data, lang),
        "to_check": _to_check(data, pids, end, today, collector.missing, lang),
        "upcoming_stays": _upcoming(data, pids, today, lang),
    }
    if compare:
        prev_start, prev_end = previous_period(start, end)
        previous = compute(data, property_ids=pids, start=prev_start, end=prev_end, mode=mode, lang=lang, today=today, compare=False)
        result["previous"] = {
            "period": previous["period"],
            "values": {key: previous["indicators"][key]["value"] for key in ("revenue", "operating_expenses", "operating_balance", "balance_after_financing", "nights")},
        }
    return result


def indicator_detail(data: dict[str, Any], indicator_id: str, **kwargs: Any) -> dict[str, Any]:
    """One indicator with every line behind it (« Comment est calculé ce montant ? »)."""
    result = compute(data, compare=False, with_lines=True, **kwargs)
    item = result["indicators"].get(indicator_id)
    if item is None:
        raise KeyError(indicator_id)
    return {"indicator": item, "period": result["period"], "mode": result["mode"], "reading": result["reading"]}


# --------------------------------------------------------------------------- pieces

def _line(m: Movement, data: dict[str, Any], lang: str) -> dict[str, Any]:
    prop = data["properties"].get(m.property_id, {})
    category = data["categories"].get(m.category_id)
    return {
        "ref_type": m.ref_type, "ref_id": m.ref_id, "property": prop.get("name", "—"), "label": m.label,
        "date": m.date, "total": m.total, "share": m.share, "bucket": m.bucket,
        "category": category_label(category, lang), "rule": _t(RULES.get(m.rule, (m.rule, m.rule)), lang),
        "sign": -1 if m.bucket != "revenue" else 1,
        # What the line comes from, so « Comment est calculé ce montant ? » can open it.
        "stay_id": m.extra.get("stay_id") or (m.ref_id if m.ref_type in ("stay", "stay_commission") else ""),
        "entry_id": m.extra.get("entry_id") or (m.ref_id if m.ref_type == "entry" else ""),
    }


def _nights(data: dict[str, Any], pids: set[str], start: date, end: date) -> tuple[int, int, int]:
    booked = 0
    stay_revenue = 0
    for stay in data.get("stays", {}).values():
        if stay["property_id"] not in pids or stay["status"] == "cancelled":
            continue
        s, e = parse_date(stay["start"]), parse_date(stay["end"])
        inside = max(0, (min(e, end) - max(s, start)).days)
        booked += inside
        gross = (stay.get("amounts") or {}).get("gross")
        if inside and gross is not None:
            stay_revenue += _slice_share(gross, s, e, start, end)
    available = 0
    for pid in pids:
        prop = data["properties"][pid]
        first = max(start, parse_date(prop["activity_start"])) if prop.get("activity_start") else start
        if first >= end:
            continue
        blocked: set[date] = set()
        for block in prop.get("unavailable", []):
            b_start, b_end = max(parse_date(block["start"]), first), min(parse_date(block["end"]), end)
            day = b_start
            while day < b_end:
                blocked.add(day)
                day += timedelta(days=1)
        available += (end - first).days - len(blocked)
    return booked, available, stay_revenue


def _financing_split(movements: list[Movement]) -> dict[str, int | None]:
    """Principal / interest / insurance when known; ``unknown`` otherwise. Never added twice."""
    split = {"principal": 0, "interest": 0, "insurance": 0, "unknown": 0}
    for m in movements:
        if m.bucket != "financing":
            continue
        loan = m.extra.get("loan_split") or {}
        parts = [loan.get(k) for k in ("principal", "interest", "insurance")]
        if all(p is not None for p in parts) and sum(parts) == m.total:
            shares = allocate(m.share, parts) if sum(parts) else [0, 0, 0]
            for key, value in zip(("principal", "interest", "insurance"), shares, strict=True):
                split[key] += value
        else:
            split["unknown"] += m.share
    return split


def _by_category(movements: list[Movement], data: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    for m in movements:
        if m.bucket == "revenue":
            continue
        lines = m.extra.get("lines") or []
        if lines and m.share == m.total and all(line["amount"] >= 0 for line in lines):
            for line in lines:
                totals[LINE_KIND_CATEGORY.get(line["kind"], m.category_id)] += line["amount"]
        else:
            totals[m.category_id] += m.share
    rows = []
    for category_id, amount in totals.items():
        category = data["categories"].get(category_id, {})
        rows.append({"category_id": category_id, "label": category_label(category, lang), "treatment": category.get("treatment", ""), "amount": amount})
    return sorted(rows, key=lambda r: -r["amount"])


def _pending(data: dict[str, Any], pids: set[str], end: date, lang: str) -> dict[str, int]:
    paid_by_entry: dict[str, int] = defaultdict(int)
    received_by_stay: dict[str, int] = defaultdict(int)
    for payment in data.get("payments", {}).values():
        for link in payment["links"]:
            if link["type"] == "entry":
                paid_by_entry[link["id"]] += link["amount"]
            else:
                received_by_stay[link["id"]] += link["amount"]
    to_pay = to_pay_count = 0
    for entry in data.get("entries", {}).values():
        if entry["property_id"] not in pids or entry["kind"] != "expense" or entry.get("archived") or entry.get("superseded_by"):
            continue
        if parse_date(entry["date"]) >= end:
            continue
        remaining = entry["amount"] - paid_by_entry[entry["id"]]
        if remaining > 0:
            to_pay += remaining
            to_pay_count += 1
    to_receive = to_receive_count = from_entries = 0
    for entry in data.get("entries", {}).values():
        # Income outside stays (a refund, an occasional rental…) is to receive until paid in full.
        if entry["property_id"] not in pids or entry["kind"] != "income" or entry.get("archived") or entry.get("superseded_by"):
            continue
        if parse_date(entry["date"]) >= end:
            continue
        remaining = entry["amount"] - paid_by_entry[entry["id"]]
        if remaining > 0:
            to_receive += remaining
            from_entries += remaining
            to_receive_count += 1
    for stay in data.get("stays", {}).values():
        if stay["property_id"] not in pids or stay["status"] in ("cancelled", "provisional"):
            continue
        if parse_date(stay["start"]) >= end:
            continue
        expected = expected_payout(stay)
        if expected is None:
            continue
        remaining = expected - received_by_stay[stay["id"]]
        if remaining > 0:
            to_receive += remaining
            to_receive_count += 1
    return {"to_pay": to_pay, "to_pay_count": to_pay_count, "to_receive": to_receive, "to_receive_count": to_receive_count,
            "to_receive_entries": from_entries, "to_receive_stays": to_receive - from_entries}


def expected_payout(stay: dict[str, Any]) -> int | None:
    """Net amount the owner should receive for a stay, when it can be known."""
    amounts = stay.get("amounts") or {}
    adjustments = sum(a["amount"] for a in stay.get("adjustments", []))
    if amounts.get("payout") is not None:
        return amounts["payout"] + adjustments
    if amounts.get("gross") is not None and amounts.get("commission") is not None:
        return amounts["gross"] - amounts["commission"] + adjustments
    return None


def _to_check(data: dict[str, Any], pids: set[str], end: date, today: date, missing: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """« Données à vérifier » : what keeps a result from being final."""
    fr = lang == "fr"
    items: list[dict[str, Any]] = []
    unknown_payment = [e for e in data.get("entries", {}).values()
                       if e["property_id"] in pids and e["kind"] == "expense" and not e.get("archived") and not e.get("superseded_by")
                       and e.get("payment_declared", "unknown") == "unknown"
                       and not any(link["type"] == "entry" and link["id"] == e["id"] for p in data["payments"].values() for link in p["links"])]
    received = {link["id"] for p in data.get("payments", {}).values() for link in p["links"] if link["type"] == "stay"}
    payouts = [s for s in data.get("stays", {}).values()
               if s["property_id"] in pids and s["status"] in ("confirmed", "completed") and parse_date(s["end"]) <= today
               and s["id"] not in received and expected_payout(s)]
    incomplete_docs = [d for d in data.get("documents", {}).values()
                       if d.get("property_id") in pids and (not d.get("entry_ids") or d.get("amount") is None or not d.get("supplier"))]
    unallocated = []
    for e in data.get("entries", {}).values():
        if e["property_id"] not in pids or e.get("archived") or e.get("superseded_by") or not e.get("allocations"):
            continue
        rest = sum(r["remaining"] for r in _remaining(e))
        if rest > 0:
            unallocated.append((e, rest))

    def add(kind: str, count: int, title: tuple[str, str], hint: tuple[str, str], ids: list[str], severity: str = "warning", amount: int | None = None) -> None:
        if count:
            items.append({"kind": kind, "count": count, "title": title[0] if fr else title[1], "hint": hint[0] if fr else hint[1],
                          "ids": ids[:50], "severity": severity, "amount": amount})

    add("documents_incomplete", len(incomplete_docs),
        (f"{len(incomplete_docs)} facture{'s' if len(incomplete_docs) > 1 else ''} à compléter", f"{len(incomplete_docs)} invoice{'s' if len(incomplete_docs) > 1 else ''} to complete"),
        ("Ajoutez les informations manquantes ou rattachez le justificatif à une dépense.", "Add the missing details or attach the document to an expense."),
        [d["id"] for d in incomplete_docs])
    add("payouts_to_confirm", len(payouts),
        (f"{len(payouts)} versement{'s' if len(payouts) > 1 else ''} à confirmer", f"{len(payouts)} payout{'s' if len(payouts) > 1 else ''} to confirm"),
        ("Séjours terminés sans somme reçue : vérifiez que l'argent est bien arrivé.", "Completed stays with no money received: check that it arrived."),
        [s["id"] for s in payouts], amount=sum(expected_payout(s) or 0 for s in payouts))
    add("payments_unknown", len(unknown_payment),
        (f"{len(unknown_payment)} paiement{'s' if len(unknown_payment) > 1 else ''} à confirmer", f"{len(unknown_payment)} payment{'s' if len(unknown_payment) > 1 else ''} to confirm"),
        ("Dépenses dont on ne sait pas si elles sont payées : indiquez « Payé » ou « Non payé ».", "Expenses with an unknown payment status: mark them \"Paid\" or \"Unpaid\"."),
        [e["id"] for e in unknown_payment], amount=sum(e["amount"] for e in unknown_payment))
    add("stays_without_amount", len(missing),
        (f"{len(missing)} séjour{'s' if len(missing) > 1 else ''} sans montant", f"{len(missing)} stay{'s' if len(missing) > 1 else ''} without an amount"),
        ("Le montant est inconnu : les recettes de la période sont incomplètes.", "The amount is unknown: the period's revenue is incomplete."),
        [m["id"] for m in missing], severity="incomplete")
    add("allocations_incomplete", len(unallocated),
        (f"{format_cents(sum(r for _, r in unallocated), 'fr')} restent à affecter", f"{format_cents(sum(r for _, r in unallocated), 'en')} left to allocate"),
        ("Des prestations ne sont pas encore réparties entre les séjours.", "Some services are not yet split between stays."),
        [e["id"] for e, _ in unallocated], severity="info", amount=sum(r for _, r in unallocated))
    return items


def _remaining(entry: dict[str, Any]) -> list[dict[str, Any]]:
    from .ledger import allocation_remaining  # local import keeps modules independent
    return allocation_remaining(entry)


def _upcoming(data: dict[str, Any], pids: set[str], today: date, lang: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = []
    for stay in data.get("stays", {}).values():
        if stay["property_id"] not in pids or stay["status"] == "cancelled":
            continue
        start, end = parse_date(stay["start"]), parse_date(stay["end"])
        if end <= today:
            continue
        prop = data["properties"].get(stay["property_id"], {})
        rows.append({
            "id": stay["id"], "property_id": stay["property_id"], "property": prop.get("name", "—"), "property_kind": prop.get("kind", ""),
            "start": stay["start"], "end": stay["end"], "nights": count_nights(start, end), "guests": stay.get("guests"),
            "guest_label": stay.get("guest_label", ""), "status": stay["status"],
            "timing": "in_progress" if start <= today < end else "upcoming",
        })
    rows.sort(key=lambda r: r["start"])
    return rows[:limit]


def movement_dict(m: Movement) -> dict[str, Any]:  # pragma: no cover - debugging helper
    return asdict(m)
