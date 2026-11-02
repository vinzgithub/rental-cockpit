# Acceptance of version 1.0

Each blocking criterion of the specification (§ 11), with what checks it. The automated tests run on every change, on Python 3.11, 3.12 and 3.13, plus a real Chromium for the journeys (`tests/e2e`). All data are fictional.

| Criterion | Expected result | Automated check | Manual check |
|---|---|---|---|
| **T01** Fresh install | Documented install on x86-64 and ARM64, with no private data copied | Docker image built for `linux/amd64` and `linux/arm64` on each PR; read-only, unprivileged container started, `/healthz` and command-line backup checked; ARM64 image run under emulation | Install on an x86-64 machine (test instances of the PRs); **Raspberry Pi 4 (ARM64) trial to be done during acceptance** |
| **T02** Neutrality | No personal data or real amount in the repository, its archives and its demo | `scripts/check_public_data.py` (CI); generated demo (`tests/test_demo.py`) | Review of the screenshots (all from the demo or fictional data) |
| **T03** Calculations | €1,000 → €800 before financing, €600 cash | `test_documented_example_T03` | Example month of the demo |
| **T04** Full PDF | Preview, create, view and download a PDF with identical bytes | `test_create_an_expense_from_an_invoice`, `test_invoice_to_expense_duplicate_attach_and_detach` (download compared byte for byte) | Scenario of the L5 PR |
| **T05** Duplicates | Renamed re-import, other equivalent binary, double click, two parallel confirmations: no double charge | `test_create_an_expense_from_an_invoice` (same file renamed, same reference, probable case, double click, second confirmation refused); `test_same_file_again_changes_nothing`, `test_property_creation_double_click_creates_one` | Scenario of the L5 PR (steps 2 and 5) |
| **T06** Separate actions | Attaching or detaching a PDF creates or removes no expense; reconciliation without double counting | `test_attach_and_detach_never_change_the_expense`, `test_reconciliation_replaces_entries_typed_by_hand`, `test_supplier_invoice_split_and_reconciled` | Scenarios of the L4 and L5 PRs |
| **T07** Rights | Commands, PDFs and exports refused to a forbidden user, including for a guessed identifier | `test_rights_on_documents`, `test_reader_account_from_creation_to_deletion`, `test_api_supplier_edit_archive_and_rights`, `test_unknown_property_is_refused_not_leaked`, `test_changes_without_csrf_token_are_refused` | Reader account created from Settings |
| **T08** Imports | Valid CSV accepted, ambiguous lines explained, idempotent re-import, unknown format refused | `tests/test_imports.py` (42 tests), including `test_same_file_again_changes_nothing`, `test_airbnb_reader_refuses_another_export`, `test_api_rejects_unreadable_and_oversized_files` | Scenario of the L2 PR |
| **T09** Services | Cleaning, linen, travel; invoice over several stays; split sums equal to the total | `tests/test_suppliers.py`, `test_supplier_invoice_split_and_reconciled` | Scenario of the L4 PR |
| **T10** Incidents | Storage failure, disk full, interruption, expired token: consistent state and useful message | `tests/test_incidents.py` (disk full when saving and for a PDF, interruption after the file is written, expired preview and restore, stale CSRF token) | — |
| **T11** Backup | Full restore on another installation, documents readable and same totals | `test_backup_restored_on_another_installation`, `test_command_line_backup_and_restore_after_a_failed_update`, `test_damaged_or_foreign_backups_are_refused` | Backup downloaded then restored on another test instance ([backup.md](backup.md)) |
| **T12** Usability | Keyboard, screen reader, mobile and beginners' journeys checked | `tests/e2e/test_accessibility.py` (axe-core on every screen and the main dialogs, computer and 360 px, "Skip to content" link), "fits a phone" checks of each journey | **Beginners' journeys by at least five outside people** (create a property, enter an expense, find its PDF, explain an indicator): to be organised |

## Quality

**QUA 01** — The interface only calls routes that exist: `test_interface_calls_only_existing_routes`. Every change route requires a session, the CSRF token and the administrator role. Their contract tests are in the test files of each delivery.

**QUA 02** — Measured in a Linux x86-64 container (Python 3.13, SQLite), with 10,000 entries, 2,000 stays, 3,334 payments and 4 fictional properties (`tests/test_performance.py` keeps a smaller version of this data set):

| Operation | Time |
|---|---|
| Overview of a month, a year or six years (each reading) | 0.13 to 0.23 s |
| Expenses list (all) | 0.16 s |
| Stays list (all) | 0.06 s |
| Preview of an 18,000-line CSV import | 0.3 s (writing: 1.5 s) |
| Full backup | 0.6 s |

Targets of the specification: Overview under 2 s, preview of a 5,000-line CSV under 10 s. No calculation needs the Internet.

## Known limits of 1.0

- No OCR: a scanned PDF is described by hand.
- A document belongs to one property; explicitly splitting an invoice between properties will come later.
- Abritel and other platforms will only be added from genuine, anonymised exports.
- Backups are started by hand (Settings or command line): no scheduled backup yet.
