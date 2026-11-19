"""PR H (SK 16-Nov KF-05549): only PDFs and photos on a customer-facing record; costing stays internal; no cabin number."""

from sk_app.file_rules import allowed_on, customer_file_name


def test_only_pdf_and_photos_on_a_deal():
	assert allowed_on("CRM Deal", "Godrej quote rev1.pdf") == (True, None)
	assert allowed_on("CRM Deal", "site photo.jpg") == (True, None)
	ok, why = allowed_on("CRM Deal", "Cabin 53 BOM costing.xlsx")
	assert not ok and "costing Excel stays on the internal Project" in why
	ok, why = allowed_on("Quotation", "costing sheet.pdf")
	assert not ok and "looks internal" in why
	assert allowed_on("Project", "Cabin 53 BOM costing.xlsx") == (True, None)
	assert allowed_on("Sales Invoice", "invoice.docx")[0] is False


def test_customer_file_name_drops_the_cabin_number():
	assert customer_file_name("Cabin 53 Godrej quote.pdf") == "Godrej quote.pdf"
	assert customer_file_name("CAB-053_Godrej_Elaris_drawing_R1.pdf") == "Godrej_Elaris_drawing_R1.pdf"
	assert customer_file_name("C53-office-cabin-20x10.pdf") == "office-cabin-20x10.pdf"
	assert customer_file_name("Godrej Properties 2026-11-16 quote.pdf") == "Godrej Properties 2026-11-16 quote.pdf"
	assert customer_file_name("cabin 7.pdf") == "Document.pdf"


from sk_app.file_rules import is_quote_file


def test_only_a_pdf_is_the_quote_file_sk_16_nov():
	assert is_quote_file("Godrej Quotation R1.pdf") and is_quote_file("QUOTE_rev2.PDF")
	assert not is_quote_file("Cabin53_BOM_Costing_Quote_Rev0.xlsx") and not is_quote_file("drawing.pdf") and not is_quote_file(None)
