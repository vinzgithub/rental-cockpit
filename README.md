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
> **Preview 0.1.0, under development.** The **Overview** screen works end to end (accounts, demo, explained indicators, creating a property), and so does the account part of **Settings** (password, two-factor sign-in, keys for Home Assistant). The Stays, Expenses, Suppliers and Documents screens come next, in the same style. This is not a stable release yet: do not keep your only copy of real data in it.

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
| **Two-factor sign-in** | Optional: six-digit code from an authenticator app (TOTP), ten single-use recovery codes, guided three-step setup. |
| **Home Assistant link** | Optional: read-only key and JSON summary (revenue, balance, occupied tonight, next arrival, to check) for your sensors, cards and automations. [Guide](docs/en/home-assistant.md) |
| **Computer, tablet, phone** | Sidebar, top tabs or bottom bar depending on the width. |

<table>
<tr>
<td width="50%"><img src="docs/images/en/explain.png" alt="Explanation of an indicator: formula, period, exclusions and lines used"></td>
<td width="25%"><img src="docs/images/en/overview-phone.png" alt="Overview on a phone"></td>
<td width="25%"><img src="docs/images/en/first-account.png" alt="Creating the first administrator account"></td>
</tr>
<tr>
<td width="50%"><img src="docs/images/en/settings-desktop.png" alt="Settings: account, two-factor sign-in on, a key for Home Assistant"></td>
<td width="50%" colspan="2"><img src="docs/images/en/mfa-setup.png" alt="Turning on two-factor sign-in with a QR code"></td>
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

**With Docker** (recommended): a ready-made image is published for x86-64 and ARM64 (including Raspberry Pi 4).

```bash
mkdir rental-cockpit && cd rental-cockpit
curl -fsSLO https://raw.githubusercontent.com/vinzgithub/rental-cockpit/main/docker-compose.yml
docker compose up -d
```

Then open `http://<machine-address>:8080` and create the administrator account. Upgrade: `docker compose pull && docker compose up -d`.

**Without Docker** (Python 3.11 or newer):

```bash
pip install .
RENTAL_COCKPIT_DATA_DIR=./data uvicorn --factory rental_cockpit.app:create_app --host 127.0.0.1 --port 8080
```

All options, upgrading and backing up the data folder: [docs/en/installation.md](docs/en/installation.md).

## Privacy and security

- Data stays in one folder (`/data`): a SQLite database and, later, the private PDFs. No telemetry, no outbound call.
- Hashed passwords (scrypt), optional two-factor sign-in (TOTP and recovery codes), signed `HttpOnly` and `SameSite=Strict` session, anti-CSRF token on every change, lock after five failed sign-ins, strict Content-Security-Policy (no external or inline script or style).
- The container runs unprivileged, with a read-only filesystem.
- Keys for Home Assistant can only read, are shown once and can be revoked at any time.
- Rights are checked on the server for every request: a reader only sees the properties granted to them, and access to PDFs is a separate permission.
- Keep the application on your local network or behind an HTTPS reverse proxy; do not expose it directly to the Internet.

See [SECURITY.md](SECURITY.md) and [docs/en/security.md](docs/en/security.md).

## Documentation

| Document | Content |
|---|---|
| [Installation](docs/en/installation.md) | Docker image, Python, variables, upgrading, backup, account recovery |
| [Getting started](docs/en/guide.md) | The first ten minutes, with the demo |
| [Calculation rules](docs/en/calculations.md) | The three readings, each indicator, glossary |
| [Architecture and adaptations](docs/en/architecture.md) | What is reused from the original project, what changes with a standalone application |
| [Security](docs/en/security.md) | Accounts, two-factor sign-in, rights, API keys, data, network exposure |
| [Home Assistant](docs/en/home-assistant.md) | Optional link: sensors, automations, card, API reference |
| [Roadmap](docs/en/roadmap.md) | Screens and work packages to come |

## Licence

**To be decided.** No licence is granted on this code yet; until a licence is published in this repository, default copyright applies.

The bundled fonts (Source Serif 4 and Inter) are distributed under the SIL Open Font License 1.1: see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Copyright © 2026 Vincent Fournet
