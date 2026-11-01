<div align="center">

# 🏡 Rental Cockpit

### Your holiday let, every figure explained

**Overview · Stays · Airbnb and CSV import · Expenses and payments · Three readings · Explained indicators · To check · Two-factor sign-in · Home Assistant**

[**Français**](README.fr.md) · **English**

![Version](https://img.shields.io/badge/version-0.4.0%20preview-126caa) ![Docker](https://img.shields.io/badge/Docker-amd64%20%7C%20arm64-2496ED) ![Licence](https://img.shields.io/badge/licence-to%20be%20decided-lightgrey)

<br>

<img src="docs/images/en/hero.png"
     alt="Rental Cockpit on a computer and a phone: month overview, three readings, properties and data to check"
     width="100%">

<sub>The screenshots show the built-in demo: two fictional properties, "Démo" suppliers and invented amounts.</sub>

<br><br>

**Self-hosted · Local-first · Bilingual (FR / EN) · No outside service**

</div>

---

## 🚀 At a glance

<table>
<tr>
<td width="33%" valign="top"><b>🧾 Every figure explains itself</b><br>Under each amount, "How is this amount calculated?": formula, period, exclusions and every line used.</td>
<td width="33%" valign="top"><b>🔀 Three readings, never mixed</b><br>Activity, Invoices, Cash: three different questions, three stated calculation rules.</td>
<td width="33%" valign="top"><b>✅ What is left to check</b><br>Unknown payments, stays without an amount, payouts not received: an incomplete result is flagged, never disguised as zero.</td>
</tr>
<tr>
<td valign="top"><b>📅 Complete stays</b><br>Entered by hand or imported from Airbnb or a CSV after a check; cancelled with the fee retained, payouts followed: each stay shows its share of the Overview.</td>
<td valign="top"><b>🔐 Two-factor sign-in</b><br>A code from an authenticator app after the password, and ten single-use recovery codes.</td>
<td valign="top"><b>🏠 Home Assistant, if you like</b><br>A read-only key: revenue, occupancy, next arrival, and automations such as heating the day before an arrival.</td>
</tr>
</table>

> [!NOTE]
> **Version 0.4.0, preview.** The Overview, **stays** (entry, **Airbnb and CSV import**, cancellation, payouts received), **expenses and payments** (partial payments, loan instalments, categories, CSV export), the demo, accounts, two-factor sign-in and the Home Assistant link are ready. **Suppliers** (splitting an invoice between stays) and **PDF documents** come in the next versions.

---

## ✨ Why Rental Cockpit?

Renting out a home means juggling platform payouts already cut by the commission, a cleaning invoice covering three stays, a loan instalment, a tax that falls once a year… At the end of the month, one simple question has no clear answer: **what did the rental actually bring in?**

A spreadsheet gives a figure; it does not say where it comes from. Rental Cockpit does the opposite: **every amount shows its calculation**, every incomplete result is flagged, and nothing is ever counted twice.

It grew out of a personal tool for tracking a holiday let and reuses its calculation rules, in a standalone application you run at home. No subscription, no online account: your data stays on your server.

---

## 🧾 "How is this amount calculated?"

<table>
<tr>
<td width="60%" valign="top"><img src="docs/images/en/explain-card.png" alt="Explanation of an indicator: formula, period, exclusions and lines used"></td>
<td width="40%" valign="top">

One click under any indicator opens its explanation:

- the **equation**: Revenue − Expenses = Balance;
- the **formula**, **period**, **reading** and **properties included**;
- what is **excluded**, and why;
- **every line used**, with the rule applied to each — "Spread night by night over the stay", "Counted on its date"… — and the total.

No black box: you can redo every calculation by hand.

</td>
</tr>
</table>

---

## 📅 Stays, from booking to payout

<img src="docs/images/en/stays-desktop.png" alt="List of stays with their status and payout status" width="100%">

<table>
<tr>
<td width="55%" valign="top"><img src="docs/images/en/stay-detail-card.png" alt="A stay across two months: amounts, month-by-month split, payout received"></td>
<td width="45%" valign="top">

- **Guided entry**: property, dates (nights per month shown at once), booking channel, gross amount and commission; the expected net payout is computed.
- **Tourist tax and security deposit** recorded apart: never counted as revenue.
- **Stay page**: what was received, what is left to receive, and **what the stay counts in the Overview**, month by month.
- **Payout received** in one click: the Cash reading updates.
- **Cancellation** with the amount retained, counted on the arrival date; **Restore** brings everything back.
- Explicit statuses: *Upcoming*, *In progress*, *Finished*, *Provisional*, *Cancelled*; *Payout expected*, *to confirm*, *received*.

</td>
</tr>
</table>

---

## 📥 Airbnb and CSV import, checked before writing

<img src="docs/images/en/import-preview.png" alt="Import preview: each line of the file with its status, amounts, payout and the decision to take" width="100%">

<table>
<tr>
<td width="38%" valign="top"><img src="docs/images/en/import-phone.png" alt="CSV import on a phone: commission computed from the rate, probable duplicate, new stays"></td>
<td width="62%" valign="top">

- **Airbnb export** (French "Historique des transactions") or **any CSV**: Booking.com, Abritel, spreadsheet.
- **Nothing is written before you confirm**: each line says what will happen — *New*, *Updated* (field by field), *Probable duplicate*, *Up to date*, *Error*.
- **Duplicates detected**: same reference, or same dates as a stay entered by hand; you choose to complete it, create another one or skip the line.
- **Commissions** read from the file, or computed from the platform's rate, to the cent.
- **Checks**: unreadable dates, nights that do not match, overlaps, unavailable dates, negative amounts, payout above what is expected.
- **Payouts** dated in the file are recorded once; Airbnb transfers are never counted twice.
- **Columns and properties remembered** for the next file; the last import can be **undone** in one click.

</td>
</tr>
</table>

---

## 💳 Expenses and payments, nothing assumed paid

<img src="docs/images/en/expenses-desktop.png" alt="List of expenses with their payment status, the totals to pay and to receive, the instalments to come" width="100%">

<table>
<tr>
<td width="38%" valign="top"><img src="docs/images/en/expenses-phone.png" alt="Expenses on a phone: totals and cards with the payment status"></td>
<td width="62%" valign="top">

- **Expenses and income outside stays**: cleaning, repairs, insurance, subscriptions, refunds… each in a category whose **treatment** is stated (operations, investment, financing, taxes).
- **Explicit payment status**: *Paid*, *Partly paid*, *To pay* or *Payment to confirm* — nothing is assumed paid.
- **Partial payments**, never above what is left; the Cash reading counts each payment on its date.
- **Loan instalments**: principal, interest and insurance checked to the cent, outside the operating balance; **monthly repetition** up to 36 months, future instalments staying *Coming up*.
- **Period covered**: an annual insurance is spread day by day in the Activity reading.
- **Categories** you can adapt in Settings; **CSV export** ready for a spreadsheet or an accountant.

</td>
</tr>
</table>

<img src="docs/images/en/overview-settle.png" alt="Overview: loan repayments broken down, balance after financing, left to pay and to receive" width="100%">

---

## 🔀 Same month, several questions

<img src="docs/images/en/readings.png" alt="The same month in the Activity reading, then in the Cash reading" width="100%">

<sub>Top, the Activity reading; bottom, the Cash reading of the same month: €970 actually received, the €30 commission being already taken off the payout.</sub>

| Reading | The question | The rule |
|---|---|---|
| **Activity** | What did the rental produce during the period? | A stay is spread night by night; an expense counts on its date or over the period it covers |
| **Invoices** | Which documents are dated in the period? | Each invoice on its date, each stay on its arrival date |
| **Cash** | What money actually came in or went out? | Payments only, on their date |

Percentages always compare the period with the previous one, **computed with the same rules**.

### An example you can check

It is reproduced exactly in the demo's example month:

```text
   €1,000   stay revenue
 −    €30   platform commission
 −    €80   cleaning
 −    €20   linen
 −    €10   travel
 −    €60   repair
 ─────────
     €800   balance before financing
 −   €200   loan instalment
 ─────────
     €600   cash after financing
```

### Rules that never move

- Amounts are stored as **whole cents**: no floating-point rounding, totals reconcile to the cent.
- A stay from 10 to 12 June is **two nights**: the departure day is not a night.
- An unknown value is **never shown as zero**: the result is flagged as incomplete.
- A due date, a "paid in cash" mention or an attached PDF **is not a payment**.
- An invoice split between several stays remains **one expense**.
- The *balance before financing* excludes loans, taxes and investments: it is **not a taxable profit**.

📖 [All calculation rules](docs/en/calculations.md)

---

## 📱 Computer, tablet, phone

<table>
<tr>
<td width="46%" valign="top"><img src="docs/images/en/overview-tablet.png" alt="Overview on a tablet"></td>
<td width="27%" valign="top"><img src="docs/images/en/overview-phone.png" alt="Overview on a phone"></td>
<td width="27%" valign="top"><img src="docs/images/en/stays-phone.png" alt="Stays on a phone"></td>
</tr>
<tr>
<td align="center"><b>On a tablet</b></td>
<td align="center"><b>On a phone</b></td>
<td align="center"><b>Stays, thumb-friendly</b></td>
</tr>
</table>

Sidebar on a large screen, top tabs on a tablet, bottom bar on a phone. On touch screens, every control aims at 44 × 44 pixels.

---

## 🎮 Up and running in two minutes

<table>
<tr>
<td width="50%" valign="top"><img src="docs/images/en/first-account-card.png" alt="Creating the first administrator account"></td>
<td width="50%" valign="top"><img src="docs/images/en/welcome-card.png" alt="Welcome screen: use my data or explore the demo"></td>
</tr>
<tr>
<td align="center"><b>1. The administrator account</b><br><sub>No default account: the first visit creates it.</sub></td>
<td align="center"><b>2. Your data or the demo</b><br><sub>Two explicit choices, each one reversible.</sub></td>
</tr>
</table>

With the demo, everything is already filled in: a permanent banner reminds you the figures are fictional. With your data, you start from an empty space and create your first property — only the name is required. The **My data / Demo** switch takes you from one to the other at any time.

📖 [Getting started: the first ten minutes](docs/en/guide.md)

---

## 🏠 Home Assistant, as an option

Rental Cockpit does **not need** Home Assistant. But if you use it, a read-only key is enough to show your figures and trigger automations, with the RESTful integration that is already included: nothing to install.

```yaml
rest:
  - resource: http://rental-cockpit.lan:8080/api/v1/summary?lang=en
    headers:
      Authorization: !secret rental_cockpit_authorization
    scan_interval: 900
    sensor:
      - name: Rental month balance
        value_template: "{{ value_json.month.balance_before_financing }}"
        unit_of_measurement: "EUR"
        device_class: monetary
    binary_sensor:
      - name: Rental arrival tomorrow
        value_template: "{{ value_json.properties | selectattr('arrival_tomorrow') | list | count > 0 }}"
```

Then: **heat the home the day before an arrival**, get told when a payment needs confirming, show tonight's occupancy on your dashboard…

- The key reads **what its account can read** and can **change nothing**.
- It is shown once, kept as a hash and can be revoked at any time.

<img src="docs/images/en/settings-desktop.png" alt="Settings: account, two-factor sign-in on and a key for Home Assistant" width="100%">

📖 [Home Assistant guide: sensors, card, automations, API reference](docs/en/home-assistant.md)

---

## 📦 Installation

A ready-made image is published for **x86-64 and ARM64** (including Raspberry Pi 4). No Python needed, no need to clone the repository:

```bash
mkdir rental-cockpit && cd rental-cockpit
curl -fsSLO https://raw.githubusercontent.com/vinzgithub/rental-cockpit/main/docker-compose.yml
docker compose up -d
```

Open `http://<machine-address>:8080`, create the administrator account, then explore the demo or start with your properties.

Upgrade: `docker compose pull && docker compose up -d`.

| Image | For |
|---|---|
| `ghcr.io/vinzgithub/rental-cockpit:latest` | The latest released version |
| `ghcr.io/vinzgithub/rental-cockpit:0.1` | Staying on 0.1.x versions |
| `ghcr.io/vinzgithub/rental-cockpit:edge` | Trying what is coming (main branch) |

> [!WARNING]
> Rental Cockpit holds your financial data. Keep it on your local network or behind a VPN, and back up the `/data` volume.

📖 [Full guide: Docker, Python, variables, backup, account recovery](docs/en/installation.md)

---

## 🔒 Secure by default

- No default account: the first visit creates the administrator
- Passwords hashed with scrypt, lock after five failures, anti-CSRF token on every change
- Optional two-factor sign-in: TOTP code after the password, single-use recovery codes
- Rights checked on the server for every request: a reader only sees the properties granted to them
- Strict Content-Security-Policy: no external script, font or tracker — Rental Cockpit never calls the Internet
- Read-only API keys, shown once and kept as a hash
- Imports checked before writing; CSV exports protected against formula injection
- Unprivileged container, read-only filesystem

<table>
<tr>
<td width="65%" valign="top"><img src="docs/images/en/mfa-card.png" alt="Turning on two-factor sign-in with a QR code"></td>
<td width="35%" valign="top"><img src="docs/images/en/login-code.png" alt="The code asked after the password, on a phone"></td>
</tr>
<tr>
<td align="center"><b>Two-factor sign-in in one scan</b></td>
<td align="center"><b>The code asked after the password</b></td>
</tr>
</table>

📖 [Security and data protection](docs/en/security.md) · [Report a vulnerability](SECURITY.md)

---

## 💾 Your data

Everything fits in **one folder**, `/data`: a SQLite database and, soon, your private PDF documents. The demo lives in its own registry and never mixes with your real data. No telemetry, no vendor account, no outbound call.

Until the built-in backup arrives, a copy of the volume is enough: the command is in the [installation guide](docs/en/installation.md#the-data-folder).

---

## 🗺️ Roadmap

| | Step | Content |
|:--:|---|---|
| ✅ | **0.1.0** | Overview, three readings, explained indicators, demo, accounts and rights, two-factor sign-in, Home Assistant link, Docker images |
| ✅ | **0.1.1** | Fixes from the independent audit: menu without empty screens, My data / Demo switch, explanations readable on a phone |
| ✅ | **0.2.0** | Stays: entry, cancellation and restoration, payouts received, each stay's share of the Overview |
| ✅ | **0.3.0** | Airbnb and CSV import: preview with nothing written, duplicates, commissions, checks, undo of the last import |
| ✅ | **0.4.0** | Expenses and payments: partial payments, to pay / to receive, loan instalments, categories, CSV export |
| 🔜 | **0.5.0 – 0.6.0** | Suppliers and invoice splitting; PDF documents |
| 🎯 | **1.0** | Checked backup, reader accounts, full acceptance run, first stable version |

📖 [Detailed roadmap](docs/en/roadmap.md)

---

## 📚 Documentation

| Document | Content |
|---|---|
| [Installation](docs/en/installation.md) | Docker image, Python, variables, upgrading, backup, account recovery |
| [Getting started](docs/en/guide.md) | The first ten minutes, with the demo |
| [Calculation rules](docs/en/calculations.md) | The three readings, each indicator, glossary |
| [Home Assistant](docs/en/home-assistant.md) | Optional link: sensors, automations, card, API reference |
| [Security](docs/en/security.md) | Accounts, two-factor sign-in, rights, API keys, data, network exposure |
| [Architecture and adaptations](docs/en/architecture.md) | What is reused from the original project, what changes with a standalone application |
| [Roadmap](docs/en/roadmap.md) | Screens and work packages to come |
| [Changelog](CHANGELOG.md) | What each version contains |

---

## 🛡️ Licence and copyright

**Copyright © 2026 Vincent Fournet.**

The licence is **to be decided**. No licence is granted on this code yet: until a licence is published in this repository, default copyright applies.

The bundled fonts (Source Serif 4 and Inter) are distributed under the SIL Open Font License 1.1: see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

## ℹ️ Disclaimer

Rental Cockpit is a tracking tool, not accounting software or tax advice: the balance before financing is not a taxable profit, and Rental Cockpit replaces neither your tax return nor an accountant.

The figures in the screenshots and documentation come from the fictional demo shipped with the application.

Airbnb, Abritel, Home Assistant and the other product or company names mentioned remain the property of their owners. Rental Cockpit is not affiliated with any of these companies.

---

<div align="center">

### 🏡 Rental Cockpit

**Every euro of your rental, explained.**

Copyright © 2026 Vincent Fournet

</div>
