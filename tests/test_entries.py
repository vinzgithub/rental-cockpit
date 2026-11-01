# Copyright © 2026 Vincent Fournet
"""Expenses and payments (delivery L3, 0.4.0): engine rules, monthly series, exports and the « Dépenses » API.

Fictional data only. The figures are the ones of the validation scenario
given to the independent testers in the pull request.
"""
from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine import entries as entry_views
from rental_cockpit.engine import exports
from rental_cockpit.engine.errors import RCError
from rental_cockpit.engine.indicators import compute, month_period
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.schema import empty_registry
from rental_cockpit.security import hash_password

TODAY = date(2026, 11, 1)
PASSWORD = "un-mot-de-passe-long"
KEYS = ("revenue", "operating_expenses", "operating_balance", "financing", "balance_after_financing", "to_pay", "to_receive")


def figures(data, pid, year, month, mode):
    start, end = month_period(year, month)
    ind = compute(data, property_ids={pid}, start=start, end=end, mode=mode, lang="fr", today=TODAY)["indicators"]
    return {key: ind[key]["value"] for key in KEYS}


@pytest.fixture
def house():
    data = empty_registry()
    ledger = Ledger(data, "1")
    pid = ledger.create_property({"name": "Gîte d'essai"})["property"]["id"]
    return data, ledger, pid


def expense(ledger, pid, **fields):
    payload = {"property_id": pid, "kind": "expense", "category_id": "maintenance", "label": "Réparation", "amount": "100",
               "date": "2026-10-10", **fields}
    return ledger.create_entry(payload)["entry"]


# --------------------------------------------------------------------------- engine


def test_payment_status_follows_the_real_payments(house):
    data, ledger, pid = house
    unknown = expense(ledger, pid, label="Ménage", category_id="cleaning", amount="80")
    due = expense(ledger, pid, amount="300", payment_declared="unpaid")
    assert entry_views.summary(data, data["entries"][unknown["id"]], "fr")["state_label"] == "Paiement à confirmer"
    assert entry_views.summary(data, data["entries"][due["id"]], "fr")["state"] == "unpaid"
    ledger.create_payment({"property_id": pid, "direction": "out", "date": "2026-10-12", "amount": "100",
                           "links": [{"type": "entry", "id": due["id"], "amount": "100"}]})
    item = entry_views.summary(data, data["entries"][due["id"]], "fr")
    assert (item["state"], item["paid"], item["remaining"], item["state_label"]) == ("partial", 10000, 20000, "Partiellement payée")
    with pytest.raises(RCError) as over:
        ledger.create_payment({"property_id": pid, "direction": "out", "date": "2026-10-13", "amount": "250",
                               "links": [{"type": "entry", "id": due["id"], "amount": "250"}]})
    assert over.value.code == "payment_exceeds"
    # Activity and Invoices count the whole expense on its date; Cash only what left the account.
    assert figures(data, pid, 2026, 10, "activity")["operating_expenses"] == 38000
    assert figures(data, pid, 2026, 10, "cash")["operating_expenses"] == 10000
    assert figures(data, pid, 2026, 10, "activity")["to_pay"] == 28000


def test_amount_cannot_go_below_what_was_paid(house):
    data, ledger, pid = house
    entry = expense(ledger, pid, amount="300", paid=True, paid_date="2026-10-10")
    with pytest.raises(RCError) as refused:
        ledger.update_entry(entry["id"], {"amount": "250"})
    assert refused.value.code == "entry_amount_below_paid"


def test_income_outside_stays_is_to_receive_until_paid(house):
    data, ledger, pid = house
    income = ledger.create_entry({"property_id": pid, "kind": "income", "category_id": "other_income", "label": "Remboursement sinistre",
                                  "amount": "150", "date": "2026-10-20", "payment_declared": "unpaid"})["entry"]
    assert entry_views.summary(data, data["entries"][income["id"]], "fr")["state_label"] == "À recevoir"
    october = figures(data, pid, 2026, 10, "activity")
    assert (october["revenue"], october["to_receive"]) == (15000, 15000)
    ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-10-25", "amount": "150",
                           "links": [{"type": "entry", "id": income["id"], "amount": "150"}]})
    assert figures(data, pid, 2026, 10, "cash")["revenue"] == 15000
    assert figures(data, pid, 2026, 10, "activity")["to_receive"] == 0


def test_coverage_period_is_spread_day_by_day(house):
    data, ledger, pid = house
    expense(ledger, pid, category_id="insurance", label="Assurance PNO", amount="240", date="2026-11-01",
            period_start="2026-11-01", period_end="2027-11-01")
    # 24 000 cents over 365 days, to the cent (largest remainder): 30 days of November = 19.80 €.
    assert figures(data, pid, 2026, 11, "activity")["operating_expenses"] == 1980
    assert figures(data, pid, 2026, 11, "invoice")["operating_expenses"] == 24000
    total = sum(figures(data, pid, *divmod(index, 12), "activity")["operating_expenses"]
                for index in range(2026 * 12 + 10, 2027 * 12 + 11) if divmod(index, 12)[1])
    assert total <= 24000


def test_monthly_series_for_a_loan(house):
    data, ledger, pid = house
    result = entry_views.create_series(ledger, {
        "property_id": pid, "kind": "expense", "category_id": "loan", "label": "Mensualité de prêt", "amount": "500",
        "date": "2026-01-31", "payment_declared": "unpaid", "loan_split": {"principal": "350", "interest": "120", "insurance": "30"}}, 12, TODAY)
    created = [data["entries"][i] for i in result["series"]["entries"]]
    assert [e["date"] for e in created][:3] == ["2026-01-31", "2026-02-28", "2026-03-31"]
    assert [e["series"]["index"] for e in created] == list(range(1, 13)) and created[0]["series"]["count"] == 12
    october = figures(data, pid, 2026, 10, "activity")
    # Financing stays outside the operating balance.
    assert (october["operating_balance"], october["financing"], october["balance_after_financing"]) == (0, 50000, -50000)
    with pytest.raises(RCError):
        entry_views.create_series(ledger, {"property_id": pid, "kind": "expense", "category_id": "loan", "label": "x",
                                           "amount": "1", "date": "2026-01-01"}, 40, TODAY)


def test_series_marked_paid_only_settles_the_dates_already_past(house):
    data, ledger, pid = house
    result = entry_views.create_series(ledger, {
        "property_id": pid, "kind": "expense", "category_id": "subscription", "label": "Box internet", "amount": "30",
        "date": "2026-09-07", "paid": True, "payment_method": "Prélèvement"}, 4, TODAY)
    states = [entry_views.summary(data, data["entries"][i], "fr")["state"] for i in result["series"]["entries"]]
    assert states == ["paid", "paid", "unpaid", "unpaid"]
    assert result["series"]["payments"] == 2


def test_delete_only_without_payment(house):
    data, ledger, pid = house
    paid = expense(ledger, pid, paid=True, paid_date="2026-10-10")
    with pytest.raises(RCError) as refused:
        ledger.delete_entry(paid["id"])
    assert refused.value.code == "entry_has_payments"
    mistake = expense(ledger, pid)
    ledger.delete_entry(mistake["id"])
    assert mistake["id"] not in data["entries"]


def test_archived_entry_leaves_every_total(house):
    data, ledger, pid = house
    entry = expense(ledger, pid, category_id="cleaning", amount="80")
    assert figures(data, pid, 2026, 10, "activity")["operating_expenses"] == 8000
    ledger.set_entry_archived(entry["id"], True)
    assert figures(data, pid, 2026, 10, "activity")["operating_expenses"] == 0
    assert figures(data, pid, 2026, 10, "activity")["to_pay"] == 0


def test_archived_category_cannot_be_chosen(house):
    data, ledger, pid = house
    custom = ledger.create_category({"kind": "expense", "treatment": "operating_expense", "label": "Conciergerie"})["category"]
    entry = expense(ledger, pid)
    ledger.update_category(custom["id"], {"archived": True})
    with pytest.raises(RCError):
        ledger.update_entry(entry["id"], {"category_id": custom["id"]})
    with pytest.raises(RCError):
        expense(ledger, pid, category_id=custom["id"])


def test_csv_export_neutralises_formulas_and_keeps_numbers(house):
    data, ledger, pid = house
    entry = expense(ledger, pid, label="=HYPERLINK(\"x\")", amount="1234.5", note="+33 test", invoice_number="-F1")
    item = entry_views.summary(data, data["entries"][entry["id"]], "fr")
    rows = list(csv.reader(io.StringIO(exports.entries_csv(data, [item], "fr").decode("utf-8-sig")), delimiter=";"))
    assert rows[0][:3] == ["Date", "Bien", "Type"]
    line = dict(zip(rows[0], rows[1], strict=True))
    assert line["Libellé"] == "'=HYPERLINK(\"x\")" and line["Note"] == "'+33 test" and line["N° de facture"] == "'-F1"
    assert line["Montant"] == "1234,50" and line["Reste"] == "1234,50" and line["État du paiement"] == "Paiement à confirmer"
    english = list(csv.reader(io.StringIO(exports.entries_csv(data, [entry_views.summary(data, data["entries"][entry["id"]], "en")], "en")
                                          .decode("utf-8-sig"))))
    assert english[1][english[0].index("Amount")] == "1234.50"


# --------------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path):
    client = TestClient(create_app(Config(data_dir=tmp_path)))
    client.app.state.services.today = lambda: TODAY
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    client.post("/api/start", json={"choice": "own_data"})
    return client


def new_property(client, name="Gîte d'essai") -> str:
    return client.post("/api/properties", json={"name": name, "op_id": f"op-{name}"}).json()["property"]["id"]


def post(client, path, body, op):
    response = client.post(path, json={**body, "op_id": op}, params={"lang": "fr"})
    assert response.status_code == 200, response.text
    return response.json()


def test_api_scenario_views_totals_and_payments(client):
    pid = new_property(client)
    post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage de départ",
                                  "amount": "80", "date": "2026-10-05"}, "op-1")
    repair = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "maintenance",
                                           "label": "Réparation chauffe-eau", "amount": "300", "date": "2026-10-10",
                                           "payment_declared": "unpaid"}, "op-2")
    assert repair["detail"]["state_label"] == "À payer"
    paid = post(client, f"/api/entries/{repair['entry']['id']}/payments", {"date": "2026-10-12", "amount": "100", "method": "Carte"}, "op-3")
    assert (paid["detail"]["state"], paid["detail"]["remaining"]) == ("partial", 20000)
    over = client.post(f"/api/entries/{repair['entry']['id']}/payments", json={"date": "2026-10-13", "amount": "250", "op_id": "op-4"},
                       params={"lang": "fr"})
    assert over.status_code == 400 and "200,00" in over.json()["message"]
    loan = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "loan", "label": "Mensualité de prêt",
                                         "amount": "500", "date": "2026-10-05", "payment_declared": "unpaid", "repeat_months": 12,
                                         "loan_split": {"principal": "350", "interest": "120", "insurance": "30"}}, "op-5")
    assert len(loan["series"]["entries"]) == 12 and loan["detail"]["series"]["index"] == 1
    post(client, f"/api/entries/{loan['entry']['id']}/payments", {"date": "2026-10-05", "amount": "500"}, "op-6")
    post(client, "/api/entries", {"property_id": pid, "kind": "income", "category_id": "other_income", "label": "Remboursement sinistre",
                                  "amount": "150", "date": "2026-10-20", "payment_declared": "unpaid"}, "op-7")

    listing = client.get("/api/entries", params={"property_id": pid}).json()
    # The eleven next instalments are planned, not due yet: they stay out of « À payer » until their date.
    assert listing["counts"] == {"all": 15, "to_pay": 1, "to_confirm": 1, "to_receive": 1, "archived": 0}
    # Left to pay: the repair (200 €) and the cleaning whose payment is still to confirm (80 €), like the Overview.
    assert (listing["totals"]["to_pay"], listing["totals"]["upcoming"]) == (28000, 11 * 50000)
    assert [e["upcoming"] for e in listing["entries"]][:4] == [False] * 4 and listing["entries"][4]["upcoming"] is True
    assert listing["entries"][0]["label"] == "Remboursement sinistre"  # newest first, then what comes next
    assert listing["entries"][4]["date"] == "2026-11-05"
    to_pay = client.get("/api/entries", params={"property_id": pid, "view": "to_pay"}).json()
    assert [e["label"] for e in to_pay["entries"]] == ["Réparation chauffe-eau"] and to_pay["totals"]["to_pay"] == 20000
    october = client.get("/api/overview", params={"property_id": pid, "start": "2026-10-01", "end": "2026-11-01"}).json()["indicators"]
    assert (october["operating_expenses"]["value"], october["financing"]["value"], october["revenue"]["value"]) == (38000, 50000, 15000)
    assert (october["to_pay"]["value"], october["to_receive"]["value"]) == (28000, 15000)
    cash = client.get("/api/overview", params={"property_id": pid, "start": "2026-10-01", "end": "2026-11-01", "mode": "cash"}).json()["indicators"]
    assert (cash["operating_expenses"]["value"], cash["financing"]["value"]) == (10000, 50000)
    search = client.get("/api/entries", params={"property_id": pid, "q": "chauffe"}).json()
    assert [e["label"] for e in search["entries"]] == ["Réparation chauffe-eau"]
    assert client.get("/api/entries", params={"property_id": pid, "kind": "income"}).json()["totals"]["income"] == 15000
    assert listing["years"] == ["2027", "2026"]


def test_api_edit_archive_delete_and_payment_removal(client):
    pid = new_property(client)
    entry = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage",
                                          "amount": "80", "date": "2026-10-05", "paid": True}, "op-1")["detail"]
    edited = client.patch(f"/api/entries/{entry['id']}", json={"label": "Ménage de départ", "revision": entry["revision"], "op_id": "op-2"})
    assert edited.status_code == 200 and edited.json()["detail"]["label"] == "Ménage de départ"
    stale = client.patch(f"/api/entries/{entry['id']}", json={"label": "Autre", "revision": entry["revision"], "op_id": "op-3"})
    assert stale.status_code == 409
    refused = client.request("DELETE", f"/api/entries/{entry['id']}", json={"op_id": "op-4"})
    assert refused.json()["code"] == "entry_has_payments"
    payment = edited.json()["detail"]["payments"][0]
    undone = client.request("DELETE", f"/api/payments/{payment['id']}", json={"op_id": "op-5"})
    assert undone.json()["detail"]["state"] == "unknown"
    archived = post(client, f"/api/entries/{entry['id']}/archive", {}, "op-6")
    assert archived["detail"]["archived"] is True
    assert client.get("/api/entries", params={"view": "archived"}).json()["counts"]["archived"] == 1
    post(client, f"/api/entries/{entry['id']}/archive", {"archived": False}, "op-7")
    assert client.request("DELETE", f"/api/entries/{entry['id']}", json={"op_id": "op-8"}).json()["deleted"] == entry["id"]
    assert client.get(f"/api/entries/{entry['id']}").status_code == 404


def test_api_categories(client):
    created = post(client, "/api/categories", {"kind": "expense", "treatment": "operating_expense", "label": "Conciergerie"}, "op-1")
    custom = next(c for c in created["categories"] if c["label"] == "Conciergerie")
    assert custom["builtin"] is False and custom["treatment_label"] == "Dépense d'exploitation"
    response = client.patch("/api/categories/energy", json={"label": "Électricité et eau", "op_id": "op-2"}, params={"lang": "fr"})
    energy = next(c for c in response.json()["categories"] if c["id"] == "energy")
    assert (energy["label"], energy["default_label"]) == ("Électricité et eau", "Énergie")
    client.patch(f"/api/categories/{custom['id']}", json={"archived": True, "op_id": "op-3"})
    listing = client.get("/api/categories").json()
    assert next(c for c in listing["categories"] if c["id"] == custom["id"])["archived"] is True
    assert [t["id"] for t in listing["treatments"]["income"]] == ["operating_income", "information"]
    wrong = client.post("/api/categories", json={"kind": "income", "treatment": "financing", "label": "x", "op_id": "op-4"})
    assert wrong.status_code == 400
    nameless = client.patch(f"/api/categories/{custom['id']}", json={"label": " ", "op_id": "op-5"})
    assert nameless.status_code == 400
    reset = client.patch("/api/categories/energy", json={"label": "", "op_id": "op-6"}, params={"lang": "fr"})
    assert next(c for c in reset.json()["categories"] if c["id"] == "energy")["label"] == "Énergie"


def test_api_exports(client):
    pid = new_property(client)
    post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "=1+1",
                                  "amount": "80", "date": "2026-10-05"}, "op-1")
    post(client, "/api/stays", {"property_id": pid, "start": "2026-09-28", "end": "2026-10-04", "guest_label": "@client",
                                "amounts": {"gross": "600", "commission": "90"}}, "op-2")
    response = client.get("/api/export/entries.csv", params={"lang": "fr"})
    assert response.headers["content-type"].startswith("text/csv") and "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[1][rows[0].index("Libellé")] == "'=1+1"
    stays = list(csv.reader(io.StringIO(client.get("/api/export/stays.csv", params={"lang": "fr"}).content.decode("utf-8-sig")), delimiter=";"))
    line = dict(zip(stays[0], stays[1], strict=True))
    assert (line["Libellé"], line["Nuits"], line["Montant brut"], line["Versement net attendu"]) == ("'@client", "6", "600,00", "510,00")


def test_api_reader_reads_and_exports_granted_entries_only(client):
    pid = new_property(client)
    other = new_property(client, "Autre bien")
    mine = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage",
                                         "amount": "80", "date": "2026-10-05"}, "op-1")["entry"]
    hidden = post(client, "/api/entries", {"property_id": other, "kind": "expense", "category_id": "cleaning", "label": "Secret",
                                           "amount": "90", "date": "2026-10-05"}, "op-2")["entry"]
    db = client.app.state.services.db
    with db.transaction() as conn:
        conn.execute("INSERT INTO users(username, display_name, password_hash, role, created_at, updated_at) VALUES ('lecteur', '', ?, 'reader', '2026-10-31', '2026-10-31')",
                     (hash_password(PASSWORD),))
        uid = conn.execute("SELECT id FROM users WHERE username = 'lecteur'").fetchone()[0]
        conn.execute("INSERT INTO grants(user_id, property_id, documents) VALUES (?, ?, 0)", (uid, pid))
    reader = TestClient(client.app)
    token = reader.get("/api/session").json()["csrf"]
    reader.headers["X-CSRF-Token"] = reader.post("/api/auth/login", json={"username": "lecteur", "password": PASSWORD},
                                                 headers={"X-CSRF-Token": token}).json()["csrf"]
    assert [e["id"] for e in reader.get("/api/entries").json()["entries"]] == [mine["id"]]
    assert reader.get(f"/api/entries/{hidden['id']}").status_code == 403
    assert "Secret" not in reader.get("/api/export/entries.csv").content.decode("utf-8-sig")
    assert reader.post("/api/entries", json={"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "x",
                                             "amount": "1", "date": "2026-10-05"}).status_code == 403
    assert reader.post(f"/api/entries/{mine['id']}/payments", json={"date": "2026-10-05", "amount": "80"}).status_code == 403
    assert reader.patch("/api/categories/energy", json={"label": "x"}).status_code == 403


def test_api_csrf_and_demo_separation(client):
    client.post("/api/start", json={"choice": "demo"})
    demo = client.get("/api/entries", params={"dataset": "demo"}).json()
    assert demo["entries"] and demo["counts"]["to_confirm"] > 0  # the demo shows payments to confirm
    assert client.get("/api/entries").json()["entries"] == []
    pid = new_property(client)
    del client.headers["X-CSRF-Token"]
    refused = client.post("/api/entries", json={"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "x",
                                                "amount": "1", "date": "2026-10-05"})
    assert refused.status_code == 403 and refused.json()["code"] == "csrf_failed"
