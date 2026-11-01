# Calculation rules

Rental Cockpit is a **management tracking** tool. Its results are not a tax return, a certified statement or legal advice.

## Principles

- **Exact amounts.** Everything is stored in whole cents. When an amount is spread (per night, per day), it is split once for the whole stay or covered period using the largest remainder method: the shares of two consecutive months always add back to the total, to the cent.
- **Euros only** in this version. Another currency is refused rather than converted.
- **Periods include the start and exclude the end.** A stay from 10 to 12 June is two nights; the 12th is the departure day.
- **Unknown is not zero.** A stay without an amount is not counted as €0: the indicator is marked *incomplete* and the stay is listed in *To check*.
- **Nothing is assumed paid.** A due date, a "paid in cash" mention or a PDF is not a payment. Only a recorded payment (date and amount) counts as cash.
- **An invoice stays one expense.** Splitting it between stays explains what it was for; it creates no extra charge.
- **Corrections keep their history**: previous value, author and date.

## The three readings

| Reading | Question | Stay | Expense | Payment |
|---|---|---|---|---|
| **Activity** | What did the rental produce during the period? | Revenue and commission spread night by night | On its date, or day by day over its covered period (e.g. an annual insurance) | Ignored |
| **Invoices** | Which documents are dated in the period? | On the arrival date | On the invoice date | Ignored |
| **Cash** | What money actually moved? | Money received, on its date | Payments made, on their date | Counted |

The chosen reading is always shown. Figures from two readings are never added together.

Special cases:

- **Cancelled stay**: no nights; any retained amount counts once, on the arrival date.
- **Adjustment or refund**: counted on its own date, without erasing the original amount.
- **Platform commission**: operating expense in Activity and Invoices. In Cash it is not a payment, since it is already deducted from the payout received.

## A stay, from entry to the Overview

A stay is entered in the **Stays** screen: property, arrival, departure and, when known, the gross amount paid by the guest and the platform commission. The **expected net payout** is gross − commission, unless another amount is entered (the platform paid something else). The tourist tax collected and the security deposit are recorded apart: **they are never revenue**.

Example (it is the test scenario): a stay from 28 September to 4 October 2026, €600 gross, €90 commission.

| | September 2026 | October 2026 |
|---|---|---|
| Nights | 3 | 3 |
| **Activity** — revenue / commission / balance | €300 / €45 / €255 | €300 / €45 / €255 |
| **Invoices** — revenue / commission / balance | €600 / €90 / €510 (arrival month) | €0 |
| **Cash** — before the payout | €0 | €0 |
| **Cash** — after "payout received: €510 on 5 October" | €0 | €510 received |

The stay page shows this split, month by month, with the same rule as the Overview.

**Payout status** of a stay:

| Status | When |
|---|---|
| Payout expected | The stay has not ended, nothing received yet |
| Payout to confirm | The stay has ended and no payout is recorded (it appears in *To check*) |
| Partly received | Part of the expected payout is recorded |
| Payout received | The expected payout is fully recorded |
| Amount to complete | The gross amount is unknown: nothing can be checked |
| Nothing to receive | Cancelled stay with no retained amount |

A payout cannot exceed what is still expected: if the platform paid more, correct the stay amounts first.

**Cancelling a stay** asks for any amount retained (cancellation fee) and the commission on it. The stay stays visible, with no night; only the retained amount counts, once, on the arrival date. The amounts from before the cancellation are kept: **Restore the stay** brings them back. Deleting a stay is reserved for an entry made by mistake, with no payout.

## An imported stay

An imported stay follows exactly the same rules as a stay entered by hand: the import only fills the same fields.

**Airbnb export** (French "Historique des transactions"):

| Airbnb column | Stay field |
|---|---|
| Code de confirmation | Reference |
| Date de début / Date de fin | Arrival / departure (the file's number of nights must match) |
| Revenus bruts | Gross amount (otherwise: Montant + Frais de service) |
| Frais de service | Commission |
| Montant | Net payout |
| Taxes reversées par Airbnb | Tourist tax collected (never revenue) |
| Date | Payout date, when it is already past |

- **"Payout"** lines are transfers of amounts already on the booking lines: they are **never counted a second time**. Other line types (adjustments, resolutions…) are not bookings: they are counted in the preview, not imported.
- One code on several lines makes one stay, whose amounts add up. If those lines disagree on the dates or the listing, the stay is refused rather than guessed.
- The day/month order comes from the unambiguous dates (Airbnb writes MM/DD/YYYY); a file mixing both is refused.
- When gross − service fee ≠ amount paid out, a remark says so.

**CSV**: each column is chosen in the preview. Amounts in French or English format ("1 234,50", "1,234.50"). Without a commission column, a **rate** can be given: commission = gross × rate, rounded to the nearest cent (half a cent up). Example: 15% of €333.33 = €50.00; 3.5% of €333.33 = €11.67.

**Payouts in the file**: recorded in the Cash reading on their date, once (same date and amount already recorded = skipped), never above the expected payout, and only when their date is past.

**Stay entered by hand on the same dates** (probable duplicate): completing it only fills what it did not know. When the file states another gross amount or commission, the ones typed are kept and a remark says so; the file's net payout is then not taken either, so it does not contradict the amounts kept.

## An expense or income outside stays

An entry has an amount including tax, a date (the invoice date) and a **category**. The category's **treatment** says where it counts:

| Treatment | Counted in | Examples |
|---|---|---|
| Operations | Expenses (or Revenue) and balance before financing | Cleaning, linen, repair, energy, property insurance, subscription, platform fees |
| Investment | Investments, apart | Equipment, improvement works |
| Financing | Loan repayments, outside the operating balance | Instalment: principal + interest + borrower insurance |
| Taxes | Taxes, apart | Property tax |
| Information only | No total | Expense kept for reference |

**The three readings.** In *Activity*, the entry counts on its date, or day by day over its **period covered** when it has one (an annual insurance of €240 from 1 November 2026 to 1 November 2027 counts €19.80 in November: 30 days of €0.66, the remaining cents going to the largest remainders). In *Invoices*, it counts on its date. In *Cash*, only its **payments** count, on their date and for their amount.

**Payment status.** The status always comes from the payments recorded:

| Status | When |
|---|---|
| Paid (Received) | The payments cover the whole amount |
| Partly paid (received) | Part of it is settled |
| To pay (To receive) | Nothing is settled and the entry is known to be due |
| Payment to confirm | Nothing is settled and nobody said whether it is: listed in *To check* |

A payment never exceeds what is left, and the amount of an entry cannot go below what was already settled.

Example (it is the test scenario): a €300 repair dated 10 October 2026, to pay, then a €100 payment on 12 October. In October: *Activity* and *Invoices* count €300 of expenses; *Cash* counts €100; €200 is left to pay.

**Instalments.** A monthly series creates one entry per month, on the same day (the 31st becomes the last day of a shorter month). Each instalment is settled on its own. An instalment dated after today is *planned*: it is not yet in "To pay" on the Expenses screen. When principal, interest and insurance are given, they must add up to the instalment; the Overview details them under **Loan repayments**. Example: €500 = €350 principal + €120 interest + €30 insurance; in October, the balance before financing is unchanged, the balance after financing is €500 lower.

**Archiving** removes an entry from every total without erasing it; its payments are kept. **Deleting** is only possible for an entry with no payment and no document.

## A supplier's invoice

**Services.** An invoice can be broken down into lines: cleaning, linen, travel, other, discount, tax, adjustment. A line has an amount, or a quantity and a unit price (amount = quantity × price, which must come out exactly to the cent: nothing is quietly rounded). A discount is negative; an adjustment may be, and needs a reason. **The lines must add up to the invoice amount**, otherwise nothing is saved. A supplier's rates pre-fill a unit price, they never change an amount. The invoice stays **one single expense**: it is what counts in the three readings.

**Split between stays.** Each service (cleaning, linen, travel, other) can be given, in one or several parts, to stays of the same property (only stays that are not cancelled are offered); a discount, a tax or an adjustment follows the invoice. What is given out for a service never exceeds its amount. The stay offered is the one whose departure falls on the day of the work, otherwise the one under way that day. The split **adds no expense**: it says which stays an expense served. A service already split can only be removed from the invoice once its split has been changed. An invoice split only in part is listed in *To check* with the amount left.

**Reconciliation.** An invoice can replace expenses typed by hand for the same services. Offered: the expenses of the same property, in the category of the invoice or of its services, dated between the first day of work (otherwise one month before the invoice month) and the invoice date, with no supplier or the same one. Always refused: an expense of another property, income, an expense that is archived, broken down, already replaced or replacing others. The total replaced does not exceed the invoice amount. The entries replaced leave every total; their payments **move to the invoice** (on their original date, so the Cash reading does not change) and cannot exceed its amount. A reconciliation is undone entry by entry: it comes back with its payments. An invoice that replaces entries can be neither deleted nor archived until those reconciliations are undone, and its amount cannot go below the total replaced.

**A stay's costs and margin.** The costs allocated to a stay are its shares of split invoices, plus the expenses attached to the whole stay (with no split). **Margin after costs = expected net payout − allocated costs**; it is not computed for a cancelled stay or one whose amount is unknown.

Example (it is the test scenario): stay A from 28 September to 4 October 2026 (€600, commission €90, expected payout €510) and stay B from 10 to 13 October (€300, commission €45, expected payout €255). Two cleanings typed by hand and paid: €45 on 4 October, €35 on 13 October. The supplier then sends their invoice of 20 October: **€150** = 4 h of cleaning at €25 on 4 October + 4 sets of linen at €10 on 13 October + €10 of travel on 13 October.

| Step | October expenses without commissions (Activity, Invoices) | October cash | Left to pay |
|---|---|---|---|
| Invoice entered | 45 + 35 + 150 = €230 | €80 paid | €150 |
| Split: cleaning → A, linen and travel → B | €230 (unchanged) | €80 | €150 |
| Both cleanings reconciled | **€150**: counted once | €80 (payments moved, same dates) | 150 − 80 = **€70** |
| Cleaning of 4 October restored | 45 + 150 = €195 | €80 | 150 − 35 = €115 |

After the split: stay A, costs €100, margin 510 − 100 = **€410**; stay B, costs €50, margin 255 − 50 = **€205**.

## A document

A document (PDF) **counts in no total**: the expense does. Attaching a PDF to an expense, detaching it or deleting it creates, changes or removes no expense, in any reading. An expense with a document cannot be deleted, only archived (or detached from its document first).

**Duplicates.** Before an expense is saved from an invoice, on every property:

| Case | Rule | Effect |
|---|---|---|
| Same file | Same SHA-256 fingerprint, whatever the file name | Certain: refused, link to the existing expense |
| Same reference | Same supplier and same invoice number ("F-018", "f 018" and "F018" are the same number) | Certain: refused, link to the existing expense |
| Similar | Same supplier, same date and same amount, one of the two invoices without a number | Probable: saved only after "I checked: this is another invoice" |
| Amount only | Same amount, nothing else in common | Never a duplicate |

An invoice with another number, even with the same amount on the same date, is not a duplicate.

**To complete.** A document is listed in *To check* while it is attached to no expense or lacks the supplier or the amount.

## Indicators

| Indicator | Formula | Excludes |
|---|---|---|
| **Revenue** (*Money received* in Cash) | Stay revenue + adjustments + other income | Taxes collected for a third party, deposits, net payouts already counted |
| **Expenses** | Commissions + operating expenses | Loans, taxes, equipment, "information only" entries |
| **Balance before financing** | Revenue − Expenses | Financing, taxes, investments. Not a taxable profit |
| **Investments** | Equipment and one-off spending | Never turned into a recurring charge |
| **Taxes** | Taxes category | Tourist taxes collected for a third party |
| **Financing** | Loan instalments, split into principal, interest and insurance when known | Never counted twice |
| **Balance after financing** (Activity, Invoices) | Balance before financing − Financing | |
| **Cash after financing** (Cash) | Money received − every payment made | |
| **Nights** | Nights of non-cancelled stays inside the period | Departure day, cancelled stays |
| **Occupancy** | Nights ÷ available nights | Unavailable periods, days before the activity start |
| **Average revenue per night** (Activity) | Stay revenue ÷ nights | Adjustments, other income |
| **To pay** | Expenses dated before the end of the period − recorded payments | Archived entries |
| **To receive** | Expected payout of stays + income outside stays − money received | Stays with unknown amount (listed to check), provisional stays |

**Changes.** The percentage under an indicator compares the period with the previous one (previous month, previous year, or the same length just before), computed with the same reading and rules. Without a reference value, no percentage is shown.

## A checkable example

For one month: €1,000 activity revenue, €30 commission, €80 cleaning, €20 linen, €10 travel and €60 repair.

- Balance before financing: 1,000 − 30 − 80 − 20 − 10 − 60 = **€800**.
- If everything is paid within the month and a €200 loan instalment is paid: money received €970 (net payout, commission deducted), payments €170 + €200; cash after financing **€600**.
- If the payments happen the following month, Cash changes; the Activity reading does not.

The demo's example month reproduces exactly these figures; the test `test_documented_example_T03` checks them.

Services example: a €150 invoice holds €100 cleaning, €40 linen and €10 travel; €90 goes to stay A and €60 to stay B. The yearly table keeps **one** €150 expense, not €300. The demo holds this invoice, already split (see "A supplier's invoice").

## Glossary

| Term | Meaning in Rental Cockpit |
|---|---|
| **Revenue** | Money earned by the rental (accommodation, cleaning fees charged to guests, other income). |
| **Commission** | Fees kept by a platform on a booking. |
| **Payout** | Money actually received from the platform or the guest. |
| **Payment** | Money actually paid, with a date and an amount. |
| **Invoice** | Dated document supporting an expense. |
| **Expense** | Entry that counts in the results, with or without an attached invoice. |
| **Document** | PDF attached to an expense; attaching it creates or changes no expense. |
| **Allocation** | Split of an expense between stays or services, without a new charge. |
| **Occupancy** | Share of available nights actually rented. |
| **Cash** | Money received minus money paid, on the dates of the movements. |
