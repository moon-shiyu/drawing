"""Tests for the minimap overlay rectangle computation.

These tests verify the pure calculation logic without any GTK dependency.
Run with:  python -m pytest tests/test_minimap_rect.py
    or:    python -m unittest tests/test_minimap_rect.py
"""

import math
import os
import sys
import unittest

# Allow importing the utility module directly without triggering the
# GTK-dependent package. The utility file has zero external imports
# beyond the standard library (math).
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_UTILITIES_DIR = os.path.join(_TEST_DIR, '..', 'src', 'utilities')
sys.path.insert(0, _UTILITIES_DIR)

from utilities_minimap import compute_minimap_rect


class TestComputeMinimapRect(unittest.TestCase):
	"""Test suite for compute_minimap_rect()."""

	# ------------------------------------------------------------------ #
	# Helper to reduce boilerplate
	# ------------------------------------------------------------------ #
	def _compute(self, scroll_x, scroll_y, zoom, img_w, img_h,
	             wid_w, wid_h, mini_w, mini_h):
		return compute_minimap_rect(
			scroll_x, scroll_y, zoom,
			img_w, img_h, wid_w, wid_h,
			mini_w, mini_h,
		)

	def _assert_within_bounds(self, rect, mini_w, mini_h):
		x, y, w, h, _ = rect
		self.assertGreaterEqual(x, 0, "mini_x must be >= 0")
		self.assertGreaterEqual(y, 0, "mini_y must be >= 0")
		self.assertGreater(w, 0, "mini_width must be > 0")
		self.assertGreater(h, 0, "mini_height must be > 0")
		self.assertLessEqual(x + w, mini_w,
			"Right edge (%d+%d=%d) exceeds minimap width (%d)" % (x, w, x+w, mini_w))
		self.assertLessEqual(y + h, mini_h,
			"Bottom edge (%d+%d=%d) exceeds minimap height (%d)" % (y, h, y+h, mini_h))

	# ================================================================== #
	# 1. Normal zoom (100%)
	# ================================================================== #
	def test_normal_zoom_100_percent(self):
		"""Standard case: 1000x800 image, 800x600 widget, zoom 1.0."""
		rect = self._compute(
			scroll_x=100, scroll_y=50, zoom=1.0,
			img_w=1000, img_h=800,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=240,
		)
		x, y, w, h, lw = rect

		# size_ratio = 300/1000 = 0.3
		# mini_x = int(100 * 0.3) = 30
		# mini_y = int(50 * 0.3) = 15
		# visible = 800x600 (all within image)
		# mini_width = ceil(800 * 0.3) = 240
		# mini_height = ceil(600 * 0.3) = 180
		self.assertEqual(x, 30)
		self.assertEqual(y, 15)
		self.assertEqual(w, 240)
		self.assertEqual(h, 180)
		self.assertEqual(lw, 1)  # Rectangle is large, thin line
		self._assert_within_bounds(rect, 300, 240)

	# ================================================================== #
	# 2. High zoom (2000%) -- minimum size enforcement
	# ================================================================== #
	def test_high_zoom_2000_percent(self):
		"""At 2000% zoom on a large image, rect must stay visible."""
		rect = self._compute(
			scroll_x=2000, scroll_y=2000, zoom=20.0,
			img_w=5000, img_h=5000,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=300,
		)
		x, y, w, h, lw = rect

		# size_ratio = 300/5000 = 0.06
		# visible = 800/20=40, 600/20=30 (both < image, no clamping)
		# mini_x = int(2000 * 0.06) = 120
		# mini_y = int(2000 * 0.06) = 120
		# raw mini_width = ceil(40 * 0.06) = ceil(2.4) = 3
		# raw mini_height = ceil(30 * 0.06) = ceil(1.8) = 2 -> bumped to 3
		self.assertEqual(x, 120)
		self.assertEqual(y, 120)
		self.assertGreaterEqual(w, 3)  # Minimum enforced
		self.assertGreaterEqual(h, 3)  # Minimum enforced (was 2, bumped)
		self.assertEqual(lw, 2)  # Small rect -> thick line
		self._assert_within_bounds(rect, 300, 300)

	def test_extreme_zoom_10000px_image(self):
		"""Extreme case: 10000x10000 image at 2000% zoom."""
		rect = self._compute(
			scroll_x=4000, scroll_y=4000, zoom=20.0,
			img_w=10000, img_h=10000,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=300,
		)
		x, y, w, h, lw = rect

		# size_ratio = 300/10000 = 0.03
		# raw mini_width = ceil(40 * 0.03) = ceil(1.2) = 2 -> bumped to 3
		# raw mini_height = ceil(30 * 0.03) = ceil(0.9) = 1 -> bumped to 3
		self.assertGreaterEqual(w, 3)
		self.assertGreaterEqual(h, 3)
		self.assertEqual(lw, 2)
		self._assert_within_bounds(rect, 300, 300)

	# ================================================================== #
	# 3. Small image -- clamping
	# ================================================================== #
	def test_small_image_overlay_still_drawn(self):
		"""10x10 image where overlay is forced (caller overrides need check)."""
		rect = self._compute(
			scroll_x=0, scroll_y=0, zoom=1.0,
			img_w=10, img_h=10,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=300,
		)
		x, y, w, h, lw = rect

		# visible = 800x600 -> clamped to 10x10
		# size_ratio = 300/10 = 30
		# mini_width = ceil(10 * 30) = 300
		# mini_height = ceil(10 * 30) = 300
		self.assertEqual(x, 0)
		self.assertEqual(y, 0)
		self.assertEqual(w, 300)
		self.assertEqual(h, 300)
		self._assert_within_bounds(rect, 300, 300)

	def test_small_image_high_zoom(self):
		"""10x10 image at 2000% zoom -- both clamping and minimum."""
		rect = self._compute(
			scroll_x=0, scroll_y=0, zoom=20.0,
			img_w=10, img_h=10,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=300,
		)
		x, y, w, h, lw = rect

		# visible = 40x30 -> clamped to 10x10
		# size_ratio = 30
		# mini_width = ceil(10 * 30) = 300
		# mini_height = ceil(10 * 30) = 300
		self.assertEqual(w, 300)
		self.assertEqual(h, 300)
		self.assertEqual(lw, 1)  # Large rect, thin line
		self._assert_within_bounds(rect, 300, 300)

	# ================================================================== #
	# 4. Scroll at maximum position
	# ================================================================== #
	def test_scroll_at_maximum(self):
		"""Scroll at max: rect right/bottom edges touch minimap edges."""
		# max_scroll_x = 1000 - 800 = 200
		# max_scroll_y = 800 - 600 = 200
		rect = self._compute(
			scroll_x=200, scroll_y=200, zoom=1.0,
			img_w=1000, img_h=800,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=240,
		)
		x, y, w, h, lw = rect

		# size_ratio = 0.3
		# mini_x = int(200 * 0.3) = 60
		# mini_width = ceil(800 * 0.3) = 240
		# x + w = 60 + 240 = 300 = mini_w
		self.assertEqual(x, 60)
		self.assertEqual(y, 60)
		self.assertEqual(x + w, 300)
		self.assertEqual(y + h, 240)
		self._assert_within_bounds(rect, 300, 240)

	# ================================================================== #
	# 5. Widget larger than image (zoom < 100%) -- the overflow bug
	# ================================================================== #
	def test_widget_larger_than_image(self):
		"""Widget exceeds image on one axis -- the actual overflow bug."""
		# Image is 1000x400, widget is 800x600
		# show_x = (800 < 1000) = True -> overlay IS drawn
		# show_y = (600 < 400) = False -> but overlay drawn anyway
		# visible_height = 600 > image_height 400 -> must clamp
		rect = self._compute(
			scroll_x=100, scroll_y=0, zoom=1.0,
			img_w=1000, img_h=400,
			wid_w=800, wid_h=600,
			mini_w=300, mini_h=120,
		)
		x, y, w, h, lw = rect

		# Without clamping: mini_height = ceil(600*0.3)+? = 180+ -> overflows
		# With clamping: visible_height = min(600, 400) = 400
		#   mini_height = ceil(400 * 0.3) = 120
		self.assertEqual(y + h, 120)  # Exactly fits
		self._assert_within_bounds(rect, 300, 120)

	def test_widget_much_larger_than_image(self):
		"""Extreme: widget 1920x1080, image 100x50, zoom 0.2."""
		rect = self._compute(
			scroll_x=0, scroll_y=0, zoom=0.2,
			img_w=100, img_h=50,
			wid_w=1920, wid_h=1080,
			mini_w=300, mini_h=150,
		)
		x, y, w, h, lw = rect

		# visible = 9600x5400 -> clamped to 100x50
		# size_ratio = 300/100 = 3.0
		# mini_width = ceil(100 * 3.0) = 300
		# mini_height = ceil(50 * 3.0) = 150
		self.assertEqual(w, 300)
		self.assertEqual(h, 150)
		self._assert_within_bounds(rect, 300, 150)

	# ================================================================== #
	# 6. Property-based: rect NEVER exceeds minimap bounds
	# ================================================================== #
	def test_rect_never_exceeds_bounds_parametric(self):
		"""For many parameter combinations, rect stays within minimap."""
		test_cases = [
			# (scroll_x, scroll_y, zoom, img_w, img_h,
			#  wid_w, wid_h, mini_w, mini_h)
			(0, 0, 0.2, 100, 100, 800, 600, 300, 300),
			(0, 0, 1.0, 1000, 800, 800, 600, 300, 240),
			(500, 400, 2.0, 1000, 800, 800, 600, 300, 240),
			(0, 0, 20.0, 5000, 5000, 800, 600, 300, 300),
			(2000, 2000, 20.0, 5000, 5000, 800, 600, 300, 300),
			(0, 0, 1.0, 10, 10, 800, 600, 300, 300),
			(0, 0, 20.0, 10, 10, 800, 600, 300, 300),
			(100, 0, 1.0, 1000, 400, 800, 600, 300, 120),
			(0, 0, 0.5, 200, 150, 800, 600, 300, 225),
			(999, 799, 1.0, 1000, 800, 800, 600, 300, 240),
			(0, 0, 20.0, 10000, 10000, 800, 600, 300, 300),
			(0, 0, 1.0, 1, 1, 800, 600, 300, 300),
		]
		for params in test_cases:
			with self.subTest(params=params):
				mini_w, mini_h = params[7], params[8]
				rect = self._compute(*params)
				self._assert_within_bounds(rect, mini_w, mini_h)

	# ================================================================== #
	# 7. Line width behavior
	# ================================================================== #
	def test_line_width_normal(self):
		"""Large rect at normal zoom -> line_width = 1."""
		rect = self._compute(0, 0, 1.0, 1000, 800, 800, 600, 300, 240)
		self.assertEqual(rect[4], 1)

	def test_line_width_thick_at_high_zoom(self):
		"""Small rect at high zoom -> line_width = 2."""
		rect = self._compute(0, 0, 20.0, 5000, 5000, 800, 600, 300, 300)
		self.assertEqual(rect[4], 2)

	# ================================================================== #
	# 8. Precision: ceil vs int()+2
	# ================================================================== #
	def test_ceil_more_precise_than_int_plus_2(self):
		"""Verify math.ceil does not overshoot like the old int()+2."""
		rect = self._compute(0, 0, 1.0, 1001, 1001, 801, 601, 300, 300)
		x, y, w, h, lw = rect

		# size_ratio = 300/1001 = 0.299700
		# visible = 801, 601
		# exact width = 801 * 0.299700 = 240.06
		# ceil(240.06) = 241
		# old: int(240.06) + 2 = 242 (overshoot)
		self.assertEqual(w, 241)
		# exact height = 601 * 0.299700 = 180.12
		# ceil(180.12) = 181
		self.assertEqual(h, 181)

	# ================================================================== #
	# 9. Edge cases
	# ================================================================== #
	def test_zero_scroll(self):
		"""Scroll at origin."""
		rect = self._compute(0, 0, 1.0, 1000, 800, 800, 600, 300, 240)
		self.assertEqual(rect[0], 0)
		self.assertEqual(rect[1], 0)

	def test_1x1_image(self):
		"""Degenerate: 1x1 pixel image."""
		rect = self._compute(0, 0, 1.0, 1, 1, 800, 600, 300, 300)
		x, y, w, h, lw = rect
		# visible = 800x600 -> clamped to 1x1
		# size_ratio = 300
		# mini_width = ceil(1 * 300) = 300
		self.assertEqual(w, 300)
		self.assertEqual(h, 300)
		self._assert_within_bounds(rect, 300, 300)

	def test_scroll_beyond_image(self):
		"""Defensive: scroll_x exceeds image width."""
		rect = self._compute(5000, 5000, 1.0, 1000, 800, 800, 600, 300, 240)
		x, y, w, h, lw = rect
		# mini_x = int(5000 * 0.3) = 1500 -> clamped to 299
		# mini_width = 240 -> clamped to 300-299 = 1
		self.assertLessEqual(x, 299)
		self._assert_within_bounds(rect, 300, 240)


if __name__ == '__main__':
	unittest.main()
