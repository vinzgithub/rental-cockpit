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

## Three views of the Overview

The Overview opens on **My money**. The other two views are one click away. The calculation rules are the same everywhere: only the presentation changes.

| View | Question | What it shows | Method used |
|---|---|---|---|
| **My money** (default) | What money came in and went out, what is left to receive or pay? | Money in, Money out, Balance of the period; Left to pay and To receive at the end of the period | By payment date |
| **Rental performance** | What did the rental produce? | Revenue from nights, Commissions, Rental result; nights, occupancy, average revenue per night, other income and expenses; the twelve months of the year | Per night occupied |
| **Accounting analysis** | How is each amount tied to a period? | The three methods below, as chosen, with the balance before and after financing | As chosen |

**Money in** = payouts sent by the platforms + payments received, on their date. **Money out** = expenses, loan instalments, taxes and equipment paid, on their date. **Balance of the period** = Money in − Money out: the money movement of the period, not a profit.

**Rental result** = Revenue from nights + Other income − Commissions − Other expenses, before loan and taxes.

### Payout sent, payout credited

A platform sends a payout, then the bank credits it a few days later. Rental Cockpit counts a payout **on the day the platform sends it**, labelled "Payouts sent by the platforms". When the export gives the latest day it reaches the account (Airbnb: "Arrivée au plus tard le"), it is kept with the payout. It is shown under each line of "How is this amount calculated?". Example: an Airbnb payout sent on 31 October and expected by 6 November at the latest counts in October, marked "on the account by 6 Nov at the latest".

### The three ways of tying amounts to a period (Accounting analysis)

| Method | Question | Stay | Expense | Payment |
|---|---|---|---|---|
| **Per night occupied** | What did the rental produce during the period? | Revenue and commission spread night by night | On its date, or day by day over its covered period (e.g. an annual insurance) | Ignored |
| **By stay or invoice date** | Which stays start and which invoices are dated in the period? | On the arrival date | On the invoice date | Ignored |
| **By payment date** | What money actually moved? | Payouts sent or money received, on its date | Payments made, on their date | Counted |

The method used is always shown. Figures from two methods are never added together.

Special cases:

- **Cancelled stay**: no nights; any retained amount counts once, on the arrival date.
- **Adjustment or refund**: counted on its own date, without erasing the original amount.
- **Platform commission**: operating expense per night occupied and by stay date. By payment date it is not a payment, since it is already deducted from the payout received.

## A stay, from entry to the Overview

A stay is entered in the **Stays** screen: property, arrival, departure and, when known, the gross amount paid by the guest and the platform commission. The **expected net payout** is gross − commission, unless another amount is entered (the platform paid something else). The tourist tax collected and the security deposit are recorded apart: **they are never revenue**.

Example (it is the test scenario): a stay from 28 September to 4 October 2026, €600 gross, €90 commission.

| | September 2026 | October 2026 |
|---|---|---|
| Nights | 3 | 3 |
| **Per night occupied** — revenue / commission / balance | €300 / €45 / €255 | €300 / €45 / €255 |
| **By stay date** — revenue / commission / balance | €600 / €90 / €510 (arrival month) | €0 |
| **By payment date** (My money) — before the payout | €0 | €0 |
| **By payment date** (My money) — after "payout received: €510 on 5 October" | €0 | €510 in |

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

**A booking cancelled but compensated** (the guest cancels late, the platform still pays a compensation) is a cancelled stay whose retained amount is that compensation. The money counts, the nights do not. Example (it is the test scenario): a five-night booking from 18 May, cancelled and compensated €220 gross (€8.20 commission, €211.80 paid), then another booking for the night of 22 May. In May: **1 night** (the 22nd), revenue 220 + 125 = €345 per night occupied, €211.80 + €120.50 money in. No overlap is counted.

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

- **"Payout"** lines are transfers of amounts already on the lines after them (same date): they are **never counted a second time**. Each one is however **checked to the cent** against the lines it pays, and gives the date it was sent and the date it reaches the account ("Arrivée au plus tard le").
- The other lines are never dropped in silence (see below).
- One code on several lines makes one stay, whose amounts add up. If those lines disagree on the dates or the listing, the stay is refused rather than guessed.
- The day/month order comes from the unambiguous dates (Airbnb writes MM/DD/YYYY); a file mixing both is refused.
- When gross − service fee ≠ amount paid out, a remark says so.

**CSV**: each column is chosen in the preview. Amounts in French or English format ("1 234,50", "1,234.50"). Without a commission column, a **rate** can be given: commission = gross × rate, rounded to the nearest cent (half a cent up). Example: 15% of €333.33 = €50.00; 3.5% of €333.33 = €11.67.

**Payouts in the file**: recorded on the date they were sent, once (same date and amount already recorded = skipped), never above the expected payout, and only when their date is past.

### Airbnb operations that are not bookings

| Airbnb line type | Becomes | Category | Settled |
|---|---|---|---|
| Versement de résolution (including AirCover damage refunds) | Income outside stays, no night | Compensation (damage, resolution) | On the date of the payout that pays it |
| Crédit divers (bonus, goodwill credit) | Income outside stays | Platform bonus or credit | On the date of the payout |
| Régularisation de la résolution, negative amount | Expense: a refund to a guest, withheld by Airbnb | Refund to a guest | Withheld from the payout, on its date |
| Unknown type | Shown with its amount, **nothing is written without your choice** | Other income or Other expense | On the date of the payout |

The **payout** and the **operation** it pays are one sum: only the operation is recorded, with a payment on the payout date. Each operation is recognised by its type, booking, date and amount: importing again adds nothing, and undoing the import removes it.

Example (it is the test scenario, fictional data): in October, six Airbnb payouts for **€1,355.00**. Five pay bookings (€1,260.00), one pays an AirCover damage refund (€95.00). The import creates five stays and an income "Airbnb compensation" of €95.00, with no stay and no night. *Money in* for October: €1,355.00.

**Payouts check.** Before anything is imported, the preview adds up the file's payouts, by kind (stays, compensations, credits, amounts withheld, operations to check) and by month sent. It says which sums paid **would not be recorded** (line left out, in error or without a property): while they are not, the period's results are not complete.

**Overlap.** When two bookings of the file overlap, **both** lines say so. Each offers "Cancelled, amount received kept", for the one Airbnb cancelled and compensated (see "A booking cancelled but compensated").

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

**The three methods.** *Per night occupied*, the entry counts on its date, or day by day over its **period covered** when it has one (an annual insurance of €240 from 1 November 2026 to 1 November 2027 counts €19.80 in November: 30 days of €0.66, the remaining cents going to the largest remainders). *By invoice date*, it counts on its date. *By payment date* (My money), only its **payments** count, on their date and for their amount.

**Payment status.** The status always comes from the payments recorded:

| Status | When |
|---|---|
| Paid (Received) | The payments cover the whole amount |
| Partly paid (received) | Part of it is settled |
| To pay (To receive) | Nothing is settled and the entry is known to be due |
| Payment to confirm | Nothing is settled and nobody said whether it is: listed in *To check* |

A payment never exceeds what is left, and the amount of an entry cannot go below what was already settled.

Example (it is the test scenario): a €300 repair dated 10 October 2026, to pay, then a €100 payment on 12 October. In October: per night occupied and by invoice date, €300 of expenses; by payment date (*Money out* of My money), €100; €200 is left to pay.

**Instalments.** A monthly series creates one entry per month, on the same day (the 31st becomes the last day of a shorter month). Each instalment is settled on its own. An instalment dated after today is *planned*: it is not yet in "To pay" on the Expenses screen. When principal, interest and insurance are given, they must add up to the instalment; the Overview details them under **Loan repayments**. Example: €500 = €350 principal + €120 interest + €30 insurance; in October, the balance before financing is unchanged, the balance after financing is €500 lower.

**Archiving** removes an entry from every total without erasing it; its payments are kept. **Deleting** is only possible for an entry with no payment and no document.

## A supplier's invoice

**Services.** An invoice can be broken down into lines: cleaning, linen, travel, other, discount, tax, adjustment. A line has an amount, or a quantity and a unit price (amount = quantity × price, which must come out exactly to the cent: nothing is quietly rounded). A discount is negative; an adjustment may be, and needs a reason. **The lines must add up to the invoice amount**, otherwise nothing is saved. A supplier's rates pre-fill a unit price, they never change an amount. The invoice stays **one single expense**: it is what counts, whatever the method.

**Split between stays.** Each service (cleaning, linen, travel, other) can be given, in one or several parts, to stays of the same property (only stays that are not cancelled are offered); a discount, a tax or an adjustment follows the invoice. What is given out for a service never exceeds its amount. The stay offered is the one whose departure falls on the day of the work, otherwise the one under way that day. The split **adds no expense**: it says which stays an expense served. A service already split can only be removed from the invoice once its split has been changed. An invoice split only in part is listed in *To check* with the amount left.

**Reconciliation.** An invoice can replace expenses typed by hand for the same services. Offered: the expenses of the same property, in the category of the invoice or of its services, dated between the first day of work (otherwise one month before the invoice month) and the invoice date, with no supplier or the same one. Always refused: an expense of another property, income, an expense that is archived, broken down, already replaced or replacing others. The total replaced does not exceed the invoice amount. The entries replaced leave every total; their payments **move to the invoice** (on their original date: *Money out* does not change) and cannot exceed its amount. A reconciliation is undone entry by entry: it comes back with its payments. An invoice that replaces entries can be neither deleted nor archived until those reconciliations are undone, and its amount cannot go below the total replaced.

**A stay's costs and margin.** The costs allocated to a stay are its shares of split invoices, plus the expenses attached to the whole stay (with no split). **Margin after costs = expected net payout − allocated costs**; it is not computed for a cancelled stay or one whose amount is unknown.

Example (it is the test scenario): stay A from 28 September to 4 October 2026 (€600, commission €90, expected payout €510) and stay B from 10 to 13 October (€300, commission €45, expected payout €255). Two cleanings typed by hand and paid: €45 on 4 October, €35 on 13 October. The supplier then sends their invoice of 20 October: **€150** = 4 h of cleaning at €25 on 4 October + 4 sets of linen at €10 on 13 October + €10 of travel on 13 October.

| Step | October expenses without commissions (per night, by invoice date) | Money out in October | Left to pay |
|---|---|---|---|
| Invoice entered | 45 + 35 + 150 = €230 | €80 paid | €150 |
| Split: cleaning → A, linen and travel → B | €230 (unchanged) | €80 | €150 |
| Both cleanings reconciled | **€150**: counted once | €80 (payments moved, same dates) | 150 − 80 = **€70** |
| Cleaning of 4 October restored | 45 + 150 = €195 | €80 | 150 − 35 = €115 |

After the split: stay A, costs €100, margin 510 − 100 = **€410**; stay B, costs €50, margin 255 − 50 = **€205**.

## A document

A document (PDF) **counts in no total**: the expense does. Attaching a PDF to an expense, detaching it or deleting it creates, changes or removes no expense, with any method. An expense with a document cannot be deleted, only archived (or detached from its document first).

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
| **Money in** (My money) | Payouts sent by the platforms + payments received, on their date | Stays not paid yet (To receive), commissions already withheld |
| **Money out** (My money) | Expenses, instalments, taxes and equipment paid, on their date | Commissions withheld by the platform, unpaid expenses (Left to pay) |
| **Balance of the period** (My money) | Money in − Money out | Not a taxable profit |
| **Revenue from nights** (Performance) | Gross amount of stays spread night by night + adjustments | Commissions, tourist taxes, income outside stays |
| **Commissions** (Performance) | Platform commissions, spread like the stays | Other costs |
| **Other income** / **Other expenses** (Performance) | Income outside stays (compensations, bonuses…) / operating expenses other than commissions | Loan, taxes, equipment |
| **Rental result** (Performance) | Revenue from nights + Other income − Commissions − Other expenses | Financing, taxes, investments |
| **Revenue** (Accounting analysis) | Stay revenue + adjustments + other income | Taxes collected for a third party, deposits, net payouts already counted |
| **Expenses** | Commissions + operating expenses | Loans, taxes, equipment, "information only" entries |
| **Balance before financing** | Revenue − Expenses | Financing, taxes, investments. Not a taxable profit |
| **Investments** | Equipment and one-off spending | Never turned into a recurring charge |
| **Taxes** | Taxes category | Tourist taxes collected for a third party |
| **Financing** | Loan instalments, split into principal, interest and insurance when known | Never counted twice |
| **Balance after financing** (per night, by stay date) | Balance before financing − Financing | |
| **Cash after financing** (by payment date) | Money received − every payment made | |
| **Nights** | Nights of non-cancelled stays inside the period | Departure day, cancelled stays |
| **Occupancy** | Nights ÷ available nights | Unavailable periods, days before the activity start |
| **Average revenue per night** (per night occupied) | Stay revenue ÷ nights | Adjustments, other income |
| **To pay** | Expenses dated before the end of the period − recorded payments | Archived entries |
| **To receive** | Expected payout of stays + income outside stays − money received | Stays with unknown amount (listed to check), provisional stays |

**Changes.** The percentage under an indicator compares the period with the previous one (previous month, previous year, or the same length just before), computed with the same method and rules.

**Month by month** (Rental performance): the twelve months of the period's year, each computed per night occupied with the same rules as the indicators. A month chosen becomes the period shown. Without a reference value, no percentage is shown.

## A checkable example

For one month: €1,000 activity revenue, €30 commission, €80 cleaning, €20 linen, €10 travel and €60 repair.

- Balance before financing: 1,000 − 30 − 80 − 20 − 10 − 60 = **€800**.
- If everything is paid within the month and a €200 loan instalment is paid: *My money* shows Money in **€970** (net payout, commission deducted), Money out **€370** (€170 expenses + €200 loan), Balance of the period **€600**.
- If the payments happen the following month, *My money* changes; *Rental performance* does not.

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
| **Payout sent** | A platform payout, counted on the day it is sent; it reaches the account a few days later. |
| **Compensation** | A sum paid by a platform for damage or a resolution (AirCover): income outside stays, with no night. |
