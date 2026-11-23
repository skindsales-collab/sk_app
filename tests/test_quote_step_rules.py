from sk_app.quote_step_rules import DRAWING_FIRST, QUALIFY_FIRST_QUOTE, may_qualify, quote_problem


def test_steps_in_order_sk_21_nov():
	assert not may_qualify(0) and may_qualify(1)
	assert quote_problem("Cabin", None, False) == QUALIFY_FIRST_QUOTE
	for status in ("Not Required", "Sent to Design", "In Design", "Drawing Sent", "Revision Requested", "On Hold", None):
		assert quote_problem("Cabin", status, True) == DRAWING_FIRST, status
	assert quote_problem("Cabin", "Drawing Approved", True) is None
	assert quote_problem("Cabin", "BOM & Quote Sent", True) is None
	assert quote_problem("Non-Cabin", None, True) is None  # machine shifting: no drawing step


def test_attached_pdf_is_not_the_quote():
	from sk_app.quote_step_rules import ATTACHED_NOT_QUOTE, CABIN_SCREEN, scope_problem

	assert scope_problem([{"item_code": "SK-CABIN", "description": "As per the attached quotation: Cabin52_Curesense.pdf"}], False) == ATTACHED_NOT_QUOTE
	assert scope_problem([{"item_code": "SK-JOB", "item_name": "Job / service (as per quotation)", "description": ""}], False) == ATTACHED_NOT_QUOTE
	assert scope_problem([{"item_code": "SK-JOB", "description": "<p>As per&nbsp;enclosed offer</p>"}], False) == ATTACHED_NOT_QUOTE
	assert scope_problem([{"item_code": "SK-CABIN", "description": "Office cabin 20x10"}], False) == CABIN_SCREEN
	# made in the cabin quote screen (specification prints from the request) or a full hand-written specification: fine
	assert scope_problem([{"item_code": "SK-CABIN", "description": "Office cabin 20'x10'x8'-6\" (L x W x H), as per specification below"}], True) is None
	assert scope_problem([{"item_code": "SK-CABIN", "description": "Office cabin 20x10: GI frame, 0.9 mm corrugated sheet walls, "
		"18 mm cement fibre board floor, 2 windows, 1 door, LED lights"}], False) is None
	assert scope_problem([{"item_code": "SK-JOB", "description": "Shifting of 3 CNC machines from Chakan to Talegaon incl. crane"}], False) is None


def test_lead_never_back_to_new():
	from sk_app.quote_step_rules import back_to_new

	assert back_to_new("Qualified", "New") and back_to_new("Contacted", "New")
	assert not back_to_new("New", "New") and not back_to_new(None, "New") and not back_to_new("Qualified", "Junk Lead")
