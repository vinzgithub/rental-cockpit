# Getting started — the first ten minutes

This walk-through uses the **demo**: nothing you do here touches your real data.

## 1. Create the administrator account

On first opening, Rental Cockpit asks for a user name and a password (at least 10 characters). This account can configure everything. No account exists by default.

![Creating the first account](../images/en/first-account.png)

## 2. Choose: your data or the demo

The welcome screen shows the five getting-started steps and two choices:

- **Use my data**: you start empty and create your first property;
- **Explore the demo**: two fictional properties, a year of invented activity.

Every step can be resumed later. Choose the demo.

![Welcome screen](../images/en/welcome.png)

## 3. Read the Overview

A banner permanently reminds you that the data is fictional. The period offered is the demo's **example month**, which reproduces the documentation example:

- Revenue **€1,000**, Expenses **€200**, Balance before financing **€800**;
- Appartement A: €600 / €120 / €480; Studio B: €400 / €80 / €320.

Under each amount, the percentage compares with the previous month, which is ordinary fictional activity.

![Overview](../images/en/overview-desktop.png)

## 4. Change the reading

At the top, **Activity / Invoices / Cash** changes the calculation rule, not the data:

- in **Cash**, revenue becomes *money received* (€970: the commission is already deducted);
- the balance before financing stays €800 when everything is paid within the month.

A sentence under the buttons always says what the chosen reading measures.

## 5. Understand an amount

Click **How is this amount calculated?** under the balance. The window shows:

- the equation Revenue − Expenses = Balance;
- the formula, period, reading, properties included and what is excluded;
- **every line used**, with the rule applied to each ("Spread night by night over the stay", "Counted on its date"…) and the total.

![Explanation of the balance](../images/en/explain.png)

## 6. What remains to check

The **To check** card lists what keeps a result from being final. In the demo: cleaning expenses of the previous month whose payment is not confirmed yet.

## 7. Switch to your data

The banner offers **Use my data**. You land on an empty space with the getting-started steps: create your first property (only the name is required). The demo stays available and separate: the **My data / Demo** switch is at the bottom of the sidebar (in the account window on a phone, and in Settings).

## 8. Enter a stay

**Stays → Add a stay**: choose the property, the arrival and the departure. Under the dates, Rental Cockpit already shows how the nights split ("3 nights in September · 3 nights in October"). Fill in, when you know them, the gross amount paid by the guest and the platform commission: the expected net payout is computed. An unknown amount stays empty: it is never counted as 0.

The stay page then shows:

- the amounts, what was already received and what is left to receive;
- **what the stay counts in the Overview**, month by month;
- the payouts received, with **Record a payout** when the money arrives;
- **Edit**, **Cancel the stay** (with any amount retained) and, for an entry made by mistake, **Delete**.

In the Overview, "1 payout to confirm" leads straight to the list of stays to check.

![List of stays](../images/en/stays-desktop.png)

![A stay page](../images/en/stay-detail.png)

## 9. Import a file

Rather than typing everything, **Stays → Import** (or **Add → A bookings file**):

1. **File**: choose *Airbnb* for the French "Historique des transactions" export, as Airbnb provides it, or *Other CSV file* (Booking.com, Abritel, spreadsheet…), then choose or drop the file.
2. **Check**: nothing is saved yet. For a CSV, check the column chosen for each piece of information against the example shown; state the platform and, when the file has no commission, its rate. Attach each listing of the file to one of your properties. Each line says what will happen:
   - *New*: the stay will be created;
   - *Updated*: a stay already imported changes (the "before → after" detail is shown);
   - *Probable duplicate*: a stay entered by hand has the same dates — by default it is **completed** with what it did not know (reference, commission…), what you typed is kept; you can also create another stay or skip the line;
   - *Up to date*, *No property*, *Error*: nothing will be written, and the reason is given.

   Remarks point at what deserves a look: overlap, unavailable dates, arrival before the activity start, payout already recorded or above what is expected.
3. **Result**: the number of stays created, updated, completed and of payouts recorded. **Undo this import** puts everything back as it was, as long as none of these stays was changed; it can also be done later from **Previous imports**.

Importing the same file again creates nothing twice: everything is *Up to date*. The choices (columns, properties, rate) are remembered for the next file. Guests' names are only taken when you tick the option.

![Preview of an Airbnb import](../images/en/import-preview.png)

## 10. Protect your account

In **Settings → Two-factor sign-in → Turn on**:

1. confirm your password;
2. scan the QR code with an authenticator app (Aegis, Google Authenticator, 2FAS, Bitwarden…), or type the key by hand, then type the six-digit code shown;
3. store the **ten recovery codes** (copy, download): each one opens a single sign-in if you lose your phone. The window only closes once "I have stored these codes safely" is ticked.

At the next sign-in, the code is asked after the password. The other browsers signed in to this account are signed out.

![Turning on two-factor sign-in](../images/en/mfa-setup.png)

## 11. Home Assistant (optional)

In **Settings → Home Assistant and API → Create a key**, Rental Cockpit shows once the line to paste into `secrets.yaml`. The address to enter in Home Assistant is shown just above. What comes next (sensors, card, automations): [home-assistant.md](home-assistant.md).

![Settings: account, two-factor sign-in on, a key for Home Assistant](../images/en/settings-desktop.png)

## On a phone

The same Overview shows in one column, balance first, with a navigation bar at the bottom. On touch screens, controls aim at 44 × 44 pixels.

<img src="../images/en/overview-phone.png" alt="Overview on a phone" width="260"> <img src="../images/en/stays-phone.png" alt="Stays on a phone" width="260"> <img src="../images/en/import-phone.png" alt="Import on a phone" width="260"> <img src="../images/en/settings-phone.png" alt="Settings on a phone" width="260">
