from datetime import date

from sk_app import old_crm_rules as R

KNOWN = {"mobiles": {"9822012345"}, "users": {"skindsales2@gmail.com"}, "sources": {"JustDial"},
	"reasons": {"Pricing", "Other", "Junk Lead ( Not required our product )"}}


def row(**kw):
	base = {"first_name": "Amol", "organization": "Aakar", "mobile_no": "+91 98500 11111", "source": "JustDial",
		"lead_owner": "skindsales2@gmail.com", "status": "Deal Loss", "lost_reason": "Pricing", "lost_notes": "price high",
		"date": "2026-06-12", "closed_date": "2026-06-20"}
	base.update(kw)
	return base


def test_new_closed_lead_keeps_owner_reason_and_marker():
	lead, why = R.lead_from_row(row(), KNOWN)
	assert why == "" and lead["mobile_no"] == "9850011111" and lead["lead_owner"] == "skindsales2@gmail.com"
	assert lead["lost_reason"] == "Pricing" and lead["lost_notes"].startswith(R.MARKER)


def test_same_mobile_already_in_erpnext_is_skipped():
	lead, why = R.lead_from_row(row(mobile_no="9822012345"), KNOWN)
	assert lead is None and "already" in why


def test_unknown_owner_source_reason_are_left_blank_or_other():
	lead, _ = R.lead_from_row(row(lead_owner="snehal@x", source="Biziverse", lost_reason="Long distance"), KNOWN)
	assert lead["lead_owner"] is None and lead["source"] is None and lead["lost_reason"] == "Other"


def test_open_quote_has_no_lost_reason_and_carries_quote_no():
	lead, _ = R.lead_from_row(row(status="Quotation", quote_no="12", quote_amount="90000"), KNOWN)
	assert "lost_reason" not in lead and "quote no 12, Rs 90000" in lead["lost_notes"]


def test_other_status_and_zero_mobile():
	assert R.lead_from_row(row(status="Deal Won"), KNOWN)[0] is None
	assert R.mobile_key("0000000000") is None


def test_dates_fall_back_to_created():
	assert R.dates_of(row()) == (date(2026, 6, 12), date(2026, 6, 20))
	assert R.dates_of(row(closed_date="")) == (date(2026, 6, 12), date(2026, 6, 12))


def test_same_mobile_on_another_date_is_a_new_lead_sk_17_nov():
	from datetime import date

	known = {**KNOWN, "mobile_dates": {("9822012345", date(2026, 3, 2))}}
	same_day = {"first_name": "Ram", "mobile_no": "9822012345", "status": "Junk Lead", "date": "2026-03-02"}
	other_day = {**same_day, "date": "2026-07-15"}
	assert R.lead_from_row(same_day, known)[0] is None and "same date" in R.lead_from_row(same_day, known)[1]
	lead, why = R.lead_from_row(other_day, known)
	assert lead and lead["mobile_no"] == "9822012345" and why == ""
	assert R.lead_from_row({**same_day, "status": "New"}, {**known, "mobile_dates": set()})[0]["status"] == "New"
