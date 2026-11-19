from sk_app.writers.lead_rules import SITE_CHECKS, site_checklist_missing, site_checklist_text

ALL_YES = {k: "Yes" for k, _en, _mr in SITE_CHECKS}


def test_all_answered_with_photo_passes():
	assert site_checklist_missing(ALL_YES, "/files/a.jpg") == []


def test_missing_point_and_photo_are_named():
	answers = dict(ALL_YES, crane=None)
	assert site_checklist_missing(answers, None) == ["Crane / hydra can reach the machine", "Site photo"]


def test_text_has_every_point_and_note():
	text = site_checklist_text(dict(ALL_YES, dismantle="No"), " gate 3 m wide ")
	assert text.splitlines()[0] == "Site checklist"
	assert "✘ Dismantling needed: No" in text and "✔ Machine weight and size known: Yes" in text
	assert text.endswith("Note: gate 3 m wide") and len(text.splitlines()) == 10
