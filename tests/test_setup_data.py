import sys
import types

sys.modules.setdefault("frappe", types.ModuleType("frappe"))

from sk_app.functions import FUNCTIONS, home_for  # noqa: E402
from sk_app.setup import SALES_PILOT  # noqa: E402

KPI_CODES = {"orders_value", "digital_orders_value", "cabins_qty", "leads_worked", "first_response_pct",
	"quotes_sent", "digital_leads", "lead_data_quality_pct", "dsi_count", "manual"}


def test_weights_add_to_100():
	for person in SALES_PILOT:
		assert sum(t[5] for t in person["targets"]) == 100, person["full_name"]


def test_confirmed_revenue_targets():
	revenue = {p["full_name"]: p["targets"][0][3] for p in SALES_PILOT}
	assert revenue == {"Rishikesh Mhase": 4500000, "Rahul Raju Jalnil": 1250000,
		"Swati  Mashakhetri": 1500000, "Pranali Mane": 1000000}


def test_kpi_codes_known_and_dsi_for_everyone():
	for person in SALES_PILOT:
		codes = [t[2] for t in person["targets"]]
		assert set(codes) <= KPI_CODES
		assert "dsi_count" in codes


def test_every_function_has_common_screens():
	for name, spec in FUNCTIONS.items():
		assert {"my_day", "my_kpi", "dsi", "problem"} <= set(spec["tiles"]), name
	assert home_for("Unknown")["tiles"]
