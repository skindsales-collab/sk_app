from sk_app.writers.item_rules import norm, problems, same_name
from sk_app.writers.lead_rules import shape, problems as lead_problems


def test_item_norm_and_same_name():
	assert norm("GP Coil 0.5 mm") == norm("gp coil 0.5mm") == "gpcoil05mm"
	others = [("ITEM-1", "GP Coil 0.5 mm"), ("ITEM-2", "Bolt M8"), ("ITEM-3", "gp coil 0.5mm")]
	assert same_name("GP COIL 0.5MM", others, code="ITEM-1") == ["ITEM-3"]
	assert same_name("", others) == []


def test_item_problems():
	assert problems("X", "Bolt", "Hardware", "Nos", "7318", []) == []
	assert [k for k, _w in problems("X", "", None, None, None, ["Y"])] == [
		"item_no_name", "item_no_group", "item_no_uom", "item_no_hsn", "item_same_name"]


def test_lead_shape():
	d = shape({"first_name": " Ravi ", "organization": "", "mobile_no": "9876543210", "segment": "Cabin", "source": "IndiaMART",
		"owner": "a@x", "product": "x" * 200})
	assert d["first_name"] == "Ravi" and d["organization"] is None and len(d["sk_product"]) == 140
	assert lead_problems(d) == []
	assert shape({})["first_name"] == "Enquiry"
	assert "lead_first_name" in [k for k, _w in lead_problems(shape({"source": "GeM"}))]
