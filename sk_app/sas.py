"""TLC SAS (Teaching Learning Community self-assessment audit) in the app (SK 26-Oct): the SAS score next to My Score,
and the CEO's Leadership & Strategy page at the second level. SAS is the reference for each person's role, KRA / KPI
and activities; TLC asks for data as proof of each action, so every subject shows the month's evidence the app
recorded by itself. Scores are the self assessment of 04-Sep-2026; there is no assessor score yet (the "8%" for
Strategy in the sheet was a mistake). Each point is 0-4, a topic is out of 20 and a subject out of 120."""

import frappe
from frappe import _
from frappe.utils import getdate

from sk_app.logic import month_range

TARGET_PCT = 75  # target per subject
POINT_MAX = 4

SUBJECTS = [
	{"key": "strategy", "name": "Strategy", "owner": "Sunil (CEO) + core team", "functions": ["Management"], "topics": [
		("Mission statement", [
			("If Mission Statement is made and WHAT/WHOM/HOW is visible. Whether HOW is linked with PUV / CC", 4),
			("Is Mission Statement is displayed, Shared with every one in the organisation.", 4),
			("If the proactive sales efforts are aligned with mission statement with respect to customer segment & products .", 4),
			("If KPIS derived from Mission statement are reviewed with predefined frequency", 3),
			("Results from the focussed efforts on the products & customer segments are evident. The revenue from the focussed customers / products should be more than 70%", 3),
		]),
		("PUV", [
			("If PUV's are identified for each customer Segment", 4),
			("Has ranking of PUV'S is done and most Important PUV'S are identified", 3),
			("Actions taken in ABP to improve self score on most Important PUV's.", 2),
			("If Actions are monitored for improvement with predefined frequency.", 2),
			("If Increase in business or Customer satisfaction is increased due to action taken.", 2),
		]),
		("Core Competency (CC)", [
			("If CC is identified for self", 3),
			("Which CC is to be leveraged and Which CC needs to be developed is identified and team members are aware of the same.", 3),
			("Actions derived and initiated on CC in 5W1H concept", 2),
			("Actions are monitored with predefined frequency", 2),
			("Started getting results on the action taken on CC.", 2),
		]),
		("Vision", [
			("Presence of Company Vision and awarness to Team members", 4),
			("Vision mile stones are identified.", 4),
			("Actions are initiated towards vision milestone.", 3),
			("Actions are monitored for results with predefined frequency", 3),
			("Results for past actions.", 2),
		]),
		("Strategy formulation", [
			("Startegy is derived & can be justified based on different models taught. PMM is prepared", 4),
			("PUVs of startegic customer are derived from needs, wants , desires , unmet need exercise", 3),
			("CC is identified based on the PUV of strategic customer", 2),
			("Action plan is prepared to develop CC", 2),
			("Results fur the CC ddevelopment action plan is evident", 2),
		]),
		("Annual Business Plan (ABP)", [
			("Is ABP is prepared along with core team members / Every one is aware", 4),
			("ABP initiatives for all 5 levers are identified.", 3),
			("Action plan is derived for all 5 Levers in ABP and owners are assigned.", 2),
			("Initiatives are reviewed for results with predefined frequency", 2),
			("Results can be seen on initiatives.", 2),
		]),
	]},
	{"key": "sales_marketing", "name": "Sales & Marketing", "owner": "Rushi (Cabin), Aditya (Non-Cabin), Pranali (digital)", "functions": ["Sales", "Marketing", "Machine Shifting"], "topics": [
		("5Cs of Marketing", [
			("Has identified and documented. Linkage with strategy is evident", 2),
			("Shared with the Marketing team", 3),
			("Actions are derived from the analysis", 3),
			("Periodical review of the actions with predefined frequency", 3),
			("Progress on the planned actions are evident", 3),
		]),
		("STP", [
			("Is the target segment decided with some logic ( PUV & CC )?", 3),
			("Is Team focussed on Target segment. Is there any noise remaining?", 3),
			("Positioning statement is defined for target segment", 2),
			("Frequency of identifying TS defined and reviewed. Alignment in positioning statement and core competencies is evident", 2),
			("Benefits are evident ( share the success stories )", 3),
		]),
		("4Ps", [
			("Has identified the leveraging P for the current business situation", 3),
			("Has defined the actions for deployment", 3),
			("The actions are included as part of ABP", 2),
			("All actions related to 4 P are reviewed with predefined frequency", 3),
			("Benefits gained (success story/Victory)", 3),
		]),
		("SPIN & Value Proposition", [
			("Has made VP statement & SPIN questions are included in sales manual", 3),
			("Concept of value proposition is shared with the sales team", 2),
			("Sales team use SPIN in sales call and then offer VP", 3),
			("SPIN questions are added frequently.", 2),
			("Benefits gained at the sales call (story/victory sharing)", 3),
		]),
		("Sales force management", [
			("Is training of sales team done with a predefined frequency?", 2),
			("Is efficiency & effectivity of Sales team measured?", 3),
			("Sales pipeline is monitored & reviewed with a predefined frequency.", 3),
			("KRA / KPI for sales team is defined & reviewed.", 3),
			("Results from sales force management are evident", 3),
		]),
		("Negotiations & Digital marketing", [
			("Is your sales team trained on negotiation and know about RV, BATNA, Anchor price.", 2),
			("Benefits gained from applying negotiation techniques (case study, story/victory sharing)", 2),
			("Updated website exists", 3),
			("Digital marketing initiated ( SEO, AdWords, linked in , Facebook ads etc )", 3),
			("Progress is evident on Digital marketing initiatives", 2),
		]),
	]},
	{"key": "hr", "name": "HR", "owner": "Aarti", "functions": ["HR"], "topics": [
		("Employee engagement", [
			("Derived & implemented action plan based on BHMS", 4),
			("Conducted Q12 survey", 4),
			("Derived & Implemented action plan based on Q12 survey", 4),
			("Action plan is reviewed with predefined frequency", 4),
			("Results are evident in Q12 score", 3),
		]),
		("Organisation structure, Job Description & Training", [
			("Futuristic Organisation structure is prepared", 4),
			("Job responsibilities of each job profile are designed", 4),
			("Skill requirements are identified for each job profile", 3),
			("Skill gaps are assessed with predefined frequency", 2),
			("Skill gaps are reduced after training", 2),
		]),
		("Recruitment / Induction", [
			("Recruitment planning is done during ABP", 3),
			("Manpower requisition format exists & contains all the required details to source a suitable candidate", 2),
			("Interview questions bank exists to evaluate on skills , values , attitude", 2),
			("Induction training module & process exists", 3),
			("Attrition/ Termination of new inductees in the first year is less than 10%", 2),
		]),
		("KRA / KPI", [
			("KRA / KPI s for individual / team are defined", 4),
			("KRA s are aligned with the business goals", 4),
			("KRA / KPIs are communicated at the start of the year", 4),
			("KPI s are reviewed with a predefined frequency", 2),
			("Results of actions for lagging KRAs are evident", 2),
		]),
		("Salary structure / appraisal", [
			("Job profile wise salary structure is defined", 2),
			("A detailed salary breakup document is shared with each employee at the time of induction or increment", 4),
			("Appraisal criteria & process document is shared with all the employees at the start of the year", 3),
			("Appraisal process is reviewed with predefined frequency", 1),
			("Appraisal process is implemented as per the document", 1),
		]),
		("Rewards & Recognition", [
			("Reward-Recognition policies & hierarchy for the year are planned at the start of the year", 3),
			("Transparent calculation system is derived to decide winners for each reward", 2),
			("Reward-Recognition criteria are conveyed to all employees at the start of the year", 2),
			("Reward-Recognition schedule is followed without any break", 2),
			("Reward-Recognition policies are reviewed with predefined frequency", 0),
		]),
	]},
	{"key": "finance", "name": "Finance", "owner": "Shraddha", "functions": ["Accounts"], "topics": [
		("P&L, B/S", [
			("P & L & B / S is getting prepared before 7th of every month from software & by the accountant", 4),
			("Software stocks & physical stocks matches for raw material. Defined structure of FG & WIP stock valuation.", 3),
			("Action plan defined for ROTA improvement based on the ROTA mind map in 5W 1H format", 2),
			("Review of the action plan is taking place periodically", 3),
			("Results evident from the implementation of action plan on ROTA improvement.", 3),
		]),
		("Ratios", [
			("Understood the why & the trend desired for all the ratios from the MAR sheet", 2),
			("Monitoring 10 key ratios from the MAR sheet based on the type of business & the activity", 2),
			("Decided three key ratios for improvement based on CBI / KSF & prepared the action plan for the same", 2),
			("Review & monitoring of the action plan prepared to improve the three critical ratios", 2),
			("Results evident from the implementation actions related to critical ratio improvement", 2),
		]),
		("Cash Flow", [
			("Understanding of Cash flow statement with concepts of Operating, investing & financing activities", 2),
			("Prepared cash flow statement based on six months or yearly P & L & Balance sheet", 3),
			("Reviewed the cash flow statement for understanding - sources & use of funds / wrong usage of funds", 2),
			("started preparing planned inflow & outflow statements for at least next two months on a sliding window method.", 3),
			("Benefits achieved in improvement in cash management due to the above initiatives", 2),
		]),
		("BEP & OCC", [
			("Understanding of concept of OCC and calculating overall OCC for our own business", 3),
			("Deciding on initiatives to reduce the OCC with target & the review & monitoring of the same", 2),
			("Understanding of the overall contribution percentage & BEP sales of our business", 3),
			("Based on the proposed fixed cost, calculating BEP for the current year & strategy to achieve the same within 6-9 months of the financial year.", 2),
			("Result evident from the understanding of OCC & BEP (OCC is reduced or BEP is getting achieved early compared to the previous year", 2),
		]),
		("Contribution Analysis", [
			("Knows the concept of contribution calculation & its benefit / importance while accepting & rejecting orders", 2),
			("Calculated contribution percentage for product groups, customer segments or principals whichever is applicable to the business model.", 3),
			("For low contributing products prepared parato analysis for various costs for improvement of the contribution for manufacturing. For trading analysing low contribution product groups for sales force cost, absolute contribution, stocking & credit interest etc.", 2),
			("Taken strategic initiatives based on the findings of contribution analysis exercise", 2),
			("Result evident from the contribution analysis & improvement majors during the year", 2),
		]),
		("SFGR", [
			("Understood the concept of SFGR & why it needs to be worked out", 3),
			("Calculated own SFGR", 2),
			("Understood various factors which improves SFGR", 2),
			("Used SFGR in the ABP process to decide whether the planned growth will be self sustained or need bank advances", 2),
			("Result evident where SFGR is methodically used during ABP.", 1),
		]),
	]},
	{"key": "wcp", "name": "World Class Practices (WCP)", "owner": "Babasaheb (factory), Quality, Yogesh (stores), Samir (process / AI & ERP)", "functions": ["Production", "Quality", "Stores", "Subcontractor", "Purchase", "AI"], "topics": [
		("5S", [
			("Has given 5S training to all team members, Has conducted at least one hurricane activity, Red tag area is defined and use is visible", 3),
			("Plant layout defined & divided into zones and owners allocated, Individual Zone layouts displayed & updated, Schedule & frequency of 5S activity is defined & followed", 3),
			("Audit frequency is defined and audits are conducted regularly, 5S audit scores are displayed, 5S Scores are monitored by Top Management.", 2),
			("Recognition & Rewards are defined & awarded for 5S activity", 2),
			("Evidence of sustained 5S program is available", 2),
		]),
		("Process Management", [
			("Train your team on process management, Format for process writing is created and deployed", 2),
			("Has listed out all the different processes in the organization.", 2),
			("Documentation of important processes is done.", 2),
			("Monitoring & review of key process parameters is done with predefined frequency.", 2),
			("Internal audits are conducted to check effectiveness of processes and processes are improved from time to time.", 2),
		]),
		("Waste Management", [
			("Training on waste management is conducted with predefined schedule", 2),
			("Identified top 3 wastes through systematic approach", 3),
			("Defined action plan & teams to reduce the top 3 wastes", 3),
			("Actions are reviewed with a predefined frequency", 2),
			("Progress is evident for the waste reduction", 2),
		]),
		("Root Cause Analysis (RCA)", [
			("Training for RCA is given to the team, RCA format is created and available to the team.", 2),
			("Problem capturing mechanism is established & everybody is aware of the same.", 2),
			("RCAs are done for gaps other than product / customer complaint, Cross functional team is formed for the RCA.", 2),
			("Evidence of change in processes & policies based on RCA.", 2),
			("Mechanism to check recurrence of problem is established.", 2),
		]),
		("Kaizen", [
			("Training for kaizen is given to the team, Kaizen format is created and available to the team.", 3),
			("Done a Kaizen event of small size as an example.", 2),
			("Enablers for Kaizen - free time slots for executing kaizens, kaizen review teams etc have been provided, Rewards for Kaizen are declared, Good Kaizens are displayed & rewarded", 2),
			("Top Management is reviewing # of Kaizens and quality of kaizens regularly", 2),
			("Impact of Kaizens is quantified", 2),
		]),
		("7 QC Tools", [
			("Training on 7 QC tools is imparted with a predefined schedule.", 2),
			("Data of process indicators are recorded.", 3),
			("Do you prioritise the quality issues using data analysis with the help of 7 QC tools? Share a case study.", 2),
			("Monitoring of stastical data of quality issues with predefined frequency.", 2),
			("Reduction in no. of quality issues are evident.", 2),
		]),
	]},
]

# The actions that raise each subject's score (TLC SAS Alignment Rev 1, approved by SK 26-Oct), in the app's words.
ACTIONS = {
	"strategy": ["Monthly KPI review with the core team, saved as a dated meeting", "Mission and vision quiz in Training for everyone",
		"ABP: the 5 levers as ERPNext Projects / Tasks with owners and due dates"],
	"sales_marketing": ["Weekly sales lesson + quiz (SPIN, value, objections, negotiation)", "Monday pipeline review (Team meeting on the calendar)",
		"Every enquiry as a New Lead with its source; IndiaMART answered in 5 minutes"],
	"hr": ["Star of the month from My Score (transparent formula)", "Quarterly skill matrix from training results",
		"KPI review every month; attrition KPI"],
	"finance": ["P&L by the 7th and MAR by the 10th", "Monthly ratios: debtor, creditor and inventory days, GP %, NP %",
		"Friday cash statement; break-even and cash cycle in the MAR"],
	"wcp": ["5S every day at 3 pm, weekly zone audit with photo", "DSI = Kaizen with ₹ or minutes saved",
		"Root cause (5-Why) to close every NC; monthly Pareto of defects"],
}


def _pct(score: float, out_of: float) -> int:
	return round(score * 100 / out_of) if out_of else 0


def _topic(name: str, points: list, hide_salary: bool) -> dict | None:
	if hide_salary:  # SK 26-Oct: salary is confidential, so it is shown to the CEO only
		points = [p for p in points if "salary" not in p[0].lower()]
		name = name.replace("Salary structure / appraisal", "Appraisal")
	if not points:
		return None
	score = sum(s for _p, s in points)
	return {"topic": name, "score": score, "out_of": POINT_MAX * len(points), "pct": _pct(score, POINT_MAX * len(points)),
		"points": [{"text": p, "score": s, "step": i + 1} for i, (p, s) in enumerate(points)]}


def subject(key: str, hide_salary: bool = True) -> dict:
	s = next(x for x in SUBJECTS if x["key"] == key)
	topics = [t for t in (_topic(n, p, hide_salary) for n, p in s["topics"]) if t]
	score, out_of = sum(t["score"] for t in topics), sum(t["out_of"] for t in topics)
	return {"key": key, "name": s["name"], "owner": s["owner"], "functions": s["functions"], "self_score": score, "out_of": out_of,
		"self_pct": _pct(score, out_of), "assessor_pct": None, "target_pct": TARGET_PCT, "topics": topics, "actions": ACTIONS[key]}


def weakest(subj: dict, limit: int = 5) -> list[dict]:
	"""Points scored 0-2, lowest first; review (step 4) and results (step 5) first among equals: they need data."""
	rows = [{"subject": subj["name"], "topic": t["topic"], **p} for t in subj["topics"] for p in t["points"] if p["score"] <= 2]
	return sorted(rows, key=lambda r: (r["score"], -r["step"]))[:limit]


def for_functions(functions: list[str]) -> list[dict]:
	"""The SAS subjects a person's functions answer for (Management = all five)."""
	if "Management" in functions:
		return [subject(s["key"], hide_salary=False) for s in SUBJECTS]
	return [subject(s["key"]) for s in SUBJECTS if set(s["functions"]) & set(functions)]


def for_user(user: str) -> list[dict]:
	"""Short SAS line(s) for My Score: subject, self %, target, the person's weakest points."""
	from sk_app.logins import profile_functions

	return [{"key": s["key"], "name": s["name"], "self_pct": s["self_pct"], "assessor_pct": s["assessor_pct"],
		"target_pct": s["target_pct"], "weakest": weakest(s, 3), "actions": s["actions"]} for s in for_functions(profile_functions(user))]


def _count(doctype: str, filters: dict) -> int:
	try:
		return frappe.db.count(doctype, filters) if frappe.db.exists("DocType", doctype) else 0
	except Exception:
		return 0


def evidence(day=None) -> dict:
	"""This month's data the app recorded by itself, per subject (TLC: data for each action)."""
	start, end = month_range(getdate(day))
	dt = ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]
	period = ["between", [start, end]]
	lessons = _count("SK Training Done", {"completed_on": dt})
	return {
		"strategy": [("Tasks closed (ABP and others)", _count("Task", {"status": "Completed", "modified": dt})),
			("Meetings on the calendar", _count("Event", {"starts_on": dt}))],
		"sales_marketing": [("New leads", _count("CRM Lead", {"creation": dt})), ("Calls logged", _count("CRM Call Log", {"creation": dt})),
			("Quotations", _count("Quotation", {"transaction_date": period, "docstatus": ["<", 2]}))],
		"hr": [("Training lessons passed", lessons), ("Day Reports", _count("SK Day Report", {"date": period}))],
		"finance": [("Sales invoices", _count("Sales Invoice", {"posting_date": period, "docstatus": 1})),
			("Payments entered", _count("Payment Entry", {"posting_date": period, "docstatus": 1}))],
		"wcp": [("DSI / Kaizen entries", _count("SK DSI Entry", {"date": period})),
			("Quality inspections", _count("Quality Inspection", {"report_date": period})),
			("Job cards", _count("Job Card", {"creation": dt}))],
	}


def leadership(user: str, day=None) -> dict:
	"""The CEO's Leadership & Strategy page: every subject vs target, weakest points with owner and action, evidence."""
	from sk_app.logins import profile_functions

	if user != "Administrator" and "Management" not in profile_functions(user):
		frappe.throw(_("Only the CEO can open Leadership & Strategy"), frappe.PermissionError)
	subjects = for_functions(["Management"])
	ev = evidence(day)
	score, out_of = sum(s["self_score"] for s in subjects), sum(s["out_of"] for s in subjects)
	return {"self_pct": _pct(score, out_of), "target_pct": TARGET_PCT, "assessor_pct": None, "level": "SLC-Basic",
		"assessed_on": "2026-09-04",
		"subjects": [{**s, "weakest": weakest(s), "evidence": [{"label": k, "value": v} for k, v in ev[s["key"]]]} for s in subjects]}
