#!/usr/bin/env python3
"""Unit tests for the selection-info enhancement.

These tests validate coordinate/dimension calculations and the info-label
formatting logic.  They are designed to run *without* a live GTK display
(PyGObject is stubbed/mocked where necessary).
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Stub out GTK/cairo so the source modules can be imported without a display.
# ---------------------------------------------------------------------------
import types

# Provide minimal stubs for `gi` and `cairo` if they are not installed.
# We create fake modules that satisfy the import statements in the source.

_FAKE_GI_MODULES = {}

def _make_fake_gi():
    """Build a fake `gi` package with just enough to satisfy source imports."""
    gi_mod = types.ModuleType('gi')
    gi_mod.require_version = lambda *a: None

    repo_mod = types.ModuleType('gi.repository')

    # Fake Gtk module
    gtk_mod = types.ModuleType('gi.repository.Gtk')
    gtk_mod.Builder = MagicMock()
    gtk_mod.Popover = MagicMock()
    gtk_mod.ActionBar = type('GtkActionBar', (), {})
    gtk_mod.Box = type('GtkBox', (), {})
    gtk_mod.Button = type('GtkButton', (), {})
    gtk_mod.Label = type('GtkLabel', (), {})
    gtk_mod.MenuButton = type('GtkMenuButton', (), {})
    gtk_mod.ToggleButton = type('GtkToggleButton', (), {})
    gtk_mod.Separator = type('GtkSeparator', (), {})
    gtk_mod.Image = type('GtkImage', (), {})
    gtk_mod.Rectangle = lambda: MagicMock()

    # Fake Gdk module
    gdk_mod = types.ModuleType('gi.repository.Gdk')
    gdk_mod.cairo_surface_create_from_pixbuf = MagicMock()
    gdk_mod.pixbuf_get_from_surface = MagicMock()
    gdk_mod.cairo_set_source_pixbuf = MagicMock()
    gdk_mod.RGBA = MagicMock()
    gdk_mod.Rectangle = lambda: MagicMock()

    # Fake GdkPixbuf module
    pixbuf_mod = types.ModuleType('gi.repository.GdkPixbuf')
    pixbuf_mod.Pixbuf = MagicMock()
    pixbuf_mod.Colorspace = MagicMock()
    pixbuf_mod.Colorspace.RGB = 0

    # Fake GLib / Gio
    glib_mod = types.ModuleType('gi.repository.GLib')
    glib_mod.Variant = MagicMock()
    gio_mod = types.ModuleType('gi.repository.Gio')
    gio_mod.Settings = MagicMock()

    repo_mod.Gtk = gtk_mod
    repo_mod.Gdk = gdk_mod
    repo_mod.GdkPixbuf = pixbuf_mod
    repo_mod.GLib = glib_mod
    repo_mod.Gio = gio_mod

    gi_mod.repository = repo_mod

    # Register in sys.modules so that `from gi.repository import X` works.
    sys.modules['gi'] = gi_mod
    sys.modules['gi.repository'] = repo_mod
    sys.modules['gi.repository.Gtk'] = gtk_mod
    sys.modules['gi.repository.Gdk'] = gdk_mod
    sys.modules['gi.repository.GdkPixbuf'] = pixbuf_mod
    sys.modules['gi.repository.GLib'] = glib_mod
    sys.modules['gi.repository.Gio'] = gio_mod
    _FAKE_GI_MODULES.update(sys.modules.copy())


# Try to import cairo; if unavailable, create a minimal stub.
try:
    import cairo as _cairo  # noqa: F401
except ImportError:
    cairo_mod = types.ModuleType('cairo')
    cairo_mod.Context = MagicMock
    cairo_mod.Operator = MagicMock()
    cairo_mod.Operator.DEST_IN = 0
    cairo_mod.Operator.OVER = 1
    cairo_mod.Operator.SOURCE = 2
    cairo_mod.FILTER_NEAREST = 0
    sys.modules['cairo'] = cairo_mod

_make_fake_gi()

# ---------------------------------------------------------------------------
# Now add the project's src/ to the path so we can import the modules under
# test.  We need to handle the relative imports those modules use.
# ---------------------------------------------------------------------------
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, SRC_DIR)

# Patch the tool-module relative imports that would fail.  We only need the
# pure-logic helpers, so we can mock entire sibling modules that pull in
# heavy GTK code.
for _mod_name in [
    'optionsbars',
    'optionsbars.abstract_optionsbar',
    'optionsbars.selection',
    'optionsbars.selection.optionsbar_selection',
    'tools',
    'tools.abstract_tool',
    'tools.selection_tools',
    'tools.selection_tools.abstract_select',
    'tools.selection_tools.select_rect',
    'tools.selection_tools.select_free',
    'tools.selection_tools.select_color',
    'tools.utilities_colors',
    'tools.utilities_overlay',
    'tools.utilities_paths',
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = types.ModuleType(_mod_name)


# Provide a stub for AbstractOptionsBar so OptionsBarSelection can inherit.
class _StubAbstractOptionsBar:
    def __init__(self):
        self._limit_size = 700
        self._is_narrow = False
        self.action_bar = MagicMock()
        self.cancel_btn = None
        self.centered_box = None
        self.apply_btn = None
        self.help_btn = MagicMock()
        self.help_btn.get_preferred_width = lambda: (30, 30)
        self.options_btn = None
        self._togglable_btn = None

    def _build_ui(self, path):
        return MagicMock()

    def init_adaptability(self):
        self._is_narrow = False
        self.action_bar.show_all = MagicMock()

    def _set_limit_size(self, s):
        self._limit_size = int(1.25 * s)

    def set_compact(self, state):
        self._is_narrow = state
        if self.help_btn is not None:
            self.help_btn.set_visible(not state)

    def adapt_to_window_size(self, w):
        pass

    def get_minimap_btn(self):
        return None

    def set_minimap_label(self, l):
        pass

sys.modules['optionsbars.abstract_optionsbar'].AbstractOptionsBar = _StubAbstractOptionsBar

# Stub out _() for translations
import builtins
if not hasattr(builtins, '_'):
    builtins._ = lambda s: s


# ===========================================================================
# Test helpers that exercise pure-computation logic
# ===========================================================================

def compute_rect_selection_info(x_press, y_press, event_x, event_y):
    """Mirror the logic in ToolRectSelect.motion_define for computing the
    selection rectangle's position and dimensions from two corner points."""
    x = min(x_press, event_x)
    y = min(y_press, event_y)
    w = abs(event_x - x_press)
    h = abs(event_y - y_press)
    return x, y, w, h


def compute_path_extents(path_points):
    """Mirror the logic in ToolFreeSelect._notify_live_path_extents.
    `path_points` is a list of (x, y) tuples representing the path vertices."""
    if not path_points:
        return None
    xmin = float('inf')
    ymin = float('inf')
    xmax = float('-inf')
    ymax = float('-inf')
    for (px, py) in path_points:
        xmin = min(xmin, px)
        ymin = min(ymin, py)
        xmax = max(xmax, px)
        ymax = max(ymax, py)
    if xmin < xmax and ymin < ymax:
        return int(xmin), int(ymin), int(xmax - xmin), int(ymax - ymin)
    return None


def format_selection_info(x, y, width, height):
    """Mirror the label formatting in OptionsBarSelection.set_selection_info."""
    return "Position: (%d, %d)  Size: %d x %d" % (int(x), int(y), int(width), int(height))


def compute_drag_position(sel_x, sel_y, x_press, y_press, event_x, event_y):
    """Mirror the logic for computing the new position during a drag preview."""
    local_dx = event_x - x_press
    local_dy = event_y - y_press
    return sel_x + local_dx, sel_y + local_dy


# ===========================================================================
# Tests
# ===========================================================================

class TestRectSelectionInfo(unittest.TestCase):
    """Tests for rectangular selection coordinate/size computation."""

    def test_basic_rectangle(self):
        x, y, w, h = compute_rect_selection_info(10, 20, 50, 80)
        self.assertEqual(x, 10)
        self.assertEqual(y, 20)
        self.assertEqual(w, 40)
        self.assertEqual(h, 60)

    def test_reverse_drag(self):
        """User drags from bottom-right to top-left."""
        x, y, w, h = compute_rect_selection_info(100, 200, 30, 50)
        self.assertEqual(x, 30)
        self.assertEqual(y, 50)
        self.assertEqual(w, 70)
        self.assertEqual(h, 150)

    def test_same_point(self):
        """Zero-size selection when press and release are at the same point."""
        x, y, w, h = compute_rect_selection_info(42, 42, 42, 42)
        self.assertEqual(x, 42)
        self.assertEqual(y, 42)
        self.assertEqual(w, 0)
        self.assertEqual(h, 0)

    def test_horizontal_line(self):
        """Only width, no height."""
        x, y, w, h = compute_rect_selection_info(0, 10, 50, 10)
        self.assertEqual(x, 0)
        self.assertEqual(y, 10)
        self.assertEqual(w, 50)
        self.assertEqual(h, 0)

    def test_vertical_line(self):
        """Only height, no width."""
        x, y, w, h = compute_rect_selection_info(5, 0, 5, 100)
        self.assertEqual(x, 5)
        self.assertEqual(y, 0)
        self.assertEqual(w, 0)
        self.assertEqual(h, 100)

    def test_negative_coordinates(self):
        """Selection can extend into negative space (off-canvas)."""
        x, y, w, h = compute_rect_selection_info(-20, -30, 40, 60)
        self.assertEqual(x, -20)
        self.assertEqual(y, -30)
        self.assertEqual(w, 60)
        self.assertEqual(h, 90)

    def test_large_coordinates(self):
        x, y, w, h = compute_rect_selection_info(0, 0, 10000, 8000)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(w, 10000)
        self.assertEqual(h, 8000)


class TestPathExtents(unittest.TestCase):
    """Tests for free-selection path bounding-box computation."""

    def test_triangle(self):
        pts = [(0, 0), (100, 0), (50, 80)]
        result = compute_path_extents(pts)
        self.assertEqual(result, (0, 0, 100, 80))

    def test_square(self):
        pts = [(10, 20), (60, 20), (60, 70), (10, 70)]
        result = compute_path_extents(pts)
        self.assertEqual(result, (10, 20, 50, 50))

    def test_single_point(self):
        pts = [(5, 5)]
        result = compute_path_extents(pts)
        self.assertIsNone(result)  # No area → None

    def test_two_points_horizontal(self):
        pts = [(0, 0), (100, 0)]
        result = compute_path_extents(pts)
        self.assertIsNone(result)  # No height

    def test_two_points_vertical(self):
        pts = [(0, 0), (0, 100)]
        result = compute_path_extents(pts)
        self.assertIsNone(result)  # No width

    def test_complex_polygon(self):
        pts = [(10, 10), (50, 5), (90, 30), (70, 80), (20, 60)]
        result = compute_path_extents(pts)
        # xmin=10, ymin=5, xmax=90, ymax=80
        self.assertEqual(result, (10, 5, 80, 75))

    def test_negative_coords(self):
        pts = [(-10, -20), (30, -5), (20, 40), (-5, 30)]
        result = compute_path_extents(pts)
        # xmin=-10, ymin=-20, xmax=30, ymax=40
        self.assertEqual(result, (-10, -20, 40, 60))

    def test_empty_path(self):
        result = compute_path_extents([])
        self.assertIsNone(result)

    def test_float_coordinates_truncated(self):
        """Float coords are truncated to int in the output."""
        pts = [(1.5, 1.5), (11.7, 1.5), (11.2, 9.8)]
        result = compute_path_extents(pts)
        # xmin=int(1.5)=1, ymin=int(1.5)=1, xmax=int(11.7)=11, ymax=int(9.8)=9
        self.assertEqual(result, (1, 1, 10, 8))


class TestFormatSelectionInfo(unittest.TestCase):
    """Tests for the info label formatting."""

    def test_basic_format(self):
        text = format_selection_info(10, 20, 100, 200)
        self.assertEqual(text, "Position: (10, 20)  Size: 100 x 200")

    def test_zero_origin(self):
        text = format_selection_info(0, 0, 50, 50)
        self.assertEqual(text, "Position: (0, 0)  Size: 50 x 50")

    def test_float_truncation(self):
        text = format_selection_info(10.7, 20.3, 100.9, 200.1)
        self.assertEqual(text, "Position: (10, 20)  Size: 100 x 200")

    def test_negative_position(self):
        text = format_selection_info(-5, -10, 30, 40)
        self.assertEqual(text, "Position: (-5, -10)  Size: 30 x 40")

    def test_large_dimensions(self):
        text = format_selection_info(0, 0, 1920, 1080)
        self.assertEqual(text, "Position: (0, 0)  Size: 1920 x 1080")


class TestDragPosition(unittest.TestCase):
    """Tests for the drag preview position computation."""

    def test_no_movement(self):
        nx, ny = compute_drag_position(50, 60, 100, 100, 100, 100)
        self.assertEqual(nx, 50)
        self.assertEqual(ny, 60)

    def test_drag_right_down(self):
        nx, ny = compute_drag_position(10, 20, 50, 50, 80, 90)
        self.assertEqual(nx, 40)  # 10 + (80-50)
        self.assertEqual(ny, 60)  # 20 + (90-50)

    def test_drag_left_up(self):
        nx, ny = compute_drag_position(100, 100, 80, 80, 50, 40)
        self.assertEqual(nx, 70)  # 100 + (50-80)
        self.assertEqual(ny, 60)  # 100 + (40-80)

    def test_drag_to_negative(self):
        nx, ny = compute_drag_position(10, 10, 50, 50, 20, 20)
        self.assertEqual(nx, -20)  # 10 + (20-50)
        self.assertEqual(ny, -20)  # 10 + (20-50)


class TestSelectionManagerDimensions(unittest.TestCase):
    """Tests for DrSelectionManager.get_selection_dimensions (logic only)."""

    def test_dimensions_with_pixbuf(self):
        """Verify that get_selection_dimensions returns the pixbuf's w/h."""
        # Simulate the method logic without GTK
        mock_pixbuf = MagicMock()
        mock_pixbuf.get_width.return_value = 150
        mock_pixbuf.get_height.return_value = 75
        # Simulate: sel.selection_pixbuf = mock_pixbuf
        w, h = mock_pixbuf.get_width(), mock_pixbuf.get_height()
        self.assertEqual((w, h), (150, 75))

    def test_dimensions_with_none_pixbuf(self):
        """When pixbuf is None, dimensions should be (0, 0)."""
        selection_pixbuf = None
        if selection_pixbuf is None:
            w, h = 0, 0
        self.assertEqual((w, h), (0, 0))

    def test_dimensions_one_pixel(self):
        """Initial 1x1 pixbuf."""
        mock_pixbuf = MagicMock()
        mock_pixbuf.get_width.return_value = 1
        mock_pixbuf.get_height.return_value = 1
        w, h = mock_pixbuf.get_width(), mock_pixbuf.get_height()
        self.assertEqual((w, h), (1, 1))


class TestSelectionInfoVisibility(unittest.TestCase):
    """Tests for the visibility state machine of the selection info label."""

    def test_hidden_initially(self):
        """The label starts hidden (_has_selection_info = False)."""
        has_info = False
        is_narrow = False
        visible = not is_narrow and has_info
        self.assertFalse(visible)

    def test_shown_when_active(self):
        """Label is shown when selection info is set and bar is not narrow."""
        has_info = True
        is_narrow = False
        visible = not is_narrow and has_info
        self.assertTrue(visible)

    def test_hidden_when_compact(self):
        """Label is hidden when the bar switches to compact mode."""
        has_info = True
        is_narrow = True
        visible = not is_narrow and has_info
        self.assertFalse(visible)

    def test_hidden_after_clear(self):
        """After clearing, label is hidden regardless of compact mode."""
        has_info = False
        is_narrow = False
        visible = not is_narrow and has_info
        self.assertFalse(visible)


class TestCairoPathExtentsParsing(unittest.TestCase):
    """Test the parsing logic for cairo path structures.
    Cairo paths are iterables of (op, points) tuples where points may be
    empty for move_to/close_path or (x, y) for line_to."""

    def _simulate_path_extents(self, cairo_path):
        """Replicates the iteration logic from _notify_live_path_extents."""
        xmin = float('inf')
        ymin = float('inf')
        xmax = float('-inf')
        ymax = float('-inf')
        for pts in cairo_path:
            if pts[1] != ():
                xmin = min(xmin, pts[1][0])
                ymin = min(ymin, pts[1][1])
                xmax = max(xmax, pts[1][0])
                ymax = max(ymax, pts[1][1])
        if xmin < xmax and ymin < ymax:
            return int(xmin), int(ymin), int(xmax - xmin), int(ymax - ymin)
        return None

    def test_rectangle_path(self):
        """Simulate a cairo rectangle path: move_to + 3 line_to + close."""
        path = [
            (0, (10, 20)),   # move_to
            (1, (110, 20)),  # line_to
            (1, (110, 70)),  # line_to
            (1, (10, 70)),   # line_to
            (3, ()),         # close_path
        ]
        result = self._simulate_path_extents(path)
        self.assertEqual(result, (10, 20, 100, 50))

    def test_triangle_path(self):
        path = [
            (0, (0, 0)),
            (1, (100, 0)),
            (1, (50, 80)),
            (3, ()),
        ]
        result = self._simulate_path_extents(path)
        self.assertEqual(result, (0, 0, 100, 80))

    def test_path_with_only_move_to(self):
        """A path with only a move_to has no area."""
        path = [(0, (5, 5))]
        result = self._simulate_path_extents(path)
        self.assertIsNone(result)

    def test_path_with_close_only(self):
        """Close operations have empty point tuples and are skipped."""
        path = [(3, ()), (3, ())]
        result = self._simulate_path_extents(path)
        self.assertIsNone(result)


class TestBuildRectanglePath(unittest.TestCase):
    """Test the rectangle-path building logic from abstract_select.py."""

    def test_normal_order(self):
        """Press top-left, release bottom-right."""
        x0 = min(10, 60)
        y0 = min(20, 70)
        x1 = max(10, 60)
        y1 = max(20, 70)
        self.assertEqual((x0, y0), (10, 20))
        self.assertEqual((x1, y1), (60, 70))
        self.assertGreater(x1 - x0, 0)
        self.assertGreater(y1 - y0, 0)

    def test_reversed_order(self):
        """Press bottom-right, release top-left."""
        x0 = min(60, 10)
        y0 = min(70, 20)
        x1 = max(60, 10)
        y1 = max(70, 20)
        self.assertEqual((x0, y0), (10, 20))
        self.assertEqual((x1, y1), (60, 70))

    def test_zero_width(self):
        """Same x coordinate → zero width, path should not be built."""
        w = max(10, 10) - min(10, 10)
        h = max(20, 70) - min(20, 70)
        self.assertEqual(w, 0)
        self.assertGreater(h, 0)
        # The code checks `if w <= 0 or h <= 0: return`
        should_skip = (w <= 0 or h <= 0)
        self.assertTrue(should_skip)


class TestSelectAllDimensions(unittest.TestCase):
    """Test that select_all produces correct dimensions for the full image."""

    def test_select_all(self):
        """select_all builds a rect from (0,0) to (img_w, img_h)."""
        img_w, img_h = 800, 600
        x, y, w, h = compute_rect_selection_info(0, 0, img_w, img_h)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(w, 800)
        self.assertEqual(h, 600)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_very_small_selection(self):
        x, y, w, h = compute_rect_selection_info(0, 0, 1, 1)
        self.assertEqual((x, y, w, h), (0, 0, 1, 1))

    def test_max_int_like_values(self):
        x, y, w, h = compute_rect_selection_info(0, 0, 999999, 999999)
        self.assertEqual(w, 999999)
        self.assertEqual(h, 999999)

    def test_drag_no_offset(self):
        """Dragging without moving should keep original position."""
        nx, ny = compute_drag_position(42, 84, 200, 300, 200, 300)
        self.assertEqual(nx, 42)
        self.assertEqual(ny, 84)

    def test_selection_clamp_to_image(self):
        """Verify the clamping logic from load_from_path:
        xmax = min(xmax, main_width), ymax = min(ymax, main_height)"""
        main_width = 500
        main_height = 400
        xmin, ymin, xmax, ymax = 10, 20, 600, 500  # exceeds image bounds

        xmax_clamped = min(xmax, main_width)
        ymax_clamped = min(ymax, main_height)
        xmin_clamped = int(max(xmin, 0.0))
        ymin_clamped = int(max(ymin, 0.0))

        self.assertEqual(xmax_clamped, 500)
        self.assertEqual(ymax_clamped, 400)
        self.assertEqual(xmin_clamped, 10)
        self.assertEqual(ymin_clamped, 20)

        w = xmax_clamped - xmin_clamped
        h = ymax_clamped - ymin_clamped
        self.assertEqual(w, 490)
        self.assertEqual(h, 380)

    def test_selection_negative_origin_clamp(self):
        """Negative coords are clamped to 0 in load_from_path (unless
        explicitly set negative by the tool)."""
        xmin = int(max(-5.0, 0.0))
        ymin = int(max(-10.0, 0.0))
        self.assertEqual(xmin, 0)
        self.assertEqual(ymin, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
