# SK 21-Nov: nightly alert mails to the person / team box concerned (settings-driven)
from sk_app.core.night_rules import area_of, parse_routes


def test_parse_routes():
	r = parse_routes("accounts: acc@example.com\ncabin_sales: cabin@example.com, boss@example.com\nbad line\nsummary:\nMachine Shifting: ms@example.com")
	assert r == {"accounts": ["acc@example.com"], "cabin_sales": ["cabin@example.com", "boss@example.com"], "machine_shifting": ["ms@example.com"]}


def test_area_of():
	assert area_of("Accounts") == "accounts"
	assert area_of("Sales", "Cabin") == "cabin_sales"
	assert area_of("Sales", "Non-Cabin") == "machine_shifting"
	assert area_of("Machine Shifting") == "machine_shifting"
	assert area_of("Purchase") == "purchase"
	assert area_of("AI") is None
