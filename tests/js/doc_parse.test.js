// Run: node --test tests/js   (SK 20-Nov free camera reading of PO and bill photos)
const test = require("node:test");
const assert = require("node:assert");
const { parseDoc, isoDate } = require("../../sk_app/public/js/card_parse.js");

test("dates in the shapes Indian POs and bills use", () => {
	assert.strictEqual(isoDate("12/11/2026"), "2026-11-12");
	assert.strictEqual(isoDate("05-03-26"), "2026-03-05");
	assert.strictEqual(isoDate("7 Nov 2026"), "2026-11-07");
	assert.strictEqual(isoDate("2026-12-01"), "2026-12-01");
	assert.strictEqual(isoDate("no date here"), "");
});

test("customer PO: number, PO date, delivery date", () => {
	const r = parseDoc(`DEMO BEARINGS INDIA PVT LTD
PURCHASE ORDER
PO No.: 4500123456          PO Date: 18/11/2026
Vendor: SK Ind Tech Solutions Pvt Ltd
1 Portable office cabin 20x10 1 Nos 285000.00
Delivery Date: 15-12-2026`, "po");
	assert.deepStrictEqual(r, { po_no: "4500123456", po_date: "2026-11-18", delivery_date: "2026-12-15" });
});

test("PO number on the next line", () => {
	const r = parseDoc(`Order No
DBI/PO/2026/0912
Dated 3 Dec 2026`, "po");
	assert.strictEqual(r.po_no, "DBI/PO/2026/0912");
	assert.strictEqual(r.po_date, "2026-12-03");
});

test("bill: total amount, date, party", () => {
	const r = parseDoc(`Shree Ganesh Hardware Traders
TAX INVOICE
Invoice Date: 19/11/2026
Bolts M12 50 Nos 1,250.00
Paint 20 L 4,800.00
Grand Total Rs. 7,139.00`, "bill");
	assert.strictEqual(r.amount, "7139");
	assert.strictEqual(r.date, "2026-11-19");
	assert.strictEqual(r.paid_to, "Shree Ganesh Hardware Traders");
});

test("nothing readable gives empty fields, never a guess", () => {
	assert.deepStrictEqual(parseDoc("blurry", "po"), { po_no: "", po_date: "", delivery_date: "" });
});
