# Security

🇫🇷 Les signalements en français sont bienvenus.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting instead:
**Security → Report a vulnerability** on this repository.

Never attach a real database, a real invoice, a password, an API key or a session cookie to a report: describe the problem with fictional data.

## Supported versions

Rental Cockpit is in preview (0.x). Only the latest version receives fixes.

## Design

The full description is in [docs/en/security.md](docs/en/security.md) ([français](docs/fr/securite.md)). In short:

- no default account; the first visit creates the administrator;
- passwords hashed with scrypt; sign-in throttled after five failures; optional TOTP two-factor sign-in with single-use recovery codes;
- read-only API keys for Home Assistant, shown once and stored as hashes;
- signed `HttpOnly`, `SameSite=Strict` session cookie; CSRF token on every change;
- rights checked on the server for every request; readers only see granted properties; PDF access is a separate permission;
- strict Content-Security-Policy, no external resource, no telemetry, no outbound call;
- all data in one folder (`/data`), written in SQLite transactions.

Keep Rental Cockpit on your local network or behind an HTTPS reverse proxy. Do not expose it directly to the Internet.
