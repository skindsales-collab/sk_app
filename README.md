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

Every function has a home screen (`sk_app/functions.py`): Sales, Marketing, Store, Purchase, Production, Quality and
Accounts are live; HR, Machine Shifting, Design, IT / ERP and Management already get My Day (their ERPNext tasks),
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

### Finance (live)

Finance (`sk_app/finance.py`, owner Accounts): Cash Today (bank / cash balances, money in and out today), To Collect
(customer dues by age with Call / WhatsApp reminder, spoken promise with a reminder on the promised day, payment
received → Payment Entry from the invoice; the salesperson is told), To Pay (supplier and contractor dues; above
`sk_po_approval_limit` SK approves on the **Payment OK** tile before paying), Bills to Post (bill photos sent by
Purchase / Store → Purchase Invoice from the PO with the supplier's bill no., drafts checked and posted), Invoices
(Delivery Notes without invoice → Sales Invoice draft → Post), Expenses (approved Expense Claims to pay, petty cash
voucher with photo and spoken narration → Journal Entry), Segment P&L (this month's income, cost and margin by cost
centre from the GL) and Month Close (stock closing 2nd, P&L 7th, MAR 10th, GSTR-1 11th, GSTR-3B 20th, ticked as ToDos).

### Production, subcontractors and Quality (live)

Production (`sk_app/production.py`): Order Board (every open Work Order with its Job Cards as coloured stages, late
and "no Sales Order / delivery date" flags), Job Cards, Need Material (Material Request *Material Transfer* to the
job; spoken words that match no item go to Store as a task), Progress Photos on the Work Order and Ready to Dispatch
(all stages done, with the QC result). Each **subcontractor** login has a workstation and sees only that
workstation's Job Cards: big ▶ Start / 📸 Photo / ✅ Done buttons, the drawing PDF, Need Material and Problem.
Done closes the time log, saves photos and "Workers used", tries to post the Job Card (kept as a draft with a note
when ERPNext refuses) and gives Quality a check task.

Quality (`sk_app/quality.py`): Inspect lists checks waiting (incoming = Purchase Receipts of the last 14 days, stage
= finished Job Cards, final = operations named final / inspection / QC). The checklist comes from the Quality
Inspection Template (guessed from the operation name; a short standard list when none exists): one OK / Not OK tap
per point, a spoken note for every Not OK, photos. The Quality Inspection is saved under the inspector's login; a
rejected stage opens a **Non Conformance** with a task for the workstation's subcontractor (his **To Fix** tile) and
Production; a rejected receipt tells Store and Purchase. Fixed = what was done + after photo, NC resolved.

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

## Change list Rev 13, part A (26-Oct-2026)

- **Admin icons by function only**: Logins for HR and Management; Team Reports for a person with team members or
  Management. Editing a login sets the ERPNext roles to the chosen functions' roles (old HR / Sales Manager roles
  are taken off); the Logins screen shows each person's ERPNext roles.
- **Real week plan** (My Calendar → My Week): each function's weekly routine (`functions.ROUTINE`) first, then open
  work spread over the working days by free hours, overdue first; day load shown, overloaded days amber;
  "⇄ Move to" another day.
- **AI & ERP desk** (`ai_desk.py`, Samir): Improvement Inbox (every DSI and Report Problem; sort → ToDo, close →
  DSI), Department Visit, ERP Gaps, App Users, Change List, Projects, Training Progress, ERPNext desk.
- **Work Book inside My Day**: "＋ I did extra work" and "Done today".
- **New lead**: saved screen with the lead number and where it is (ERPNext CRM → Leads); My Leads tabs
  New today · To call · All.
- **Icon colours** (`colours.py`): red late / must-do, amber due today, blue new, green ✓ done; DSI red until posted.
- **Mic and camera**: every photo button offers Camera · Gallery · PDF, shows a preview, shrinks photos to about
  300 KB and sends them at once with retries; spoken numbers become digits; mic on mobile / e-mail boxes;
  forms survive the camera closing the page; "Open in Chrome" inside WhatsApp / Facebook.
- **Accounts ledger-wise** (`ledger.py`): Cash / Bank, Receivables, Payables, Purchase Invoice and Debit Note,
  Sales Invoice and Credit Note, Journal Voucher, Direct and Indirect Expenses, Segment Wise P&L (Cabin /
  Non-Cabin net) and the Month Wise Report.
- A screen that fails shows the reason and lands in the AI & ERP inbox.

## Change list Rev 13, part B: team mailboxes and auto leads (26-Oct-2026)

- **Mail → Team mailbox** (`mailbox.py`): cabin@ for Sales / Marketing, service@ for Aditya, acc@ for Accounts,
  sales@ for the CEO, info@ for HR (SK App Settings → Team mailboxes). Each mail shows New → Taken by … →
  Replied / Lead made / Not a lead; "I'll answer", "Give to" (manager), "Make lead", reply from the team mailbox
  signed with the person's name and mobile. The mails come from ERPNext Email Accounts.
- **Auto leads, free** (`lead_sources.py`, every 5 minutes): IndiaMART enquiry mails, JustDial lead mails and GeM
  bid alerts become CRM leads with source, segment and owner (digital → Pranali, cabin / GeM → Rushi, machine
  shifting / job work → Aditya; SK App Settings). Same mobile within 90 days → a note on the earlier lead.
  IndiaMART's Leads API is a paid add-on and is not used.
- **Excel upload**: the IndiaMART Lead Manager export (or a JustDial list) uploaded from New Lead or Lead Sources.
- **Lead Sources** page (AI & ERP, CEO): sources on / off, leads today / this month, check now, mailboxes set up.

## Change list Rev 13, part C: segments, View Member App, CEO dashboards (26-Oct-2026)

- **Point 2, Cabin / Non-Cabin** (`segments.py`): Customer Group is the segment. The tree is All Customer Groups → Cabin
  (Standard Cabin (GI / ACP), LGSF, Modular / Labour Camp) and Non-Cabin (Machine Shifting, Job Work, Other Non-Cabin).
  CRM Lead / Deal keep the sub-segment in `sk_segment` and get `sk_main_segment`, filled on save. Segment is required on a
  new lead. A customer made from a won deal gets the deal's group. SK App User → *Segment (customers seen)*: Cabin team
  Cabin, Aditya Non-Cabin, Management / Accounts both (blank = from the function). The 🏠 Customers icon shows only the
  person's segment; Management, the sales manager and Aditya also get "Segment not set" with one-tap tagging (the old
  Commercial / Government / Individual group moves to Customer Type and is noted on the customer). The same rule on the
  ERPNext desk (User Permission on Customer Group) is a switch in SK App Settings, off until old customers are tagged.
  The Tally import of old customers comes later, after SK checks the match list.
- **Point 3, 👀 View Member App** (`view_member.py`): the CEO picks a member and the app opens as that member sees it.
  Every reading screen runs with the member's own ERPNext permissions (`api.view_as`, GET endpoints only, rolled back
  after). Save / send / call are blocked, mic and camera are hidden, and the PIN page is never shown. A yellow bar has
  💡 (idea goes to the AI & ERP inbox with the page name) and Exit. Each view is written to Activity Log.
- **Point 13, 📊 Live dashboards** (`dashboards.py`): 14 icons on the CEO Home: Overview, Daily Review, Sales, Marketing,
  Machine Shifting, Job Work, 100 Cr, Finance, Manufacturing, Purchase, Store, Quality, HR, AI & ERP. Each is live from
  ERPNext with month and Cabin / Non-Cabin filters and last month's figure. A number opens its list and a row opens
  the record. Swipe left / right moves between pages. A red number on an icon means items need attention there.
- **Point 5, 🛠️ Complaints** (`complaints.py`): the salesperson registers a complaint (customer from their segment or
  untagged, latest order picked by itself, spoken / written text, photos / files, one of 10 types). It is kept as a
  standard ERPNext Issue with SK fields (stage, order / delivery / invoice, segment, sent to, fix by, customer OK, cost).
  By type it goes to Production (factory faults also make a Non Conformance for the workstation subcontractor's My
  Fixes), Store, Design / AI desk, Accounts, Aditya or the sales manager, with a ToDo and a red number. Steps: Accept with a
  fix date → Fixed with an after-fix photo → Customer OK closes it, Not OK sends it back. A passed fix date shows red.
- **Point 7, manuals and FAQ** (`training.py`): a person in two functions now sees the lessons of both (Sales also
  Marketing). Training → FAQ shows the FAQ of each of the person's functions (SK Library Item, category FAQ), searchable by
  voice, with ❓ Ask a question: it goes to the person's manager (or the function head) as a ToDo, the answer comes back
  to the person and can be added to the FAQ with one tap. The Finance, HR and Manufacturing manuals themselves come to SK
  as PDFs first and are loaded only after SK's OK.
- **Point 8, product cards** (`products.py`): one card per product / service = SK Library Item (category Product) with
  Item Group, photos (attached), sizes, brochure, video and internal notes (staff only, never in a customer message).
  Company & Products → Products lists Cabin and Non-Cabin; Item Groups with no card yet show greyed so the list is
  complete. New Lead has "Product asked" (`sk_product` on CRM Lead / Deal), and the lead / deal page shows "Products for
  this customer" with one-tap WhatsApp share. Photos, sizes and brochures come from SK / Sales.
- **Point 1, check before saving** (`photocheck.py`): on New Lead, New Supplier, supplier bill and Dispatch, a
  "Check before saving" card shows each value with its ERPNext field: green ✓ fits, amber ⚠ suggestion, red ✗ needed.
  It checks duplicate mobile (lead / customer), nearest customer / supplier, duplicate bill number, bill total against
  open POs, GSTIN format with state and PAN, and the number plate format. GST certificate and bill photos are read on the
  phone (free reader) to fill empty boxes. A picked suggestion is remembered in the new SK Photo Match list. Every photo
  also shows which ERPNext record it goes to, with a warning if it is too dark or blurred.
- **Point 16 + HR step, attendance, leave and expenses** (`hr.py`): HR (Aarti) uploads the Optick "Basic Report" file
  (or the eSSL thumb machine file) on Attendance → Upload. Each row becomes an ERPNext Employee Checkin (device "Optick"
  / "Office thumb") and, while no Shift Type does auto attendance, a submitted Attendance (late after SK App Settings
  "Late after", 09:15). People are matched by Attendance Device ID, then mobile, then name; a person not found is picked
  once and their ID is saved on the Employee. "23:00:00 Auto Checkout" is a missed out-punch (no OUT made). Absent is
  never written from the file. Attendance → Today / Month shows present, late, no check-in, leave and absent days; HR fixes a
  day from a person's "Ask HR to fix". My Day shows "In 9:02 (Optick)" on top; tap it for my month, selfie check-in
  (backup, with location) and "Ask HR to fix". Everyone (not subcontractors) has Leave & Expense: Leave Application and
  Expense Claim with bill photo, approved by the manager (Employee approver, else Reports to, else app manager, else HR).
  Approved claims Accounts cannot post yet get a ToDo to Accounts. ERPNext v16 needs a Holiday List Assignment for leave.
- PO approval limit is Rs 5,000 (SK 26-Oct); site config `sk_po_approval_limit` changes it.
- **Send to design** (SK OK 26-Oct): New Lead has a "Send to design (AI drawing)" switch for Cabin segments, on by
  default. On save the lead becomes a CRM Deal through Frappe CRM's own conversion (owner = salesperson), Design Status
  "Sent to Design" when that option exists, with the lead's photos and requirement notes copied to the deal, because the
  AI design pickup reads deals only.

## SK Hub: one Claude connector for all Claude Projects (28-Oct-2026)

Every Claude Project (Sales, Design Cabin, Store, Purchase, Manufacturing, Quality, Finance, HR, Machine Shifting ...)
connects to ERPNext through **one** connector instead of its own API key and cloud environment.

- **Address for Claude:** `https://<erpnext-site>/api/method/sk_app.hub.mcp` (`sk_app/hub.py`, MCP over HTTP).
- **Login:** each person signs in with **their own ERPNext login** through Frappe's built-in OAuth (OAuth Settings:
  dynamic client registration, auth-server and protected-resource metadata, all on by default in v16). No keys are
  kept in Claude. Only desk (staff) users can connect; portal customers / suppliers cannot.
- **Permissions:** every tool runs as that person, so their roles and the CRM own-leads rule apply as on the desk.
- **Drafts only:** the hub creates and changes drafts; it never submits, cancels or deletes. Users, roles, permissions,
  scripts, settings and OAuth records are never changed, and token / secret records are never read
  (`NO_READ` / `NO_WRITE` in `sk_app/hub_tools.py`).
- **Handoffs:** `SK Hub Handoff` passes work from one team's Project to another (team = SK App User home function).
- **Shared log:** every write is in `SK Hub Log`, so each Project can see what the others changed before any bulk job.

Tools: `hub_overview`, `describe_doctype`, `search_records`, `get_record`, `count_records`, `item_stock`, `create_draft`,
`update_draft`, `add_comment`, `post_handoff`, `list_handoffs`, `close_handoff`, `recent_activity`.

Set-up after deploy: check **OAuth Settings** (Enable Dynamic Client Registration, Show Auth Server Metadata and Show
Protected Resource Metadata ticked, Skip Authorization off), then in Claude: Settings → Connectors → Add custom
connector → the address above, Client ID / Secret empty → Connect → ERPNext login → Allow. Tests: `sk_app/tests/test_hub.py`.

## Mandatory gate: no next step until the data is filled (28-Oct-2026)

SK: "without processing mandatory things the screen will not process further, and all data will be captured". The rules
are in `sk_app/gate_rules.py` (unit tested) and applied by `sk_app/gates.py` both in the app and in ERPNext (doc events),
so the phone, the ERPNext desk and the API all stop at the same place. Every refusal lists what is missing in plain words.

| Screen | Must be filled before it moves on |
|---|---|
| New lead | Real customer name (not "Enquiry"), mobile (10 digits), source, segment; salesperson = the person |
| Lead / deal status | Moving past New needs the lead data above. Quotation step needs a quotation; Negotiations a submitted quotation; Won a submitted Sales Order. Old "Enquiry" leads get a ⚠️ card on the detail screen to fill the gaps; locked status chips show 🔒 and why |
| Customer (from the deal) | GSTIN (checked, 15 characters) or "unregistered" with the reason; billing address with state and PIN; mobile |
| Quotation | Submitted only with a complete customer, items with qty and rate, GST (company default template applied) and valid-till date. The app submits it when complete; a draft shows "Submit quotation" |
| Order received = Deal Won | Order date, promised delivery date (no default), customer PO number or PO copy. The Sales Order is made from the quotation and submitted; the deal (and its lead) turn Won with the order value. Without the right to submit, it waits for the manager's Confirm |
| Sales Order (ERPNext too) | Delivery date, PO number or PO file, items with rate, value, complete customer |
| Purchase request | Item and qty, required-by date, reason (ERPNext's own re-order run gets an automatic reason); CEO approval as before |
| Stock count | Every line counted (0 if none), not only the differences |

Junk / lost needs nothing. Background drafts (mail leads, design quote values) are still saved; the gate sits on the step
that moves them on.
