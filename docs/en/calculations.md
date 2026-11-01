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
| **To pay** | Expenses − recorded payments | |
| **To receive** | Expected payout of stays − money received | Stays with unknown amount (listed to check) |

**Changes.** The percentage under an indicator compares the period with the previous one (previous month, previous year, or the same length just before), computed with the same reading and rules. Without a reference value, no percentage is shown.

## A checkable example

For one month: €1,000 activity revenue, €30 commission, €80 cleaning, €20 linen, €10 travel and €60 repair.

- Balance before financing: 1,000 − 30 − 80 − 20 − 10 − 60 = **€800**.
- If everything is paid within the month and a €200 loan instalment is paid: money received €970 (net payout, commission deducted), payments €170 + €200; cash after financing **€600**.
- If the payments happen the following month, Cash changes; the Activity reading does not.

The demo's example month reproduces exactly these figures; the test `test_documented_example_T03` checks them.

Services example: a €150 invoice holds €100 cleaning, €40 linen and €10 travel; €90 goes to stay A and €60 to stay B. The yearly table keeps **one** €150 expense, not €300.

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
