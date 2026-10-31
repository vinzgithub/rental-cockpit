# Roadmap

Rental Cockpit moves forward in short work packages. Each screen is shown as screenshots for approval of its look before it is rolled out.

| Package | Content | Status |
|---|---|---|
| **1. Foundations** | Inventory of the original project, isolated and tested calculation engine, separate fictional demo | ✅ Done |
| **1b. Standalone application** | Accounts, sessions, rights, SQLite storage, Docker, Overview and welcome screens | ✅ Done — preview 0.1.0 |
| **2. Recording** | Stays, Expenses and payments, Suppliers with invoice splitting | Coming |
| **3. Documents and imports** | PDF documents (checks, duplicates, protected download), reused Airbnb import, generic CSV import with preview | Coming |
| **4. Settings and backup** | Readers and rights per property, two-factor authentication, categories, checked backup and restore, diagnostics | Coming |
| **5. Public release** | x86-64 and ARM64 Docker image, beginner tests, full repository audit, criteria T01 to T12 | Coming |

Abritel (and other platforms) will only be announced after analysing genuine, anonymised exports: no format is guessed.

## Pending decisions

- Licence.
- Published Docker image or local build only.
- Optional link with Home Assistant (read-only), never required.
