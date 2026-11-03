# Changelog

## 1.0.0 — not released yet

Version 1.0 (delivery L6): reader accounts, checked backup and restore, an accessibility and performance pass, and the acceptance of every release criterion.

- Settings → Accounts and access (administrators): add a reader with a temporary password generated in the browser, open properties to them one by one and, separately, the PDF documents of each property; change their access, give a new temporary password (their sessions end), delete the account. The administrator account cannot be changed from there.
- A temporary password opens nothing but "Choose your password": the server refuses everything else until it is replaced.
- Settings → Backup and restore: a ZIP backup of "My data" — registry, PDF originals, readers' rights by name and a manifest with the fingerprint of every file, the counts and the totals — never a password, two-factor secret or API key. It is written in `backups/`, read back and checked, then downloaded; the server keeps a list to download again or delete.
- Restore: the backup is unpacked and checked in a staging folder (file names, unpacked size, fingerprints, PDFs, schema, totals) and compared with the current data. It is applied only after typing REMPLACER / REPLACE; the data it replaces are first saved in `avant-restauration-….zip`; the result says whether the totals are the same. Readers' rights come back for the accounts that exist here.
- Command line: `python -m rental_cockpit.cli backup` and `restore <file>`; with Docker, `restore -` reads the backup on standard input, checks it, and replaces the data only when run again with `--yes`. The documented procedure after an update that went wrong is run for real by the tests and, in the Docker image, by CI.
- Accessibility: secondary text contrast raised to 4.5:1 at least, a main landmark on the sign-in screen, the illustration marked decorative, a "Skip to content" link, keyboard focus kept inside a dialog that is redrawn; every screen and the main dialogs pass axe-core on a computer and at 360 pixels, checked in CI.
- Performance: the Overview no longer scans every payment for each expense (22 s → 0.2 s with 10,000 entries and 2,000 stays) and the stays list adds up the payouts once (1.4 s → 0.06 s); a regression test keeps it so.
- Layout: no horizontal scrolling on any screen from 360 to 1,440 pixels wide (checked by a test at nine widths); the stays table appears from 1,080 pixels, cards below; the expense filters keep their full labels.
- Incidents: a full disk while storing a PDF is refused with an explanation and nothing recorded; full disk, interruption and expired tokens are covered by tests.
- Docker: the CI smoke test also runs a command-line backup in the read-only, unprivileged container, then the documented restore with the application stopped, and starts the ARM64 image under emulation.
- Documentation: backup and restore guide, acceptance matrix T01–T12 with performance measurements, guide chapters on readers and backups, screenshots with the full menu.

Corrections from the first acceptance report (delivery L7, same version):

- Airbnb import (ANO-001): every "Payout" line is checked to the cent against the lines it pays, and gives the date sent and the latest date it reaches the account. "Versement de résolution" (AirCover damage refunds included) becomes an income "Compensation (damage, resolution)" with no night; "Crédit divers" an income "Platform bonus or credit"; a negative resolution adjustment an expense "Refund to a guest" withheld from the payout. A type the reader does not know is shown with its amount and recorded only when chosen. A payouts check sums the file's payouts by kind and month and says which sums would not be recorded. Importing again adds nothing; undoing the import removes these operations.
- Bookings cancelled but compensated (ANO-002): a third choice, "Cancelled, amount received kept", records the stay as cancelled with its amounts and payout: the money counts once, the nights do not. Both lines of an overlap offer it.
- Overview in three views (ERGO-001, ERGO-002): "My money" by default (money in, money out, balance, left to pay and to receive; platform payouts counted on the day they are sent, the bank date shown when known), "Rental performance" (revenue from nights, commissions, rental result, nights, occupancy, other income and expenses, the twelve months of the year) and "Accounting analysis" (the three readings, renamed per night occupied, by stay or invoice date, by payment date). The calculation engine is unchanged.
- Period picker (ERGO-003): "◀ October 2026 ▶", a grid of the twelve months with the year's arrows, this month, the whole year and a free period; keyboard and touch. The Expenses screen uses it too, with "All dates", and filters by year or month.
- "How is this amount calculated?" on phones (ERGO-004): the whole screen, the calculation as a short list, lines as cards up to 720 pixels, one scroll only, a compact head when held sideways; the "?" of each amount stays on phones.
- Copy on plain HTTP (ERGO-005): a note next to each secret says the browser may refuse the automatic copy, one tap selects the secret whole, HTTPS is advised; a failed copy is said in the window. The temporary password of a reader uses the same copy.
- Links and alerts (ERGO-006): a test checks that no button leads to a missing screen and that each alert opens its list.
- New built-in categories: Compensation (damage, resolution), Platform bonus or credit, Refund to a guest. Payments keep the date a platform payout reaches the bank when the export gives it.

## 0.6.0 — not released yet

PDF documents (delivery L5): invoices are kept as private PDFs, checked without being run, recognised when they come back, and attached to the expenses they justify — or used to create them.

- New "Documents" screen in the menu: every PDF with its supplier, number, date, amount and the expenses it justifies; views All and To complete (attached to nothing, or without a supplier or an amount); search.
- "Create an expense from an invoice" (Documents screen, Expenses screen, Add menu): the PDF is checked, its text read, and the date, amount including tax, invoice number and a known supplier are proposed, each marked "To check"; what is not found stays empty and a scan is typed by hand. The expense and its document are saved together, after confirmation only.
- "Add a document to this expense" on an expense's page: the expense is not changed. The same PDF can justify several expenses of a property, stored once.
- Document page: what the invoice says (editable), the expenses it justifies, attach to another expense of the property, detach, open, download (the original bytes), delete when attached to nothing.
- Checks: a real PDF structure, 8 MiB and 200 pages at most, no password needed, no script, launch action, form submission or embedded file; nothing is ever run; a check that takes too long is refused. The checked file waits 10 minutes in memory for its sender; nothing is written before the confirmation.
- Duplicates on every property: same file (SHA-256, even renamed) or same supplier and invoice number is a certain duplicate, refused with a link to the existing expense; same supplier, date and amount without a number is a probable one, saved after an explicit confirmation; an amount alone never counts.
- Private storage: one file per fingerprint, folder 0700 and files 0600, checked against its fingerprint before each sending; a newly written file is removed if the save fails, and leftovers are cleaned at start-up.
- Rights: access to a property's PDFs is granted separately from access to the property; a reader without it only sees that a document exists. Changes are for administrators.
- An incomplete document is listed in "To check" and leads to the To complete view.
- Demo: the documented invoice F-DEMO-018 comes with a fictional PDF.
- New dependency: pypdf (BSD-3-Clause), to check and read PDFs.
- New automated tests: refused files (script, embedded file, password, truncated, renamed text file, too many pages, too large), reading assistance, duplicate rules, create, double click, attach, link, detach, delete, metadata, rights of readers with and without PDF access, damaged or missing original, start-up cleanup, demo PDF, and the browser journey.

## 0.5.0 — not released yet

Suppliers (delivery L4): a supplier's invoice can be broken down into services, split between the stays it served and reconciled with the entries typed by hand, without ever being counted twice.

- New "Suppliers" screen in the menu: active and archived suppliers, search by name, activity or category; each card shows the invoices of the year, what is left to pay, payments to confirm and what is left to split.
- Supplier form: name, activity, usual categories (offered first for their invoices), indicative rates (kind of service, unit, unit price, label), contact, note; archive and restore.
- Supplier page: invoices of the year, left to pay, left to split, rates, recent invoices, "See them in Expenses" (the Expenses screen filtered on the supplier), "New invoice".
- Detailed invoice: "Break the invoice down into services" in the expense form — cleaning, linen, travel, other, discount, tax, adjustment; quantity × unit price or amount; date of the work. The total is checked live and again by the server; an adjustment needs a reason; a supplier's rate pre-fills the unit price, never an amount. The invoice stays one expense.
- "Split between stays": each service given to one or several stays of the same property; the stay whose departure falls on the day of the work is offered first. Analysis only: no expense is added. A service already split cannot be removed from the invoice before its split is changed. An invoice split only in part is listed in "To check" with the amount left.
- "Reconcile entries typed by hand" (offered on invoices: broken down or with an invoice number): the invoice replaces the expenses typed by hand for the same services (same property and kind, invoice period). They leave every total, their payments move to the invoice on their original dates, and each reconciliation can be undone. Everything is checked before anything is written; the total replaced never exceeds the invoice.
- Stay page: "Costs allocated to this stay" (shares of split invoices and expenses attached to the whole stay) and "Margin after costs".
- Service lines keep unique identifiers, and editing an invoice keeps its lines intact.
- Rows of the dialogs no longer widen a dialog on a phone; hover outlines only on devices with a mouse.
- New automated tests: detailed invoice, split, suggested stay, reconciliation and its limits, supplier totals, API rights, and the browser journey with the figures of the documentation; the two-factor test no longer depends on crossing a 30-second step.

## 0.4.0 — not released yet

Expenses and payments (delivery L3): expenses and income outside stays can be entered, settled in one or several payments, and show up in the three readings. Day-to-day use with your own data is now possible.

- New "Expenses" screen in the menu: views All, To pay, Payment to confirm, To receive, Archived; filters by property, type, year and text; totals of the list shown (expenses, left to pay, income, left to receive, instalments to come); table on a computer, cards on a phone.
- Entry form: category with its treatment explained (operating, investment, financing, taxes, information only), amount, date, payment (already paid with its date, to pay, or not known yet), supplier when there are suppliers, invoice number, related stay, period covered (spread day by day in the Activity reading), note.
- Loan instalments: principal / interest / insurance breakdown, checked live against the instalment; outside the operating balance, in "Balance after financing".
- "Repeat every month" (2 to 36 months) for loan instalments and subscriptions: one entry per month, each one settled on its own; "already paid" only settles the dates already past. Instalments dated after today are "planned": grouped under "Coming up", out of "To pay" until their date.
- Entry page: amounts, already paid, left to pay, what the entry counts in each reading, payments (record a partial or full payment, delete one), "Not paid yet" / "I don't know", archive (out of every total, kept for reference), delete an entry made by mistake (refused when it has a payment or a document).
- A payment never exceeds what is left; the amount of an entry cannot go below what was already paid.
- Income outside stays (refund, occasional rental…) counts in revenue and in "To receive" until received.
- Overview: new "Beyond operations" card (investments, taxes, loan repayments with their breakdown, balance after financing) and "Left to settle" card (to pay, to receive, with the list behind each); "Payments to confirm" opens the matching expenses; "How is this amount calculated?" opens the entry of a line.
- Settings: categories of expenses and income — create, rename (an empty name goes back to the original), archive.
- CSV exports of the expenses and of the stays, with the filters shown on screen: semicolons and decimal commas in French, a text that a spreadsheet would run as a formula is neutralised. Readers export only the properties they were granted.
- Switching between "My data" and "Demo" reloads the list shown.
- New automated tests: payment status, partial payments, series, coverage period, archive, delete, categories, exports, API rights and the browser journey with the figures of the pull request.

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
