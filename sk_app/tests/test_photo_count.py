"""Photo Count (SK 28-Oct): tiling, merging pieces seen twice in tile overlaps, recount rule, weight to pieces.
Claude is replaced by a stand-in that 'sees' a known grid of pieces, so the counting maths is checked exactly."""

import io
import json
import unittest
from unittest.mock import patch

from sk_app import photo_count as pc


def _photo(w=1600, h=1200) -> bytes:
	from PIL import Image

	buf = io.BytesIO()
	Image.new("RGB", (w, h), (120, 120, 120)).save(buf, "JPEG")
	return buf.getvalue()


class FakeClaude:
	"""Sees `pieces` (x, y in photo pixels). The survey answers `estimate`; each tile returns the pieces inside it."""

	def __init__(self, pieces, size, estimate, kind="bundle_ends", countable=True):
		self.pieces, self.size, self.estimate, self.kind, self.countable = pieces, size, estimate, kind, countable
		self.boxes = []

	def ask(self, client, model, system, schema, image_b64, text):
		if schema is pc.SURVEY_SCHEMA:
			return {"kind": self.kind, "material": "GI C-channel", "estimate": self.estimate, "countable": self.countable, "advice": ""}
		box = self.boxes.pop(0)
		left, top, right, bottom = box
		pts = [{"x": round((x - left) / (right - left) * 1000), "y": round((y - top) / (bottom - top) * 1000)}
			for x, y in self.pieces if left <= x <= right and top <= y <= bottom]
		return {"points": pts}


def run(pieces, estimate, size=(1600, 1200), **kw):
	fake = FakeClaude(pieces, size, estimate, **kw)
	n = pc.grid_for(estimate, kw.get("kind", "bundle_ends"))
	fake.boxes = pc.tiles(size[0], size[1], n)
	with patch.object(pc, "_ask", side_effect=fake.ask), \
		patch("frappe.get_cached_doc", return_value=type("S", (), {"claude_model": "x"})()), \
		patch.object(pc.claude, "_api_key", return_value="k"), \
		patch("anthropic.Anthropic"), \
		patch.object(pc, "ThreadPoolExecutor") as pool:
		pool.return_value.__enter__.return_value.map = lambda f, boxes: [f(b) for b in boxes]
		return pc.count_image(_photo(*size))


def grid(cols, rows, w=1600, h=1200):
	return [((c + 0.5) * w / cols, (r + 0.5) * h / rows) for r in range(rows) for c in range(cols)]


class TestPhotoCount(unittest.TestCase):
	def test_tiles_cover_photo_and_overlap(self):
		boxes = pc.tiles(1600, 1200, 3)
		self.assertEqual(len(boxes), 9)
		self.assertEqual(boxes[0][:2], (0, 0))
		self.assertEqual(boxes[-1][2:], (1600, 1200))
		self.assertGreater(boxes[0][2], boxes[1][0])  # neighbours overlap

	def test_grid_grows_with_pieces(self):
		self.assertEqual(pc.grid_for(30, "bundle_ends"), 1)
		self.assertEqual(pc.grid_for(150, "bundle_ends"), 2)
		self.assertEqual(pc.grid_for(5000, "bundle_ends"), 4)
		self.assertEqual(pc.grid_for(500, "sheet_stack"), 1)

	def test_small_bundle_exact(self):
		res = run(grid(5, 4), estimate=20)
		self.assertEqual(res["count"], 20)
		self.assertEqual(res["confidence"], "high")
		self.assertEqual(len(res["points"]), 20)

	def test_big_bundle_pieces_in_overlaps_counted_once(self):
		pieces = grid(20, 15)  # 300 pieces → 3 x 3 tiles, many pieces sit in two or four tiles
		res = run(pieces, estimate=300)
		self.assertEqual(res["tiles"], 9)
		self.assertEqual(res["count"], 300)
		self.assertEqual(res["confidence"], "high")

	def test_counts_disagree_gives_medium(self):
		res = run(grid(10, 8), estimate=120)
		self.assertEqual(res["count"], 80)
		self.assertEqual(res["confidence"], "medium")

	def test_loose_pile_or_sheets_always_low(self):
		self.assertEqual(run(grid(5, 4), estimate=20, kind="loose_pile")["confidence"], "low")
		self.assertEqual(run(grid(5, 4), estimate=20, kind="sheet_stack")["confidence"], "low")

	def test_recount_rule_5_percent(self):
		self.assertFalse(pc.needs_recount(100, 104))
		self.assertTrue(pc.needs_recount(100, 106))
		self.assertFalse(pc.needs_recount(0, 7))

	def test_weight_to_pieces(self):
		self.assertEqual(pc.pieces_from_weight(98.5, 9.85), 10)

	def test_points_are_percent(self):
		res = run([(800, 600)], estimate=1)
		self.assertEqual(res["points"], [[50.0, 50.0]])


if __name__ == "__main__":
	unittest.main()
