"""Lightweight tests for per-brush parameter save/restore logic.

These tests mock the GTK/GIO layer so they run without a display server.
"""

import unittest


class FakeSpinButton:
    """Minimal stand-in for GtkSpinButton."""

    def __init__(self, value=10):
        self._value = value
        self._on_change = None

    def get_value(self):
        return self._value

    def set_value(self, v):
        self._value = v
        if self._on_change:
            self._on_change()


class FakePane:
    def __init__(self):
        self.thickness_spinbtn = FakeSpinButton()

    def hide_options_menu(self):
        pass


class FakeOptionsManager:
    def __init__(self):
        self._pane = FakePane()
        self._actions = {}

    def get_classic_tools_pane(self):
        return self._pane

    def get_tool_width(self):
        return int(self._pane.thickness_spinbtn.get_value())

    def set_tool_width(self, width):
        self._pane.thickness_spinbtn.set_value(width)

    def add_option_enum(self, name, default):
        self._actions[name] = default

    def get_value(self, name):
        return self._actions.get(name)

    def set_value(self, name, value):
        self._actions[name] = value


class FakeAction:
    def __init__(self):
        self._enabled = True

    def set_enabled(self, v):
        self._enabled = v


class FakeWindow:
    def __init__(self):
        self.options_manager = FakeOptionsManager()
        self._actions = {}

    def lookup_action(self, name):
        return self._actions.setdefault(name, FakeAction())


class BrushParamsMemoryMixin:
    """Extracted core logic from ToolBrush for testability.

    Mirrors the real on_options_changed path without requiring the full
    GTK tool hierarchy.
    """

    def __init__(self, window):
        self.window = window
        self.tool_width = 10
        self._brush_type = 'simple'
        self._brush_dir = 'right'
        self._brush_params_memory = {}
        self.window.options_manager.add_option_enum('brush-type', 'simple')
        self.window.options_manager.add_option_enum('brush-dir', 'right')

    def get_option_value(self, name):
        return self.window.options_manager.get_value(name)

    def set_action_sensitivity(self, name, state):
        self.window.lookup_action(name).set_enabled(state)

    def _read_tool_width(self):
        """Simulates super().on_options_changed() reading the spinbutton."""
        self.tool_width = self.window.options_manager.get_tool_width()

    def on_options_changed(self):
        old_brush_type = self._brush_type
        self._read_tool_width()

        new_brush_type = self.get_option_value('brush-type')
        self._brush_type = new_brush_type
        self._brush_dir = self.get_option_value('brush-dir')

        if old_brush_type != new_brush_type:
            self._brush_params_memory[old_brush_type] = {
                'line_width': self.tool_width,
            }
            if new_brush_type in self._brush_params_memory:
                saved = self._brush_params_memory[new_brush_type]['line_width']
                self.window.options_manager.set_tool_width(saved)
                self.tool_width = saved

        enable_direction = self._brush_type == 'calligraphic'
        self.set_action_sensitivity('brush-dir', enable_direction)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestBrushParamsMemory(unittest.TestCase):

    def _make_brush(self, initial_width=10):
        window = FakeWindow()
        window.options_manager.set_tool_width(initial_width)
        brush = BrushParamsMemoryMixin(window)
        brush._read_tool_width()
        return brush, window

    # -- helpers to simulate user actions --

    def _switch_to(self, brush, window, brush_type):
        window.options_manager.set_value('brush-type', brush_type)
        brush.on_options_changed()

    def _set_size(self, brush, window, size):
        window.options_manager.set_tool_width(size)
        brush.on_options_changed()

    # -- tests --

    def test_first_switch_no_crash(self):
        """Switching to a brush with no memory should not error."""
        brush, win = self._make_brush(10)
        self._switch_to(brush, win, 'airbrush')
        self.assertEqual(brush._brush_type, 'airbrush')
        # simple's width was saved
        self.assertEqual(brush._brush_params_memory['simple']['line_width'], 10)
        # airbrush has no saved value yet; width stays at 10
        self.assertEqual(brush.tool_width, 10)

    def test_save_and_restore(self):
        """Size should be remembered per brush type and restored on switch."""
        brush, win = self._make_brush(10)

        # Use simple at width 10, then switch to airbrush
        self._switch_to(brush, win, 'airbrush')
        self.assertEqual(brush._brush_params_memory['simple']['line_width'], 10)

        # Resize airbrush to 25
        self._set_size(brush, win, 25)
        self.assertEqual(brush.tool_width, 25)

        # Switch to hairy
        self._switch_to(brush, win, 'hairy')
        self.assertEqual(brush._brush_params_memory['airbrush']['line_width'], 25)

        # Resize hairy to 40
        self._set_size(brush, win, 40)

        # Switch back to airbrush → should restore 25
        self._switch_to(brush, win, 'airbrush')
        self.assertEqual(brush.tool_width, 25)
        self.assertEqual(win.options_manager.get_tool_width(), 25)

        # Switch back to simple → should restore 10
        self._switch_to(brush, win, 'simple')
        self.assertEqual(brush.tool_width, 10)
        self.assertEqual(win.options_manager.get_tool_width(), 10)

        # Switch back to hairy → should restore 40
        self._switch_to(brush, win, 'hairy')
        self.assertEqual(brush.tool_width, 40)

    def test_same_brush_no_side_effects(self):
        """Changing size without switching brush should not pollute memory."""
        brush, win = self._make_brush(10)
        self._set_size(brush, win, 20)
        # No brush switch occurred, so memory should be empty
        self.assertEqual(brush._brush_params_memory, {})
        self.assertEqual(brush.tool_width, 20)

    def test_round_trip_all_types(self):
        """Round-trip through all four brush types."""
        brush, win = self._make_brush(5)
        sizes = {'simple': 5, 'airbrush': 15, 'calligraphic': 30, 'hairy': 50}

        # Set each brush to its size
        for btype in ['airbrush', 'calligraphic', 'hairy']:
            self._switch_to(brush, win, btype)
            self._set_size(brush, win, sizes[btype])

        # Switch back to simple
        self._switch_to(brush, win, 'simple')
        self.assertEqual(brush.tool_width, sizes['simple'])

        # Verify each type restores correctly
        for btype in ['airbrush', 'calligraphic', 'hairy']:
            self._switch_to(brush, win, btype)
            self.assertEqual(brush.tool_width, sizes[btype],
                             f"{btype} width should be {sizes[btype]}")

    def test_calligraphic_enables_direction(self):
        """brush-dir sensitivity should track calligraphic selection."""
        brush, win = self._make_brush(10)
        dir_action = win.lookup_action('brush-dir')

        self._switch_to(brush, win, 'calligraphic')
        self.assertTrue(dir_action._enabled)

        self._switch_to(brush, win, 'simple')
        self.assertFalse(dir_action._enabled)


if __name__ == '__main__':
    unittest.main()
