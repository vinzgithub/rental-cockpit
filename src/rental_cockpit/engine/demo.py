# Copyright © 2026 Vincent Fournet
"""Fictional demonstration data (UX 02).

The demo lives in its own registry, never in the real one. Every name,
reference and amount below is invented: two generic properties, suppliers
called "… Démo", stays labelled "Séjour A-07". Nothing comes from a real
rental.

The *example month* reproduces the worked example of the documentation, so
anyone can check the arithmetic on screen:

* revenue 1 000 € (Appartement A 600 €, Studio B 400 €);
* expenses 200 € = commission 30 + cleaning 80 + linen 20 + travel 10 + repair 60;
* balance before financing 800 €; with a 200 € loan instalment paid that
  month, cash after financing is 600 €.

The example month is the current month once it is well advanced (day 21 or
later), otherwise the previous month, so that its stays are in the past.

Every other month is ordinary fictional activity drawn from a fixed random
seed. The month-to-month changes shown on screen are computed from those
months like any real data; nothing is tuned to produce a given percentage.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from . import documents
from .indicators import month_period
from .ledger import Ledger
from .schema import empty_registry

DEMO_ACTOR = "demo"


def example_month(today: date) -> tuple[date, date]:
    if today.day >= 21:
        return month_period(today.year, today.month)
    previous = today.replace(day=1) - timedelta(days=1)
    return month_period(previous.year, previous.month)


def _shift_month(start: date, months: int) -> date:
    index = start.year * 12 + start.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def build_demo(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    data = empty_registry()
    data["settings"]["first_choice"] = "demo"
    data["settings"]["demo"] = True
    led = Ledger(data, DEMO_ACTOR)
    focus_start, focus_end = example_month(today)
    data["settings"]["demo_focus"] = {"start": focus_start.isoformat(), "end": focus_end.isoformat()}
    history_start = _shift_month(focus_start, -13)

    a = led.create_property({"name": "Appartement A", "kind": "apartment", "capacity": 4, "bedrooms": 2,
                             "activity_start": history_start.isoformat(), "note": "Bien fictif de démonstration."})["property"]["id"]
    b = led.create_property({"name": "Studio B", "kind": "studio", "capacity": 2, "bedrooms": 1,
                             "activity_start": history_start.isoformat(), "note": "Bien fictif de démonstration."})["property"]["id"]
    cleaner = led.create_supplier({"name": "Prestataire Démo", "role": "Ménage, linge et petite logistique", "categories": ["cleaning", "linen", "travel"],
                                   "rates": [{"kind": "cleaning", "unit": "hour", "unit_price": "25", "label": "Ménage à l'heure (indicatif)"},
                                             {"kind": "linen", "unit": "set", "unit_price": "10", "label": "Lot de linge (indicatif)"}]})["supplier"]["id"]
    workshop = led.create_supplier({"name": "Atelier Démo", "role": "Entretien et réparations", "categories": ["maintenance"]})["supplier"]["id"]
    led.create_supplier({"name": "Blanchisserie Démo", "role": "Linge de maison", "categories": ["linen"]})
    bank = led.create_supplier({"name": "Banque Démo", "role": "Prêt immobilier fictif", "categories": ["loan"]})["supplier"]["id"]

    counter = {"n": 0}

    def stay(prop: str, letter: str, start: date, nights: int, gross: str, guests: int, *, paid: bool = True, status: str = "completed") -> str:
        counter["n"] += 1
        end = start + timedelta(days=nights)
        if end > today and status == "completed":
            status = "confirmed"
        gross_cents = int(round(float(gross) * 100))
        commission = gross_cents * 3 // 100
        created = led.create_stay({
            "property_id": prop, "start": start.isoformat(), "end": end.isoformat(), "status": status, "guests": guests,
            "guest_label": f"Séjour {letter}-{counter['n']:02d}", "external_ref": f"DEMO-{1000 + counter['n']}",
            "channel": "abritel" if counter["n"] % 3 == 0 else "airbnb",
            "amounts": {"gross_cents": gross_cents, "commission_cents": commission, "payout_cents": gross_cents - commission},
        }, source="demo")["stay"]
        pay_day = start + timedelta(days=1)
        if paid and pay_day <= today:
            led.create_payment({"property_id": prop, "direction": "in", "date": pay_day.isoformat(), "amount_cents": gross_cents - commission,
                                "links": [{"type": "stay", "id": created["id"], "amount_cents": gross_cents - commission}],
                                "method": "Virement plateforme (fictif)"})
        return created["id"]

    def expense(prop: str, category: str, label: str, day: date, amount: str, *, supplier: str = "", paid: bool = True,
                stay_id: str = "", **extra: Any) -> str:
        cents = int(round(float(amount) * 100))
        payload = {"property_id": prop, "kind": "expense", "category_id": category, "label": label, "date": day.isoformat(),
                   "amount_cents": cents, "supplier_id": supplier, "stay_id": stay_id, **extra}
        if paid and day <= today:
            payload.update(paid=True, paid_date=day.isoformat(), payment_method="Virement (fictif)")
        elif not paid:
            payload["payment_declared"] = "unknown"
        return led.create_entry(payload)["entry"]["id"]

    rng = random.Random(4207)

    # --- History: the thirteen months before the example month, ordinary fictional activity.
    # The cleaning of the most recent month is not marked as paid yet (the supplier bills
    # monthly), which is why the demo shows payments to confirm.
    month = history_start
    previous_start = _shift_month(focus_start, -1)
    inv_month = _shift_month(focus_start, -2)  # holds the service invoice example below
    while month < focus_start:
        _, month_end = month_period(month.year, month.month)
        settled = month < previous_start
        for prop, letter, rate, cap in ((a, "A", 118, 4), (b, "B", 92, 2)):
            day = month + timedelta(days=rng.randint(1, 4))
            for _ in range(rng.randint(2, 3)):
                length = rng.randint(2, 5)
                if day + timedelta(days=length) >= month_end:
                    break
                gross, guests = f"{rate * length + rng.choice((0, 15, 25))}", rng.randint(1, cap)
                depart = day + timedelta(days=length)
                # In the month of the service invoice example, Appartement A only has the two
                # example stays: the drawn ones are skipped (the draws still happen, so every
                # other month stays exactly the same).
                if not (prop == a and month == inv_month):
                    sid = stay(prop, letter, day, length, gross, guests)
                    expense(prop, "cleaning", "Ménage de départ", depart, "45" if letter == "A" else "35", supplier=cleaner,
                            stay_id=sid, paid=settled)
                day = depart + timedelta(days=rng.randint(2, 6))
            # One stay across the end of a month, four months before the example month, so the
            # demo shows a stay spread over two months (its own stay page explains the split).
            if prop == a and month == _shift_month(focus_start, -4) and day <= month_end - timedelta(days=2):
                sid = stay(prop, letter, month_end - timedelta(days=2), 3, "354", 2)
                expense(prop, "cleaning", "Ménage de départ", month_end + timedelta(days=1), "45", supplier=cleaner,
                        stay_id=sid, paid=settled)
        if rng.random() < 0.35:
            prop = rng.choice((a, b))
            expense(prop, "maintenance", "Petite réparation (fictif)", month + timedelta(days=rng.randint(5, 25)),
                    f"{rng.randint(35, 140)}", supplier=workshop)
        expense(a, "energy", "Électricité (fictif)", month + timedelta(days=14), "48")
        expense(b, "energy", "Électricité (fictif)", month + timedelta(days=14), "31")
        expense(a, "subscription", "Box internet (fictif)", month + timedelta(days=7), "30")
        month = _shift_month(month, 1)

    # Annual insurance spread day by day over its coverage (ends before the example months).
    ins_start = history_start
    ins_end = _shift_month(history_start, 12)
    expense(a, "insurance", "Assurance propriétaire non occupant (fictif)", ins_start, "264",
            period_start=ins_start.isoformat(), period_end=ins_end.isoformat())
    expense(a, "equipment", "Lave-linge (fictif)", _shift_month(focus_start, -6) + timedelta(days=9), "489", supplier=workshop)
    expense(b, "taxes", "Taxe foncière (fictif)", _shift_month(focus_start, -3) + timedelta(days=14), "612")

    # The documentation example of a service invoice: 150 € = 100 cleaning + 40 linen + 10 travel,
    # 90 € for stay A and 60 € for stay B. One expense of 150 €, never 300 €.
    s1 = stay(a, "A", inv_month + timedelta(days=4), 7, "826", 4)
    s2 = stay(a, "A", inv_month + timedelta(days=11), 7, "840", 3)
    invoice = led.create_entry({
        "property_id": a, "kind": "expense", "category_id": "cleaning", "label": "Facture Prestataire Démo F-DEMO-018",
        "invoice_number": "F-DEMO-018", "date": (inv_month + timedelta(days=20)).isoformat(), "amount": "150", "supplier_id": cleaner,
        "lines": [{"id": "l1", "kind": "cleaning", "label": "Ménage", "amount": "100"},
                  {"id": "l2", "kind": "linen", "label": "Linge", "quantity": "4", "unit": "set", "unit_price": "10"},
                  {"id": "l3", "kind": "travel", "label": "Déplacement", "amount": "10"}],
        "allocations": [{"line_id": "l1", "stay_id": s1, "amount": "60"}, {"line_id": "l2", "stay_id": s1, "amount": "24"},
                        {"line_id": "l3", "stay_id": s1, "amount": "6"}, {"line_id": "l1", "stay_id": s2, "amount": "40"},
                        {"line_id": "l2", "stay_id": s2, "amount": "16"}, {"line_id": "l3", "stay_id": s2, "amount": "4"}],
        "paid": True, "paid_date": (inv_month + timedelta(days=24)).isoformat(),
    })
    assert invoice["entry"]["amount"] == 15000
    # Its PDF (fictional, generated identically every time), to find it again from the expense.
    pdf = documents.SAMPLES["demo-invoice-018"]()
    led.add_document({"property_id": a, "entry_id": invoice["entry"]["id"], "supplier_id": cleaner, "invoice_number": "F-DEMO-018",
                      "invoice_date": invoice["entry"]["date"], "amount_cents": 15000},
                     {"sha256": documents.sha256(pdf), "size": len(pdf), "pages": 1, "text_found": True,
                      "filename": "Facture F-DEMO-018 (fictive).pdf", "sample": "demo-invoice-018"})

    # --- Example month: exactly the documented figures.
    f = focus_start
    a1 = stay(a, "A", f + timedelta(days=2), 3, "350", 4)
    a2 = stay(a, "A", f + timedelta(days=9), 2, "250", 2)
    b1 = stay(b, "B", f + timedelta(days=14), 4, "400", 2)
    # Commissions 3 %: 10.50 + 7.50 + 12.00 = 30 €.
    expense(a, "cleaning", "Ménage de départ", f + timedelta(days=5), "25", supplier=cleaner, stay_id=a1)
    expense(a, "cleaning", "Ménage de départ", f + timedelta(days=11), "25", supplier=cleaner, stay_id=a2)
    expense(b, "cleaning", "Ménage de départ", f + timedelta(days=18), "30", supplier=cleaner, stay_id=b1)
    expense(a, "linen", "Linge", f + timedelta(days=11), "12", supplier=cleaner)
    expense(b, "linen", "Linge", f + timedelta(days=18), "8", supplier=cleaner)
    expense(a, "travel", "Déplacement", f + timedelta(days=11), "6", supplier=cleaner)
    expense(b, "travel", "Déplacement", f + timedelta(days=18), "4", supplier=cleaner)
    expense(a, "maintenance", "Réparation volet (fictif)", f + timedelta(days=19), "34", supplier=workshop)
    expense(b, "maintenance", "Réparation serrure (fictif)", f + timedelta(days=19), "26", supplier=workshop)

    # Loan instalment of 200 € every month on Appartement A: financing, outside the operating balance.
    month = history_start
    while month <= focus_start:
        expense(a, "loan", "Mensualité de prêt (fictif)", month + timedelta(days=4), "200", supplier=bank,
                loan_split={"principal": "150", "interest": "40", "insurance": "10"})
        month = _shift_month(month, 1)

    # --- Upcoming stays (after the example month and after today).
    base = max(today + timedelta(days=2), focus_end)
    stay(a, "A", base + timedelta(days=1), 3, "360", 4, status="confirmed")
    stay(b, "B", base + timedelta(days=9), 3, "285", 2, status="confirmed")
    stay(a, "A", base + timedelta(days=16), 4, "472", 3, status="confirmed")
    stay(b, "B", base + timedelta(days=24), 2, "190", 1, status="provisional")

    data["settings"]["onboarding"] = {"property": True, "first_record": True, "dashboard": False, "backup": False}
    data["audit"] = [{"at": data["created_at"], "by": DEMO_ACTOR, "action": "demo.build", "target": "registry", "result": "ok", "detail": "fictional data"}]
    return data
