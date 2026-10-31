# Security and data protection

## Accounts and sessions

- **No default account.** The first visit creates the administrator; the creation page is refused afterwards.
- **Passwords**: at least 10 characters, hashed with scrypt (N = 2¹⁴, r = 8, p = 1). An unknown user name takes as long as a wrong password.
- **Throttling**: after five failures from one address, attempts are refused for five minutes. The message never says whether the user name exists.
- **Session**: signed cookie, `HttpOnly`, `SameSite=Strict`, `Secure` when `RENTAL_COCKPIT_COOKIE_SECURE=true`. The signing key is created on first start in the data folder (mode 0600). Each account carries a session version number: changing the password (Settings screen) will increment it to sign out the other browsers.
- **Two-factor authentication**: TOTP codes (RFC 6238), each code accepted once. Sign-in already handles it; turning it on comes with the Settings screen.

## Rights

| Profile | Can |
|---|---|
| Administrator | Configure, record, import, correct, back up and restore |
| Reader | View only the granted properties; open PDFs only when explicitly granted |
| Not signed in | Nothing but the sign-in page |

Rights are checked **on the server** for every request. Hiding a button is never a protection. Totals only cover permitted properties: a hidden property appears in no list and no sum. A guessed property identifier is refused.

The demo (fictional data) can be viewed by any signed-in account and changed by administrators only.

## Requests

- **Anti-CSRF token** required on every change.
- **Idempotent operations**: each action carries a unique identifier; a double click or a network retry is saved once.
- **All or nothing**: a change is applied to a copy, written in one SQLite transaction, then published. On failure the previous state is kept and the message says so.
- **Text**: everything typed or imported is handled as text, never as HTML.

## Browser

- Strict Content-Security-Policy: `default-src 'self'`, no inline or external script or style, no framing (`frame-ancestors 'none'`).
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, restrictive `Permissions-Policy`, API responses never cached.
- Fonts and icons are served by the application: no request to any other site.

## Data

- **Local storage only**: no telemetry, no vendor account, no outbound call.
- All data is in the `/data` folder: protect it and its backups, which hold private information.
- Guest data is kept to the minimum useful (a label and a number of guests).
- The operations log records author, date, action, item and result; it holds no secret and no PDF content. It is not a certified legal archive.

## Network exposure

- Use Rental Cockpit on your local network or through a VPN.
- If outside access is unavoidable: HTTPS reverse proxy, `RENTAL_COCKPIT_COOKIE_SECURE=true`, `FORWARDED_ALLOW_IPS` set to the proxy's address, and two-factor authentication as soon as it is available.
- The base installation opens no port on your router.

## Reporting a vulnerability

See [SECURITY.md](../../SECURITY.md): private reporting, never in a public issue.
