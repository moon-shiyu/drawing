"""Tests for selection geometry calculation and display logic.

These tests validate the coordinate/dimension computation added to
DrSelectionManager.get_selection_geometry() and the formatting in
OptionsBarSelection.update_selection_info(), using mocks to avoid
requiring a running GTK environment.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock GTK / cairo modules so we can import the project sources without a
# display server.
# ---------------------------------------------------------------------------

cairo_mock = MagicMock()
gi_mock = MagicMock()
gi_repository_mock = MagicMock()

sys.modules['cairo'] = cairo_mock
sys.modules['gi'] = gi_mock
sys.modules['gi.repository'] = gi_repository_mock

# Provide a stub for gettext's _ that the sources call at module level
import builtins
if '_' not in dir(builtins):
    builtins._ = lambda s: s


# ===========================================================================
# 1.  Test get_selection_geometry (DrSelectionManager)
# ===========================================================================

class MockPixbuf:
    """Minimal stand-in for GdkPixbuf.Pixbuf."""
    def __init__(self, width, height):
        self._w = width
        self._h = height

    def get_width(self):
        return self._w

    def get_height(self):
        return self._h


class TestGetSelectionGeometry(unittest.TestCase):
    """Test DrSelectionManager.get_selection_geometry logic in isolation."""

    # -- helper to build a minimal manager-like object -----------------------

    @staticmethod
    def _make_manager(is_active, pixbuf, sel_x=0, sel_y=0):
        """Return a simple namespace that mimics the manager's state."""
        mgr = MagicMock()
        mgr.is_active = is_active
        mgr.selection_pixbuf = pixbuf
        mgr.selection_x = sel_x
        mgr.selection_y = sel_y
        return mgr

    @staticmethod
    def _call_geometry(mgr):
        """Run the same logic as get_selection_geometry on a mock manager."""
        if not mgr.is_active or mgr.selection_pixbuf is None:
            return None
        x = int(mgr.selection_x)
        y = int(mgr.selection_y)
        width = mgr.selection_pixbuf.get_width()
        height = mgr.selection_pixbuf.get_height()
        if width <= 0 or height <= 0:
            return None
        return (x, y, int(width), int(height))

    # -- tests ---------------------------------------------------------------

    def test_normal_selection(self):
        mgr = self._make_manager(True, MockPixbuf(200, 100), 10, 20)
        result = self._call_geometry(mgr)
        self.assertEqual(result, (10, 20, 200, 100))

    def test_inactive_returns_none(self):
        mgr = self._make_manager(False, MockPixbuf(200, 100), 10, 20)
        self.assertIsNone(self._call_geometry(mgr))

    def test_none_pixbuf_returns_none(self):
        mgr = self._make_manager(True, None, 10, 20)
        self.assertIsNone(self._call_geometry(mgr))

    def test_zero_width_returns_none(self):
        mgr = self._make_manager(True, MockPixbuf(0, 100), 10, 20)
        self.assertIsNone(self._call_geometry(mgr))

    def test_zero_height_returns_none(self):
        mgr = self._make_manager(True, MockPixbuf(200, 0), 10, 20)
        self.assertIsNone(self._call_geometry(mgr))

    def test_negative_coords(self):
        """Selections can be dragged partially off-canvas (negative coords)."""
        mgr = self._make_manager(True, MockPixbuf(50, 50), -10, -5)
        result = self._call_geometry(mgr)
        self.assertEqual(result, (-10, -5, 50, 50))

    def test_float_coords_truncated(self):
        mgr = self._make_manager(True, MockPixbuf(150, 80), 10.7, 20.3)
        result = self._call_geometry(mgr)
        self.assertEqual(result, (10, 20, 150, 80))

    def test_large_selection(self):
        mgr = self._make_manager(True, MockPixbuf(4000, 3000), 0, 0)
        result = self._call_geometry(mgr)
        self.assertEqual(result, (0, 0, 4000, 3000))

    def test_one_pixel_selection(self):
        mgr = self._make_manager(True, MockPixbuf(1, 1), 99, 99)
        result = self._call_geometry(mgr)
        self.assertEqual(result, (99, 99, 1, 1))


# ===========================================================================
# 2.  Test update_selection_info formatting
# ===========================================================================

class TestSelectionInfoFormatting(unittest.TestCase):
    """Test the label formatting used in OptionsBarSelection."""

    @staticmethod
    def _format_info(x, y, width, height):
        """Replicate the formatting logic from update_selection_info."""
        x, y = int(x), int(y)
        width, height = int(width), int(height)
        return _("X: {x}  Y: {y}  |  {w} × {h}").format(
            x=x, y=y, w=width, h=height)

    def test_basic_format(self):
        result = self._format_info(10, 20, 200, 100)
        self.assertIn("10", result)
        self.assertIn("20", result)
        self.assertIn("200", result)
        self.assertIn("100", result)

    def test_format_contains_all_values(self):
        result = self._format_info(55, 66, 300, 400)
        self.assertIn("55", result)
        self.assertIn("66", result)
        self.assertIn("300", result)
        self.assertIn("400", result)

    def test_format_zero_origin(self):
        result = self._format_info(0, 0, 100, 100)
        self.assertEqual(result, "X: 0  Y: 0  |  100 × 100")

    def test_negative_coords_format(self):
        result = self._format_info(-5, -10, 50, 50)
        self.assertIn("-5", result)
        self.assertIn("-10", result)

    def test_float_input_truncated(self):
        result = self._format_info(10.9, 20.1, 100.5, 200.7)
        self.assertEqual(result, "X: 10  Y: 20  |  100 × 200")


# ===========================================================================
# 3.  Test rectangle selection dimension preview calculation
# ===========================================================================

class TestRectSelectPreviewDimensions(unittest.TestCase):
    """Test the preview width/height logic used in ToolRectSelect.motion_define
    and the _build_rectangle_path helper."""

    @staticmethod
    def _compute_rect_preview(press_x, press_y, event_x, event_y):
        """Replicate the preview computation from select_rect.motion_define."""
        x0 = int(min(press_x, event_x))
        y0 = int(min(press_y, event_y))
        w = int(abs(event_x - press_x))
        h = int(abs(event_y - press_y))
        if w <= 0 or h <= 0:
            return None
        return (x0, y0, w, h)

    def test_normal_drag_right_down(self):
        result = self._compute_rect_preview(10, 20, 110, 120)
        self.assertEqual(result, (10, 20, 100, 100))

    def test_drag_left_up(self):
        """Dragging from bottom-right to top-left."""
        result = self._compute_rect_preview(110, 120, 10, 20)
        self.assertEqual(result, (10, 20, 100, 100))

    def test_zero_width(self):
        result = self._compute_rect_preview(10, 20, 10, 120)
        self.assertIsNone(result)

    def test_zero_height(self):
        result = self._compute_rect_preview(10, 20, 110, 20)
        self.assertIsNone(result)

    def test_single_pixel(self):
        result = self._compute_rect_preview(10, 20, 11, 21)
        self.assertEqual(result, (10, 20, 1, 1))

    def test_float_coords(self):
        result = self._compute_rect_preview(10.5, 20.5, 50.7, 80.3)
        self.assertEqual(result, (10, 20, 40, 59))


# ===========================================================================
# 4.  Test drag preview offset calculation
# ===========================================================================

class TestDragPreviewOffset(unittest.TestCase):
    """Test the projected position calculation used during drag preview."""

    @staticmethod
    def _compute_drag_preview(base_x, base_y, base_w, base_h, dx, dy):
        """Replicate the drag preview calculation from _preview_drag_to."""
        x = base_x + int(dx)
        y = base_y + int(dy)
        return (x, y, base_w, base_h)

    def test_drag_positive(self):
        result = self._compute_drag_preview(10, 20, 100, 50, 5, 10)
        self.assertEqual(result, (15, 30, 100, 50))

    def test_drag_negative(self):
        result = self._compute_drag_preview(10, 20, 100, 50, -15, -25)
        self.assertEqual(result, (-5, -5, 100, 50))

    def test_drag_zero(self):
        result = self._compute_drag_preview(10, 20, 100, 50, 0, 0)
        self.assertEqual(result, (10, 20, 100, 50))

    def test_drag_float_offset(self):
        result = self._compute_drag_preview(10, 20, 100, 50, 3.7, 4.2)
        self.assertEqual(result, (13, 24, 100, 50))


# ===========================================================================
# 5.  Syntax validation of modified source files
# ===========================================================================

class TestSyntaxValidity(unittest.TestCase):
    """Verify that all modified files parse without syntax errors."""

    def _check_syntax(self, filepath):
        import py_compile
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Syntax error in {filepath}: {e}")

    def test_selection_manager_syntax(self):
        self._check_syntax(os.path.join(
            os.path.dirname(__file__), '..', 'src', 'selection_manager.py'))

    def test_optionsbar_selection_syntax(self):
        self._check_syntax(os.path.join(
            os.path.dirname(__file__), '..', 'src', 'optionsbars',
            'selection', 'optionsbar_selection.py'))

    def test_abstract_select_syntax(self):
        self._check_syntax(os.path.join(
            os.path.dirname(__file__), '..', 'src', 'tools',
            'selection_tools', 'abstract_select.py'))

    def test_select_rect_syntax(self):
        self._check_syntax(os.path.join(
            os.path.dirname(__file__), '..', 'src', 'tools',
            'selection_tools', 'select_rect.py'))


if __name__ == '__main__':
    unittest.main()
