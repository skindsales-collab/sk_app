# SK Phone (Android helper)

SK 28-Oct-2026, review list Rev 1 points 17 and 18. A web app cannot read the phone's call list, so this small app
sends the calls to ERPNext as CRM Call Logs, matched to the lead or deal and counted for the person's login.

- **Company phone:** every incoming, outgoing and missed call is sent.
- **Personal phone:** only calls with numbers that are already in CRM are sent; personal calls never leave the phone.
- Reads only number, time, length and in / out. No call recording, no contacts, no messages.
- Linked once with the person's mobile number + PIN. The CEO can unlink a phone in the app: Logins → Unlink SK Phone.
- Sends every 15 minutes when there is internet, or at once with "Send calls now".

The APK is built by GitHub Actions (`.github/workflows/sk-phone.yml`) and attached to the release "sk-phone-latest".
Install it from the file (Android asks to allow installing from this source once).
