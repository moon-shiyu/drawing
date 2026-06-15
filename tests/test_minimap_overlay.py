"""Isolated unit tests for minimap overlay boundary-box computation.

These tests exercise compute_minimap_overlay_rect without requiring
GTK, cairo, or any GUI dependencies. The function and constant are
extracted from src/image.py via AST parsing, so no imports of the
full module (with its GTK/cairo dependencies) are needed.
"""
import ast
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Extract only the pure-math function and constant from image.py using AST,
# avoiding any GTK/cairo imports entirely.
# ---------------------------------------------------------------------------
_SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
_IMAGE_SRC = (_SRC_DIR / 'image.py').read_text(encoding='utf-8')

_namespace = {}
_tree = ast.parse(_IMAGE_SRC, filename='image.py')
_wanted = {'compute_minimap_overlay_rect', 'MINIMAP_MIN_VIEWPORT_SIZE'}
_nodes = [n for n in _tree.body
          if isinstance(n, (ast.FunctionDef, ast.Assign))
          and (getattr(n, 'name', None) in _wanted
               or any(getattr(t, 'id', None) in _wanted
                      for t in getattr(n, 'targets', [])))]
_extract = ast.Module(body=_nodes, type_ignores=[])
ast.fix_missing_locations(_extract)
exec(compile(_extract, 'image.py', 'exec'), _namespace)

compute_minimap_overlay_rect = _namespace['compute_minimap_overlay_rect']
MINIMAP_MIN_VIEWPORT_SIZE = _namespace['MINIMAP_MIN_VIEWPORT_SIZE']


class TestMinimapOverlayRect(unittest.TestCase):
    """Test the pure computation of minimap viewport rectangles."""

    def test_normal_case(self):
        """Basic scenario: viewport rect fits well within minimap."""
        # Image: 1000x800, minimap: 200x160, zoom shows 500x400 visible area
        # size_ratio = 200/1000 = 0.2
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=100, scroll_y=50,
            visible_width=500, visible_height=400,
            size_ratio=0.2,
            mini_pix_width=200, mini_pix_height=160
        )
        # Expected: x=20, y=10, w=102, h=82 (500*0.2+2, 400*0.2+2)
        self.assertEqual(x, 20)
        self.assertEqual(y, 10)
        self.assertEqual(w, 102)
        self.assertEqual(h, 82)

    def test_minimum_size_enforced(self):
        """At extreme zoom, the viewport rect should not shrink below MIN."""
        # Image: 2000x2000, minimap: 200x200, zoom=20x so visible=50x50
        # size_ratio = 0.1, raw_w = 50*0.1+2 = 7, raw_h = 7
        # But if visible is only 10x10: raw_w = 10*0.1+2 = 3 < MIN
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=500, scroll_y=500,
            visible_width=10, visible_height=10,
            size_ratio=0.1,
            mini_pix_width=200, mini_pix_height=200
        )
        self.assertGreaterEqual(w, MINIMAP_MIN_VIEWPORT_SIZE)
        self.assertGreaterEqual(h, MINIMAP_MIN_VIEWPORT_SIZE)

    def test_clamp_no_overflow_right(self):
        """Viewport rect must not exceed right/bottom edge of minimap."""
        # Scroll far right on a 1000px image, minimap 200px wide
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=950, scroll_y=950,
            visible_width=100, visible_height=100,
            size_ratio=0.2,
            mini_pix_width=200, mini_pix_height=200
        )
        self.assertLessEqual(x + w, 200)
        self.assertLessEqual(y + h, 200)

    def test_clamp_no_negative_position(self):
        """Viewport rect position must never be negative."""
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=-50, scroll_y=-30,
            visible_width=200, visible_height=200,
            size_ratio=0.5,
            mini_pix_width=100, mini_pix_height=100
        )
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_very_small_minimap(self):
        """Even if the minimap is smaller than MINIMAP_MIN_VIEWPORT_SIZE,
        the rect should be clamped to fit."""
        # Minimap only 4x4 pixels (smaller than MIN=6)
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=0, scroll_y=0,
            visible_width=10, visible_height=10,
            size_ratio=0.5,
            mini_pix_width=4, mini_pix_height=4
        )
        # Width/height should be clamped to the minimap size
        self.assertLessEqual(w, 4)
        self.assertLessEqual(h, 4)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_extreme_zoom_large_image(self):
        """Simulating 2000% zoom on a 4000x3000 image."""
        # minimap: 200x150, size_ratio = 200/4000 = 0.05
        # At 2000% zoom, widget 800x600 -> visible = 800/20=40, 600/20=30
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=2000, scroll_y=1500,
            visible_width=40, visible_height=30,
            size_ratio=0.05,
            mini_pix_width=200, mini_pix_height=150
        )
        # raw_w = 40*0.05+2 = 4, forced to MIN=6
        # raw_h = 30*0.05+2 = 3.5, forced to MIN=6
        self.assertGreaterEqual(w, MINIMAP_MIN_VIEWPORT_SIZE)
        self.assertGreaterEqual(h, MINIMAP_MIN_VIEWPORT_SIZE)
        # Must stay within minimap bounds
        self.assertLessEqual(x + w, 200)
        self.assertLessEqual(y + h, 150)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_zero_scroll(self):
        """At scroll origin, position should be (0, 0)."""
        x, y, w, h = compute_minimap_overlay_rect(
            scroll_x=0, scroll_y=0,
            visible_width=500, visible_height=400,
            size_ratio=0.2,
            mini_pix_width=200, mini_pix_height=160
        )
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

    def test_return_type_is_int_tuple(self):
        """All returned values must be integers for pixel drawing."""
        result = compute_minimap_overlay_rect(
            scroll_x=123, scroll_y=456,
            visible_width=300, visible_height=200,
            size_ratio=0.15,
            mini_pix_width=180, mini_pix_height=120
        )
        self.assertEqual(len(result), 4)
        for val in result:
            self.assertIsInstance(val, int)


if __name__ == '__main__':
    unittest.main()
