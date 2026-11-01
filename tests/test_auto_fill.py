from sk_app.auto_fill import functions_from_role, guess_item_defaults, state_from_gstin


def test_state_from_gstin():
	assert state_from_gstin("27AAACS1234A1Z5") == "Maharashtra"
	assert state_from_gstin(" 29aaacs1234a1z5 ") == "Karnataka"
	assert state_from_gstin("27AAACS1234") is None
	assert state_from_gstin(None) is None
	assert state_from_gstin("99AAACS1234A1Z5") is None


def test_guess_item_defaults_from_similar_names():
	items = [("GP Sheet 0.8 mm", "Raw Material", "Kg"), ("GP Sheet 1.0 mm", "Raw Material", "Kg"),
		("MS Pipe 25 NB", "Raw Material", "Nos"), ("Paint Red Oxide", "Consumable", "Ltr"), ("Paint Enamel White", "Consumable", "Ltr")]
	assert guess_item_defaults("GP sheet 1.2 mm", items) == {"item_group": "Raw Material", "uom": "Kg"}
	assert guess_item_defaults("Enamel paint grey", items) == {"item_group": "Consumable", "uom": "Ltr"}
	assert guess_item_defaults("Door hinge", items) == {"item_group": None, "uom": None}


def test_functions_from_role():
	assert functions_from_role("Sales Executive") == ["Sales"]
	assert functions_from_role("Store Keeper", "Stores") == ["Stores"]
	assert functions_from_role("Electrician", "Production") == ["Production"]
	assert functions_from_role("HR & Purchase Executive") == ["Purchase", "HR"]
	assert functions_from_role("Sales Executive", allowed={"Stores"}) == []
	assert functions_from_role(None, None) == []
