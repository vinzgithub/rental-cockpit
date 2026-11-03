# Architecture and adaptations

How Rental Cockpit is built, what is reused from the original private project, and what changed when Rental Cockpit became a **standalone application**. This is the reference before the Stays, Expenses, Suppliers, Documents and Settings screens are built.

## The decision

Rental Cockpit was first planned as a Home Assistant add-on. Since 31 October 2026 it is a standalone web application: **Home Assistant is not needed for installation, sign-in, storage or the interface.**

The original private project is neither modified nor read at run time: the public code is an isolated, adapted and neutralised copy (no house name, address, imposed supplier, personal amount or document).

## Overview

```
Browser ──HTTPS (optional proxy)──► Rental Cockpit application (one process)
                                    ├─ interface: HTML, CSS, JavaScript modules served by the app
                                    ├─ JSON API /api/*: session, CSRF check, rights checked on every request
                                    ├─ API /api/v1/summary: read-only, API key ◄── Home Assistant (optional)
                                    ├─ business engine (plain Python, no dependency)
                                    └─ data folder /data
                                         ├─ rental_cockpit.db   accounts, rights, keys (hashes), real registry, demo registry
                                         ├─ documents/          private PDF documents (coming)
                                         └─ .secret_key         session signing key (0600)
```

| Layer | Role | Files |
|---|---|---|
| Business engine | Cents, dates, properties, stays, entries, payments, allocated services, three readings, explained indicators, demo | `src/rental_cockpit/engine/` |
| Storage | SQLite, one transaction per change, revision number | `src/rental_cockpit/database.py` |
| Rights | Administrator, reader per property, separate PDF access | `src/rental_cockpit/access.py` |
| Security | scrypt passwords, CSRF token, sign-in throttling, TOTP codes, recovery codes, API keys | `src/rental_cockpit/security.py` |
| Web application | Routes, security headers, sessions, two-step sign-in | `src/rental_cockpit/app.py`, `web.py` |
| Account | Password, two-factor sign-in, API keys | `src/rental_cockpit/account_routes.py` |
| Home Assistant link | Read-only summary for the RESTful integration | `src/rental_cockpit/ha_api.py` |
| Stays | Stays and payouts API; nights, expected payout, payout status and month-by-month share computed on the fly with the indicators' rules | `src/rental_cockpit/stay_routes.py`, `engine/stays.py` |
| Import | Airbnb and CSV readers (read only), preview compared with the registry, writing in one transaction, undo of the last import | `src/rental_cockpit/import_routes.py`, `engine/imports/` |
| Expenses | Entries, payments and categories API; payment status, amount left and monthly series computed from the payments; CSV exports | `src/rental_cockpit/entry_routes.py`, `engine/entries.py`, `engine/exports.py` |
| Recovery | Reset a password, turn two-factor sign-in off from the server | `src/rental_cockpit/cli.py` |
| Interface | Screens, French/English texts, styles | `src/rental_cockpit/static/` |

The engine knows nothing about the web or the database: it receives a registry, applies an operation and returns a result. That is what makes each calculation rule testable on its own (`tests/test_indicators.py`, `tests/test_ledger.py`).

## Reuse of the existing base

Inventory required by the specification (REP 01): each item is **reused**, **adapted**, **removed** or **new**.

### Rules and functions from the original project

| Original item | Status | In Rental Cockpit |
|---|---|---|
| Expense and income register, operating / cash / information distinction | Adapted | Configurable categories with an explicit *treatment* (operating, investment, financing, taxes, information) |
| Profitability per activity year, net payouts never counted twice | Adapted | Three readings (Activity, Invoices, Cash); a stay's net payout is never added to revenue already recognised |
| Loan principal outside operations, interest and insurance apart | Adapted | Instalment split into principal, interest and insurance; never counted twice |
| Stay spread per night, arrival → departure window | Adapted | Night-by-night spreading exact to the cent (largest remainder) |
| PDF documents: structure check, active content refused, SHA-256, binary and business duplicates, undo of the last operation | To reuse | Documents screen |
| Cleaning supplier invoice: cleaning / linen / travel lines, split per stay equal to the total, matching manual entries | Adapted (rules) · to reuse (screen) | Generic services: any supplier, any rate; message "€10 of travel left to allocate" |
| Airbnb CSV import: checked headers, date order detected, payout lines ignored, duplicate guards | Reused (L2) | Stays → Import: preview without writing, duplicates, checks, undo of the last import; reader version stored with each import; generic CSV added |
| Invoice readers specific to some suppliers of the original project | Removed | Not published (PRE 06); a generic reader suggests fields marked "to check" |
| Functions specific to the original home: energy and equipment tracking, cameras, 3D plan, assets planning, automated assistance, multi-install bridge | Removed | Out of the public scope |
| Accounts, sessions, rights, separate demo, explanation of every indicator | New | See below |

### From Home Assistant add-on to standalone application

| Item | Before (Home Assistant add-on) | Now (standalone application) | Status |
|---|---|---|---|
| Business engine | `engine/` | `engine/`, unchanged | **Reused as is** |
| Demo | Separate registry | Separate registry; the month before the example month is ordinary fictional activity, changes are computed | Adapted |
| Interface | Home Assistant sidebar panel in a shadow DOM | Standalone page; stylesheet served by the app; own navigation (sidebar, tabs or bottom bar) | Adapted |
| Calls | Home Assistant WebSocket commands | JSON API `/api/*` over HTTP | Replaced |
| Identity | Home Assistant users | Own accounts: first administrator created on the first visit, no default account | Replaced |
| Rights | HA administrator = administrator | Administrator or reader role; granted properties and PDF access in the `grants` table | Adapted |
| Storage | JSON file in the HA configuration | One SQLite database, one transaction per change | Replaced |
| Installation | HACS and integration flow | Published Docker image (`ghcr.io`, x86-64 and ARM64) with Docker Compose, or `pip install` and `uvicorn` | Replaced |
| Home Assistant link | The add-on lived inside Home Assistant | Optional: Home Assistant reads a summary with a read-only key; it can also show the interface in a *Webpage* dashboard | New |
| Language | The HA user's | Chosen in the app (remembered by the browser), else the browser's | Adapted |
| Time zone | Home Assistant's | The process's (`TZ`), never imposed | Adapted |

The double navigation (Home Assistant sidebar + Rental Cockpit's) disappears with the standalone application.

### Optional link with Home Assistant

Home Assistant is no longer needed, but it remains a good place to **show** a few figures and **trigger** automations (heating the day before an arrival). The link is deliberately narrow:

- one route, `GET /api/v1/summary`, read-only; no writing route accepts a key;
- a key belongs to an account and reads exactly what that account can read (same properties, real data);
- the key is shown once, kept as a SHA-256 hash, revocable;
- on the Home Assistant side nothing to install: the bundled RESTful integration is enough (examples in [home-assistant.md](home-assistant.md)).

Showing the whole interface inside Home Assistant is still possible, provided its origin is explicitly allowed (`RENTAL_COCKPIT_FRAME_ANCESTORS`).

## Effects on the specification

| Requirement | Adaptation |
|---|---|
| CAD 01 | "Home Assistant integration" becomes "standalone web application". The independent web app is no longer out of scope: it is the product. |
| UX 03 | Same spirit: no configuration file to edit, no outside account, no token from another server, no outside service. |
| SEC 01 | Identity comes from the application's accounts. Every request and download is still checked on the server. |
| SEC 02, 03, 05, 06, 07 | Unchanged. |
| TEC 02 | One instance = one process (one worker), the only financial authority. |
| TEC 03 | HACS is replaced by a published Docker image (Docker Compose) and a documented Python installation. |
| TEC 04 | The start-up assistant is inside the app: first account, then *Use my data* / *Explore the demo*. |
| TEC 05 | The Docker recipe becomes the main method; listening address and port are visible in `docker-compose.yml`. |
| TEC 06 | Platforms to test: x86-64 and ARM64 (Raspberry Pi 4) images. No Home Assistant version to follow anymore. |
| T01 | Fresh Docker installation on x86-64 and ARM64. |
| T07 | Applies to the application's accounts; API tests check refusal without a session, without a CSRF token and for a guessed property. |
| SAU 01 | Backups will include accounts and rights, without the session key; whether password hashes are included is still to decide. |

## Remaining adaptations before the other screens

| Screen | Server side | Interface side |
|---|---|---|
| **Stays** | Done (L1): create, edit, cancel with a retained amount, restore, payouts. Done (L2): Airbnb import (reader reused, French export checked only) and generic CSV with column mapping and commission rate, preview without writing, check before confirmation, undo of the last import | Done: filterable list, stay page, three-step import, previous imports. Coming: allocated costs (L4) |
| **Expenses** | Done (L3): entries, partial payments, archiving, deleting an entry made by mistake, monthly series, categories, filters, CSV exports with neutralised formulas | Done: list with explicit statuses ("Payment to confirm", "Paid"…), entry page, form, categories in Settings, "Beyond operations" and "Left to settle" cards on the Overview |
| **Suppliers** | API for suppliers and indicative rates; multi-service invoice; matching existing entries | "Split an invoice": services detail, split per stay, "€150 allocated out of €150" check |
| **Documents** | HTTP upload (8 MiB), PDF check with *pypdf* (added then), fingerprint, binary and business duplicates, download after a rights check | "Check the invoice": file → check → save; "This invoice is already recorded" |
| **Settings** | Done: password, two-factor sign-in, API keys, categories (L3). Coming: reader accounts, rights per property and PDF access, backup / check / restore, diagnostics | Matching screens; language; demo reset |
| Cross-cutting | Versioned data format migrations, with an automatic copy of the database before converting (first one: v1 → v2, booking channel); `edge` image published on every change to the main branch, `latest` on every tagged release; continuous integration | Accessibility checked (keyboard, screen reader, 360 px) on each screen |

## Still open

- Project licence.
- Exact content of backups (accounts, password hashes, two-factor secrets, API keys).
