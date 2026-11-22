from sk_app.core.night_rules import parse_routes, with_default_routes


def test_default_routes_sk_21_nov():
	r = parse_routes(with_default_routes(""))
	assert r["purchase"] == ["prod@skind.tech"] and r["stores"] == ["prod@skind.tech"] and r["accounts"] == ["acc@skind.tech"]
	kept = parse_routes(with_default_routes("purchase: buyer@skind.tech"))
	assert kept["purchase"] == ["buyer@skind.tech"] and kept["stores"] == ["prod@skind.tech"]  # a line SK set stays
	assert with_default_routes(with_default_routes("")) == with_default_routes("")
