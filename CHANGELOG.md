# Changelog

## 0.3.0 — not released yet

Import (delivery L2): stays come from an Airbnb export or any CSV file, checked line by line before anything is saved.

- "Import" button on the Stays screen, and "A bookings file" in the Add menu (so on a phone too). Administrators only.
- Three-step wizard: file (Airbnb export or other CSV, chosen or dropped), check, result.
- Airbnb reader for the French "Historique des transactions" export: required columns checked, day/month order taken from the unambiguous dates (a file mixing both is refused), "Payout" transfer lines and other line types ignored and counted, one confirmation code on several lines merged, conflicting lines and nights that do not match the dates refused.
- Generic CSV: UTF-8 or Windows-1252, comma, semicolon or tab, decimal comma; each column suggested from its name and shown with an example value; arrival plus departure or number of nights; date order automatic or chosen; platform of the stays; commission rate when the file has no commission (rounded to the cent). The choices are remembered for files with the same columns.
- Each listing of the file is attached to a property; the choice is remembered.
- Preview with nothing written: new stay, update of a stay already imported (field by field), probable duplicate of a stay entered by hand (completed with what it does not know, or a new stay, or skipped), reference already on another property, up to date, no property, error. Overlaps with existing stays, inside the file and with unavailable dates, arrivals before the activity start, negative amounts, dates outside 2000–2100 and payouts above what is expected are flagged.
- Payouts dated in the file are recorded once, never above the expected amount; a cancelled stay is never changed by an import.
- Guests' names are not kept unless asked.
- The confirmation is refused if the stays changed since the preview; the new preview is shown.
- The last import can be undone (here or in "Previous imports") as long as its stays were not changed; updated and completed stays get their previous values back.
- The stay page says which file created it.
- Large files: 5 MiB and 20,000 lines at most; a file of that size is checked in under a second and written in one go, with one journal line for the whole file.
- New automated tests: readers, preview, apply, re-import, duplicates, undo, API (rights, CSRF, demo separation, limits) and three browser journeys.

## 0.2.0 — not released yet

Stays (delivery L1): real fictional stays can be entered and show up correctly in the Overview.

- Stays screen: list with views (upcoming and current, past, to check, cancelled, all), property filter and search; table on a computer, cards on a phone.
- Stay form: property, dates with the nights per month shown live, guests, label, booking reference, channel (Airbnb, Abritel, Booking.com, direct, other), status, gross amount, commission, net payout (computed when empty), tourist tax and security deposit (never revenue).
- Stay page: amounts, received and left to receive, month-by-month share in the Overview (same rule as the indicators), payouts, history; edit, cancel with the retained amount, restore, delete an entry made by mistake.
- Payouts: record and delete; a payout cannot exceed what is still expected.
- The Overview links to the stays: upcoming stays open their page, "payout to confirm" opens the list to check, "How is this amount calculated?" lines lead to their stay.
- Data format 2 (booking channel). Before converting, the database is copied to `backups/`; the migration is tested on a frozen schema-1 registry.
- A change made on an outdated copy of a stay is refused (revision number) instead of overwriting.
- New automated tests: rules, migration, API (rights, CSRF, double click, outdated copy) and a browser journey with the figures of the pull request.

## 0.1.1 — not released yet

Fixes from the independent audit of 0.1.0.

- The menu only lists screens that work (Overview and Settings); Stays, Expenses, Suppliers and Documents return as they are delivered. No "coming soon" page anymore.
- "My data / Demo" switch always visible: in the sidebar, in the account window and in Settings, where an administrator can also reset the demo.
- The bell opens the list of things to check.
- No more links to screens that do not exist yet (Import button, things to check, next stay).
- "How is this amount calculated?" fits a phone: each line becomes a small card, nothing scrolls sideways.
- Copy buttons work on plain HTTP (local network address), with a selection for Ctrl+C as a last resort.
- Every pull request publishes a test image `ghcr.io/vinzgithub/rental-cockpit:pr-<number>`.
- Browser tests (Chromium) run on every change.

## 0.1.0 — 2026-10-31 (preview)

First public preview of the standalone application.

- Standalone web application: own accounts (first administrator created on first visit), signed sessions, CSRF protection, sign-in throttling, strict Content-Security-Policy, SQLite storage in one data folder.
- Business engine: properties, stays, entries, payments, service lines and allocations, exact cents, three readings (Activity, Invoices, Cash), explained indicators, things to check.
- Fictional demo in a separate registry; its example month reproduces the documented example (€1,000 − €200 = €800).
- Overview screen for computer, tablet and phone; welcome screen with two explicit choices; creation of a property.
- Optional two-factor sign-in: authenticator app (TOTP) with a server-generated QR code, ten single-use recovery codes, three-step guided setup; turning it on or off signs out the other browsers.
- Settings screen, account part: password change, two-factor sign-in, API keys.
- Optional Home Assistant link: read-only API keys (shown once, stored as hashes, revocable) and `GET /api/v1/summary` for the RESTful integration; documented sensors, automations and card; framing allowed only for the origins in `RENTAL_COCKPIT_FRAME_ANCESTORS`.
- Account recovery from the server: `python -m rental_cockpit.cli reset-password|disable-mfa <username>`.
- Docker images for x86-64 and ARM64 published on `ghcr.io/vinzgithub/rental-cockpit` (`edge` from the main branch, `latest` and version tags from releases), each one started and checked before publication; unprivileged, read-only container.
- Sign-in on a phone: the form comes right after the name, above the presentation.
- Python installation; French and English interface and documentation.
