# Changelog

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
- Python installation; French and English interface and documentation.
