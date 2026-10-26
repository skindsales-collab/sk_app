# SK App

Mobile work app for SK Ind Tech Solutions Pvt Ltd, built as a Frappe custom app inside ERPNext
(proposal SKIT/IT/APP/001 Rev 5, approved by SK on 25-Oct-2026). Phase 1 is a proof of concept for the Sales pilot.

Staff open **`https://<erpnext-site>/sk`** on their phone, log in with **their own ERPNext user**, and tap
"Add to Home Screen". It works on Android and iPhone with no app store.

## What is in Phase 1

| Screen | What it does | Data |
|---|---|---|
| Home | Tiles for the person's function and the current "what to do now" card | SK App User (function, language) |
| What to do now | Hourly card, written by Claude (or by rules when Claude is off/over budget); Start / Done / Need more time / Problem. Done and Problem re-plan at once | SK Guide Card |
| My Day | All open work, ranked: overdue first, new leads (5-minute rule), follow-ups, deals, quotes, tasks, DSI | Task, ToDo, CRM Lead, CRM Deal, Quotation |
| My Leads / My Deals | Frappe CRM leads and deals owned by the person | CRM Lead, CRM Deal |
| My Score | Live KRA/KPI chart for the month, weighted score and stars; colours green >= 100%, yellow 80-99%, red < 80% | SK KPI Target + counted live from ERPNext |
| Work Book | Add extra work by voice or text, with photo; last 7 days | SK Work Log |
| DSI | Daily Small Improvement with before / after / photo | SK DSI Entry |
| Report Problem | 8 problem types, photo, voice | SK Work Log (type Problem) |

English / Marathi switch on every screen, mic button on every text box (phone speech recognition, mr-IN / en-IN),
and read-aloud for the guide card.

### All functions

Every function has a home screen (`sk_app/functions.py`): Sales and Marketing are live; Production, Quality, Stores,
Purchase, Accounts, HR, Machine Shifting, Design, IT / ERP and Management already get My Day (their ERPNext tasks),
Work Book, DSI, Report Problem and My Score. Their own tiles (job cards, inspections, stock alerts ...) open ERPNext
until they are built in later phases. Each person has a separate login: their ERPNext user, with their own roles.

### Store and Purchase (live)

Store (`sk_app/store.py`): Stock Check (live qty per store), Receive against a PO with challan photo (draft Purchase
Receipt), Issue to a job (Stock Entry *Material Transfer for Manufacture*, posted at once), Requests from Production
(issue from stock or send the short qty to Purchase), Dispatch with cabin / number-plate photos (draft Delivery Note,
Accounts and the salesperson get a task), Low Stock (Item re-order levels → Material Request), monthly Stock Count
(differences only → draft Stock Reconciliation) and New Item from a photo (made disabled, admin enables it).

Purchase (`sk_app/purchase.py`): Requests, Get Rates (Request for Quotation + WhatsApp / mail text sent from the phone),
Compare quotes (Supplier Quotation from a photo of the reply), Purchase Order (placed at once up to the limit; above it
SK approves on the **PO Approvals** tile; limit `sk_po_approval_limit` in site config, default Rs 50,000), delivery
Follow-up, Suppliers (new supplier with GSTIN duplicate check), Bills (photo to Accounts as a task) and Last Rates.

Only people in that function (or the admin) can use these screens; documents are saved under their own login.

### Logins by mobile number

Everyone logs in at `/sk` with their **mobile number and PIN** (email login stays as an option). HR opens the
🔑 **Logins** tile, picks the person (or a new one, e.g. a subcontractor), types the mobile number and taps the
functions; the app makes the ERPNext User (hidden ID `<mobile>@staff.skind.local` when the person has no email),
gives the roles of those functions, links the Employee and shows a first PIN to hand over or send on WhatsApp.
The person sets their own PIN at the first login. HR can reset a PIN or close a login (history stays).
Subcontractors (`Subcontractor` function) get the small `SK Subcontractor` role, no ERPNext desk, and a workstation.
`after_migrate` turns on *System Settings → Allow Login using Mobile Number* (`sk_app/logins.py`).

**OTP by SMS (optional):** when *SMS Settings* in ERPNext has a gateway (for example MSG91 with the DLT-approved
OTP text; site config `sk_otp_message` must match that text), the login page also shows **Send OTP**
(`sk_app/otp.py`: 6 digits, 5 minutes, 5 tries, 5 SMS per number per hour). Without a gateway only the PIN login shows.

A person in several functions (SK App User: Main Function + Other Functions) sees one Home with a labelled row of
icons per function and one "For everyone" row; no switching.

## KPI counting

`SK KPI Target.kpi_code` says how ERPNext counts the actual every month (`sk_app/kpi.py`):

| Code | Counted from |
|---|---|
| `orders_value` | Submitted Sales Orders in the month, net of GST, credited via Sales Team (Sales Person -> Employee -> User), else by creator |
| `digital_orders_value` | Submitted Sales Orders for customers whose CRM Deal source is a digital source (SK App Settings) |
| `cabins_qty` | Quantity of cabin item groups on the person's Sales Orders |
| `leads_worked` | CRM Leads owned by the person with a first response this month |
| `first_response_pct` | % of the person's new CRM Leads answered within the SLA (5 min) |
| `quotes_sent` | Submitted Quotations created by the person |
| `digital_leads` | CRM Leads from digital sources |
| `lead_data_quality_pct` | % of CRM Leads with source, owner and organisation or mobile |
| `dsi_count` | SK DSI Entries |
| `manual` | `manual_actual` typed by the manager (until the source is live) |

Score = actual / target (capped at 120%) x weight. Sources that are not live yet show as "not live yet".

## Install (Frappe Cloud)

1. The site needs a Frappe Cloud plan that allows **custom apps** (private bench). The ERPNext admin checks this first.
2. Add this GitHub repository as an app to the bench, deploy, and install `sk_app` on the site.
3. Put the Claude API key in the site config (never in a DocType, chat or Excel):
   `bench --site <site> set-config anthropic_api_key "<key>"` (Frappe Cloud: Site config tab).
4. Set up the Sales pilot people and targets (matched by ERPNext user full name):
   `bench --site <site> execute sk_app.setup.load_sales_pilot`
5. Check **SK App Settings**: model, effort, monthly Claude call cap, working hours, digital lead sources.
6. Assign ERPNext Tasks to people with "Assign To" so they appear in My Day and the guide.

## Safety

- ERPNext stays the source of truth. The app only reads ERPNext records and writes its own DocTypes
  (guide cards, work book, DSI); it never submits, pays, deletes or changes stock.
- Every endpoint works on the logged-in user only; DSI and Work Book entries are own-record-only for non-managers.
- Claude is called only from the server with the key from site config, minimum data (titles, due times, KPI numbers),
  a monthly call cap, and a rule-based fallback when it is off, over the cap, unreachable or declines.

## Tests

`python -m pytest tests` runs the pure-logic tests (scoring, working hours, ranking, setup data) without a bench.
