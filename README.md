<div align="center">

# Rental Cockpit

### Track your holiday let and understand every figure

**Properties · Stays · Expenses · Documents · Suppliers · Results that explain themselves**

🇫🇷 [Lire en français](README.fr.md)

<img src="docs/images/en/overview-desktop.png" alt="Rental Cockpit overview on a computer, with fictional demo data" width="100%">

<sub>The screenshots show the built-in demo: two fictional properties, "Démo" suppliers and invented amounts.</sub>

**Self-hosted · Local-first · Bilingual French / English · No outside service required**

</div>

---

> [!IMPORTANT]
> **Preview 0.1.0, under development.** The **Overview** screen works end to end (accounts, demo, explained indicators, creating a property). The Stays, Expenses, Suppliers, Documents and Settings screens come next, in the same style. This is not a stable release yet: do not keep your only copy of real data in it.

## Who is it for?

For individuals who rent out one or more homes (holiday lets or longer lets) and want to follow revenue and expenses, keep their documents and **understand** every result — without learning bookkeeping or handing their data to an online service.

Rental Cockpit is a standalone web application you run at home (a Docker container or a plain Python process). It depends on no other software for installation, sign-in, storage or interface.

## What works today

| | |
|---|---|
| **Guided first start** | No default account: the first visit creates the administrator. Then two explicit choices: *Use my data* or *Explore the demo*. |
| **Separate demo** | Fictional data lives in its own registry and never touches your real data. A permanent banner marks it. |
| **Three readings** | *Activity* (what the rental produced, stays spread night by night), *Invoices* (each document on its date), *Cash* (money actually received or paid). They are never mixed. |
| **"How is this amount calculated?"** | Every indicator shows its formula, period, properties included, what is excluded and **every line used**. |
| **Computed changes** | Percentages compare the period with the previous one using the same rules. |
| **To check** | What keeps a result from being final: unknown payments, stays without an amount, payouts not received, amounts left to allocate. |
| **My properties** | Revenue, expenses and balance per property; a property is created in seconds. |
| **Computer, tablet, phone** | Sidebar, top tabs or bottom bar depending on the width. |

<table>
<tr>
<td width="50%"><img src="docs/images/en/explain.png" alt="Explanation of an indicator: formula, period, exclusions and lines used"></td>
<td width="25%"><img src="docs/images/en/overview-phone.png" alt="Overview on a phone"></td>
<td width="25%"><img src="docs/images/en/first-account.png" alt="Creating the first administrator account"></td>
</tr>
</table>

## Calculation rules in short

- Amounts are stored as **whole cents**: no floating-point rounding, totals reconcile to the cent.
- A stay from 10 to 12 June is **two nights**: the departure day is not a night.
- An unknown value is **never shown as zero**: the result is flagged as incomplete.
- A due date, a "paid in cash" mention or an attached PDF **is not a payment**.
- An invoice split between several stays remains **one expense**.
- The *balance before financing* excludes loans, taxes and investments; it is **not a taxable profit**.

A checkable example (reproduced in the demo's example month): €1,000 revenue − €30 commission − €80 cleaning − €20 linen − €10 travel − €60 repair = **€800** before financing; with a €200 loan instalment paid the same month, cash after financing is **€600**.

Details: [docs/en/calculations.md](docs/en/calculations.md).

## Installation

**With Docker Compose** (recommended):

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose up -d --build
```

Then open `http://<machine-address>:8080` and create the administrator account.

**Without Docker** (Python 3.11 or newer):

```bash
pip install .
RENTAL_COCKPIT_DATA_DIR=./data uvicorn --factory rental_cockpit.app:create_app --host 127.0.0.1 --port 8080
```

All options, upgrading and backing up the data folder: [docs/en/installation.md](docs/en/installation.md).

## Privacy and security

- Data stays in one folder (`/data`): a SQLite database and, later, the private PDFs. No telemetry, no outbound call.
- Hashed passwords (scrypt), signed `HttpOnly` and `SameSite=Strict` session, anti-CSRF token on every change, lock after five failed sign-ins, strict Content-Security-Policy (no external or inline script or style).
- Rights are checked on the server for every request: a reader only sees the properties granted to them, and access to PDFs is a separate permission.
- Keep the application on your local network or behind an HTTPS reverse proxy; do not expose it directly to the Internet.

See [SECURITY.md](SECURITY.md) and [docs/en/security.md](docs/en/security.md).

## Documentation

| Document | Content |
|---|---|
| [Installation](docs/en/installation.md) | Docker, Python, variables, upgrading, backing up the data folder |
| [Getting started](docs/en/guide.md) | The first ten minutes, with the demo |
| [Calculation rules](docs/en/calculations.md) | The three readings, each indicator, glossary |
| [Architecture and adaptations](docs/en/architecture.md) | What is reused from the original project, what changes with a standalone application |
| [Security](docs/en/security.md) | Accounts, rights, data, network exposure |
| [Roadmap](docs/en/roadmap.md) | Screens and work packages to come |

## Licence

**To be decided.** No licence is granted on this code yet; until a licence is published in this repository, default copyright applies.

The bundled fonts (Source Serif 4 and Inter) are distributed under the SIL Open Font License 1.1: see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Copyright © 2026 Vincent Fournet
