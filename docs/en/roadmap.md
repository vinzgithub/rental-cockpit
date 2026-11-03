# Roadmap

Rental Cockpit moves forward in short, usable **deliveries**. Each delivery is a pull request that can be tested on its own, with its test Docker image (`ghcr.io/vinzgithub/rental-cockpit:pr-<number>`), a scenario with figures and automated tests. It is only merged once the testers have approved it.

| Delivery | Version | Content | Status |
|---|---|---|---|
| Foundations | 0.1.0 | Standalone application: accounts, rights, two-factor sign-in, Overview and three readings, separate demo, Home Assistant link, Docker images | ✅ Released |
| **L0** — audit fixes | 0.1.1 | Menu without empty screens, My data / Demo switch, bell, explanations readable on a phone, copy over HTTP, browser tests | Under review |
| **L1** — Stays | 0.2.0 | Create, edit, cancel, restore and delete stays; booking channel; payouts received; stay page with its share of the Overview; data format migration with an automatic copy | Under review |
| **L2** — Import | 0.3.0 | Airbnb import (reader reused and adapted) and generic CSV: preview without writing, duplicates detected, commissions (rate for a CSV), checks before confirmation, all-at-once validation, undo of the last import | Under review |
| **L3** — Expenses and payments | 0.4.0 | Expenses and income outside stays, partial payments, to pay / to receive, loan instalments (monthly series, principal / interest / insurance), period covered, categories, CSV exports, "beyond operations" Overview | Under review |
| **L4** — Suppliers | 0.5.0 | Suppliers and indicative rates, invoice broken down into services, split between stays (stay offered from the date of the work), undoable reconciliation with the entries typed by hand, costs and margin per stay | Under review |
| **L5** — Documents | 0.6.0 | PDFs checked without running anything, preview with nothing written, reading assistance marked "To check", duplicates (file, reference, probable case), create an expense from an invoice, attach and detach without touching the expense, private storage by fingerprint, viewing after a rights check | Under review |
| **L6** — Version 1.0 | 1.0.0 | Checked backup and restore, reader accounts, accessibility and mobile pass, ARM64 test, full acceptance run | Coming |

Day-to-day use (priority P0) is reached with 0.4.0. Abritel (and other platforms) will only be announced after analysing genuine, anonymised exports: no format is guessed.

## Pending decisions

- Licence.
