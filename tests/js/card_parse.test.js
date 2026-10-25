// Run: node --test tests/js
const test = require("node:test");
const assert = require("node:assert");
const { parseCard } = require("../../sk_app/public/js/card_parse.js");

test("typical English card", () => {
	const r = parseCard(`PATIL ENGINEERING WORKS PVT. LTD.
Rajesh Patil
Purchase Manager
Plot No. 12, MIDC Bhosari, Pune 411026
Mob: +91 98220 12345 | Tel: 020-2712 3456
rajesh.patil@patileng.co.in
www.patileng.co.in`);
	assert.strictEqual(r.mobile_no, "9822012345");
	assert.strictEqual(r.email, "rajesh.patil@patileng.co.in");
	assert.strictEqual(r.first_name, "Rajesh Patil");
	assert.match(r.organization, /PATIL ENGINEERING WORKS/);
});

test("name below the role, number with 0 and dashes, OCR O for 0", () => {
	const r = parseCard(`Director
SUNIL KULKARNI
Kulkarni Infra Projects LLP
Cell 0-9881O-55443
sunil@kulkarniinfra.com`);
	assert.strictEqual(r.first_name, "Sunil Kulkarni");
	assert.strictEqual(r.mobile_no, "9881055443");
	assert.match(r.organization, /Kulkarni Infra Projects LLP/);
});

test("nothing readable gives empty fields, no crash", () => {
	const r = parseCard("~~ ## ..\n\n");
	assert.deepStrictEqual(r, { first_name: "", organization: "", mobile_no: "", email: "", requirement: "", source: "", segment: "", invoice: null });
});

test("two mobiles on one line takes the first mobile", () => {
	const r = parseCard("Amit Shah\nShah Traders\n9876543210 / 9123456780");
	assert.strictEqual(r.mobile_no, "9876543210");
	assert.strictEqual(r.first_name, "Amit Shah");
});

test("enquiry email from IndiaMART: labelled name, company, size and material go to requirement", () => {
	const r = parseCard(`IndiaMART Buy Lead
Buyer Name: Ramesh Jadhav
Company: Jadhav Constructions
Mobile: +91-98505 11223
Requirement: Portable site office cabin
Size 20 x 10 ft, 2 nos
Material: GI frame, PUF panel 50 mm, cement fiber board floor
Location: Chakan, Pune
Regards`);
	assert.strictEqual(r.first_name, "Ramesh Jadhav");
	assert.strictEqual(r.organization, "Jadhav Constructions");
	assert.strictEqual(r.mobile_no, "9850511223");
	assert.match(r.requirement, /20 x 10 ft, 2 nos/);
	assert.match(r.requirement, /PUF panel 50 mm/);
	assert.match(r.requirement, /Chakan/);
	assert.strictEqual(r.source, "indiamart");
	assert.strictEqual(r.segment, "cabin");
});

test("drawing title block and spec notes: sizes and specs, no name invented", () => {
	const r = parseCard(`SECURITY CABIN 8' x 6'
SPECIFICATION
1. Wall: 50 mm PUF panel
2. Roof: corrugated GI sheet 0.5 mm
3. Door: MS door 3' x 7'
HEIGHT 8'`);
	assert.match(r.requirement, /8' x 6'/);
	assert.match(r.requirement, /PUF panel/);
	assert.match(r.requirement, /Door: MS door/);
	assert.strictEqual(r.segment, "cabin");
	assert.strictEqual(r.mobile_no, "");
});

test("letter with sign-off name and machine shifting", () => {
	const r = parseCard(`Dear Sir,
We need shifting of 3 CNC machines from Bhosari to Chakan.
Please send quotation.
Thanks & Regards,
Prakash Deshmukh
Deshmukh Auto Components Pvt Ltd
9822334455`);
	assert.strictEqual(r.first_name, "Prakash Deshmukh");
	assert.match(r.organization, /Deshmukh Auto Components/);
	assert.match(r.requirement, /shifting of 3 CNC machines/);
	assert.strictEqual(r.segment, "shifting");
});

test("number at the end of a line is not joined with a number on the next line", () => {
	const r = parseCard("Prakash Deshmukh\nDeshmukh Auto Components Pvt Ltd\nMob: 98223 34455\n8\n6'");
	assert.strictEqual(r.mobile_no, "9822334455");
});

test("purchase invoice photo: number, date, GSTIN, total and item lines", () => {
	const r = parseCard(`TAX INVOICE
MAHALAXMI STEEL TRADERS
Shop 4, Bhosari MIDC, Pune 411026
GSTIN: 27AABCM1234F1Z5
Invoice No: MST/245/26-27   Date: 18/10/2026
Bill To: SK Ind Tech Solutions Pvt Ltd  GSTIN 27AAKCS5678P1ZQ
1 GI Square Pipe 40x40x1.6 mm 7306 120 nos 450.00 54,000.00
2 MS Angle 50x50x5 mm 7216 850 kg 62.00 52,700.00
CGST 9% 9,603.00
SGST 9% 9,603.00
Grand Total Rs. 1,25,906.00
Mob: 98220 99887`);
	assert.strictEqual(r.invoice.number, "MST/245/26-27");
	assert.strictEqual(r.invoice.date, "18/10/2026");
	assert.match(r.invoice.gstin, /27AABCM1234F1Z5/);
	assert.match(r.invoice.gstin, /27AAKCS5678P1ZQ/);
	assert.strictEqual(r.invoice.total, "125906.00");
	assert.strictEqual(r.invoice.items.length, 2);
	assert.match(r.requirement, /^Invoice · No MST\/245\/26-27 · Date 18\/10\/2026/);
	assert.match(r.requirement, /GI Square Pipe/);
	assert.match(r.organization, /MAHALAXMI STEEL TRADERS/);
	assert.strictEqual(r.mobile_no, "9822099887");
});
