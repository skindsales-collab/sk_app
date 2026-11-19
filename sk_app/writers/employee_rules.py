"""Pure rules of the HR line, new joiner (Flow 6): what HR must give before the Employee is saved, and what is only
warned. Bank details are never read or kept in the app; pay is not in the app at all."""

import re

PAPERS = 2  # SK 26-Oct: photo of Aadhaar and bank passbook (PAN, passport photo when there)


def joiner_errors(data: dict) -> list:
	"""Stops the save: name, Male / Female, date of birth, Aadhaar 12 digits, PAN pattern."""
	out = []
	if not " ".join((data.get("name") or "").split()):
		out.append(("emp_no_name", "Please give the name"))
	if data.get("gender") not in ("Male", "Female"):
		out.append(("emp_no_gender", "Please pick Male or Female"))
	if not data.get("dob"):
		out.append(("emp_no_dob", "Please give the date of birth"))
	aadhaar = re.sub(r"\D", "", data.get("aadhaar") or "")
	if aadhaar and len(aadhaar) != 12:
		out.append(("emp_aadhaar", "Aadhaar must have 12 digits"))
	pan = (data.get("pan") or "").strip().upper()
	if pan and not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan):
		out.append(("emp_pan", "PAN looks wrong: 5 letters, 4 digits, 1 letter"))
	return out


def joiner_warnings(mobile: str, photos: int, joined) -> list:
	"""Written to SK Rule Log (Warn only): no mobile means no app login and no attendance match; the papers' photos."""
	out = []
	if len(re.sub(r"\D", "", mobile or "")[-10:]) != 10:
		out.append(("emp_no_mobile", "No 10-digit mobile: no app login can be made"))
	if int(photos or 0) < PAPERS:
		out.append(("emp_no_papers", "Photos of Aadhaar and bank passbook are missing"))
	if not joined:
		out.append(("emp_no_joining", "The joining date is missing (needed for paid leave after 6 months)"))
	return out
