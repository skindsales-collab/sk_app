"""PR D (SK 15-Nov go): mail leads read the HTML part, IndiaMART buyer data, role-word senders, blank segment, no empty leads.
The two IndiaMART texts are real mails from the Mac copy of live (15-Nov), names as they came."""

from sk_app.lead_mail_rules import has_contact, parse_indiamart, pick_text, segment_or_none, sender_name

IM1 = ("Enquiry for MS Portable Site Office Container from Ravi Kumar",
	"Business Enquiry for MS Portable Site Office Container Download App Hi Rishikesh, I received your company details from IndiaMART "
	"while searching for MS Portable Site Office Container. Below are the requirement details :Length:20 ftMaterial:Mild SteelBusiness "
	"Type:InstitutionalProbable Requirement Type:Business Use &nbsp;Call &nbsp;Chat Below are the Buyer details :Products of Interest:"
	"Sugarcane Bagasse,Soya Husk,Biomass BriquettesRequirements till now:12 &nbsp; &nbsp;RegardsRavi KumarDemo Agro Products, "
	"Pune - 412216, Maharashtra, IndiaMobile: +91-9876500012Email: ravi.kumar@example.com ✓ Need Help? Contact Us")
IM2 = ("Enquiry for MS Prefab Movable Container from MANOJ",
	"Business Enquiry for MS Prefab Movable Container Download App Hi Rishikesh, I received your company details from IndiaMART while "
	"searching for MS Prefab Movable Container. Below are the requirement details :Length:20 ftWidth:10 ftProbable Requirement Type:"
	"Business Use &nbsp;Call &nbsp;Chat Below are the Buyer details :Products of Interest:Shopping Baskets,Office Containers,Double Sided "
	"Display RackRequirements till now:6 &nbsp; &nbsp;RegardsMANOJJai hind, Pune - 412308, Maharashtra, IndiaMobile: +91-9876500013"
	"Email: manoj@example.com ✓ Need Help?")


def test_html_part_is_read_when_the_text_part_is_only_dear_user():
	assert pick_text("Dear User", IM1[1]) == IM1[1]
	assert pick_text("Dear Sir,\n\nAs per our telephonic discussion, complete RFQ for service of twin drill has been attached. Regards, Amit M - 9876500014",
		"<html>x</html>") .startswith("Dear Sir")


def test_indiamart_buyer_data_is_read():
	d = parse_indiamart(*IM1)
	assert d["first_name"] == "Ravi Kumar" and d["mobile_no"] == "9876500012" and d["email"] == "ravi.kumar@example.com"
	assert d["organization"] == "Demo Agro Products" and d["city"] == "Pune"
	assert d["requirement"].startswith("MS Portable Site Office Container · Length:20 ft")
	d = parse_indiamart(*IM2)
	assert d["first_name"] == "MANOJ" and d["organization"] == "Jai hind" and d["mobile_no"] == "9876500013" and d["city"] == "Pune"


def test_role_word_sender_is_not_a_person_company_comes_from_the_domain():
	assert sender_name("Purchase", "purchase@gurudattaforging.com") == (None, "Gurudattaforging")
	assert sender_name("Amit Chakraborty", "amit.chakraborty@jsw.in") == ("Amit Chakraborty", "Jsw")
	assert sender_name("Amit Chakraborty", "amit.chakraborty@jsw.in", "JSW Steel") == ("Amit Chakraborty", "JSW Steel")
	assert sender_name("ramesh", "ramesh@gmail.com") == ("ramesh", None)
	assert sender_name("info", "info@gmail.com") == (None, None)


def test_segment_blank_until_the_product_is_known():
	assert segment_or_none("MS Portable Site Office Container") == "Standard Cabin (GI / ACP)"
	assert segment_or_none("need quotation for machine shifting of VMC") == "Machine Shifting"
	assert segment_or_none("Need quotation for reconditioning of floor boring machine") == "Machine Shifting"
	assert segment_or_none("Price please") is None and segment_or_none("") is None


def test_a_lead_needs_a_mobile_or_an_email():
	assert has_contact({"mobile_no": "+91 96575 39879"}) and has_contact({"email": "a@b.in"})
	assert not has_contact({"mobile_no": "", "email": None}) and not has_contact({"first_name": "Prashant"})


from sk_app.writers.lead_rules import owner_fields


def test_portal_lead_owner_by_source_sk_16_nov():
	assert owner_fields("IndiaMART", False) == ("lead_owner_indiamart", "lead_owner_digital", "lead_owner_cabin")
	assert owner_fields("JustDial", False) == ("lead_owner_justdial", "lead_owner_digital", "lead_owner_cabin")
	assert owner_fields("Email", False) == ("lead_owner_cabin",) and owner_fields(None, False) == ("lead_owner_cabin",)
	assert owner_fields("IndiaMART", True)[0] == "lead_owner_noncabin"  # machine shifting words win over the portal
