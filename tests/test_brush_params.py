"""
Lightweight tests for brush parameter save/restore logic in ToolBrush.

These tests verify the per-brush parameter memory feature WITHOUT requiring
GTK/GObject runtime. They mock the minimal interface needed and exercise
the save/restore logic directly.

Run with:  python -m pytest tests/test_brush_params.py -v
   or:     python tests/test_brush_params.py
"""

import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Mock infrastructure that simulates the ToolBrush + OptionsBarClassic
# environment without GTK.
# ---------------------------------------------------------------------------

class MockSpinButton:
	"""Simulates GtkSpinButton — tracks value and fires value-changed."""

	def __init__(self, initial=10):
		self._value = float(initial)
		self._callbacks = []

	def get_value(self):
		return self._value

	def set_value(self, v):
		self._value = float(v)
		# Fire callbacks synchronously, like GTK value-changed signal
		for cb in self._callbacks:
			cb(self)

	def connect(self, signal, callback):
		if signal == 'value-changed':
			self._callbacks.append(callback)


class MockOptionsBar:
	"""Simulates OptionsBarClassic.set_size_value()."""

	def __init__(self, spinbtn):
		self.thickness_spinbtn = spinbtn

	def set_size_value(self, value):
		self.thickness_spinbtn.set_value(value)


class MockOptionsManager:
	"""Simulates options_manager.get_classic_tools_pane() and get_tool_width()."""

	def __init__(self, optionsbar, spinbtn):
		self._optionsbar = optionsbar
		self._spinbtn = spinbtn

	def get_classic_tools_pane(self):
		return self._optionsbar

	def get_tool_width(self):
		return int(self._spinbtn.get_value())


class MockWindow:
	def __init__(self, options_manager):
		self.options_manager = options_manager


# ---------------------------------------------------------------------------
# Minimal replica of ToolBrush save/restore logic (extracted for testing).
# This mirrors the real implementation in tool_brush.py so the tests verify
# the actual algorithm without needing GTK.
# ---------------------------------------------------------------------------

class ToolBrushUnderTest:
	"""
	Replicates the save/restore portion of ToolBrush.on_options_changed().
	All GTK-dependent parts are replaced with mocks above.
	"""

	def __init__(self, spinbtn, optionsbar, options_manager):
		self.tool_width = 10
		self._brush_type = 'simple'
		self._brush_dir = 'right'
		self._brushes_params = {}
		self._prev_brush_type = 'simple'
		self._restoring_brush_params = False
		self._last_user_width = 10

		self._spinbtn = spinbtn
		self._optionsbar = optionsbar
		self.window = MockWindow(options_manager)

		# Track sensitivity calls for assertion
		self._sensitivity_calls = []

		# Simulated option store (set externally by tests)
		self._option_values = {'brush-type': 'simple', 'brush-dir': 'right'}

		# Register callback on spinbutton, like GTK's
		# thickness_spinbtn.connect('value-changed', _on_size_changed)
		# In the real app, this triggers the chain:
		# _on_size_changed -> window.on_tool_options_changed -> tool.on_options_changed
		self._spinbtn.connect('value-changed', lambda *_: self.on_options_changed())

	# -- Simulated AbstractClassicTool.on_options_changed() --
	def _super_on_options_changed(self):
		"""Reads tool_width from the spinbutton, like the real super() call."""
		self.tool_width = int(self._spinbtn.get_value())

	# -- Public interface mirroring ToolBrush --
	def on_options_changed(self):
		# Capture the spinbutton width BEFORE super() or any restore
		current_width = int(self.window.options_manager.get_tool_width())

		if self._restoring_brush_params:
			self._super_on_options_changed()
			self._restoring_brush_params = False
			self._last_user_width = self.tool_width
			return

		self._super_on_options_changed()
		old_type = self._prev_brush_type
		self._brush_type = self._option_values.get('brush-type', 'simple')
		self._brush_dir = self._option_values.get('brush-dir', 'right')

		enable_direction = self._brush_type == 'calligraphic'
		self._sensitivity_calls.append(('brush-dir', enable_direction))

		if old_type != self._brush_type:
			self._save_brush_params(old_type, current_width)
			self._restore_brush_params(self._brush_type)
			self._prev_brush_type = self._brush_type
			self._last_user_width = self.tool_width
		else:
			self._prev_brush_type = self._brush_type
			self._last_user_width = self.tool_width

	def _save_brush_params(self, brush_type, width):
		self._brushes_params[brush_type] = {'width': width}

	def _restore_brush_params(self, brush_type):
		params = self._brushes_params.get(brush_type)
		if params is None:
			return
		if 'width' in params:
			self.tool_width = params['width']
			optionsbar = self.window.options_manager.get_classic_tools_pane()
			self._restoring_brush_params = True
			optionsbar.set_size_value(self.tool_width)

	# Test helper: simulate user changing the brush type via UI
	def switch_brush_to(self, new_type):
		self._option_values['brush-type'] = new_type
		self.on_options_changed()

	# Test helper: simulate user changing the size via spinbutton
	def set_width_via_ui(self, width):
		# set_value fires the value-changed callback, which triggers
		# on_options_changed — just like the real GTK spinbutton.
		self._spinbtn.set_value(width)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestBrushParamsSaveRestore(unittest.TestCase):
	"""Tests for per-brush parameter memory (save/restore on switch)."""

	def _make_tool(self, initial_width=10):
		spinbtn = MockSpinButton(initial_width)
		optionsbar = MockOptionsBar(spinbtn)
		options_manager = MockOptionsManager(optionsbar, spinbtn)
		tool = ToolBrushUnderTest(spinbtn, optionsbar, options_manager)
		tool.tool_width = initial_width
		return tool, spinbtn, optionsbar

	# -- Basic save/restore -----------------------------------------------

	def test_switch_away_saves_current_width(self):
		"""Switching from simple to airbrush saves simple's current width."""
		tool, spin, _ = self._make_tool(initial_width=20)
		tool.set_width_via_ui(20)

		tool.switch_brush_to('airbrush')

		self.assertIn('simple', tool._brushes_params)
		self.assertEqual(tool._brushes_params['simple']['width'], 20)

	def test_switch_back_restores_saved_width(self):
		"""Switching back to a brush restores its previously saved width."""
		tool, spin, _ = self._make_tool(initial_width=20)
		tool.set_width_via_ui(20)

		tool.switch_brush_to('airbrush')
		# Change width while on airbrush
		tool.set_width_via_ui(5)
		self.assertEqual(tool.tool_width, 5)

		# Switch back to simple — should restore width=20
		tool.switch_brush_to('simple')
		self.assertEqual(tool.tool_width, 20)
		self.assertEqual(int(spin.get_value()), 20)

	def test_switch_updates_spinbutton(self):
		"""Restoring brush params also updates the spinbutton value."""
		tool, spin, _ = self._make_tool(initial_width=25)
		tool.set_width_via_ui(25)

		tool.switch_brush_to('hairy')
		tool.set_width_via_ui(8)
		self.assertEqual(int(spin.get_value()), 8)

		tool.switch_brush_to('simple')
		self.assertEqual(int(spin.get_value()), 25)

	# -- Independent brushes -----------------------------------------------

	def test_each_brush_remembers_own_width(self):
		"""Different brush types maintain independent width values."""
		tool, spin, _ = self._make_tool(initial_width=15)

		# simple = 15
		tool.set_width_via_ui(15)
		tool.switch_brush_to('airbrush')

		# airbrush = 30
		tool.set_width_via_ui(30)
		tool.switch_brush_to('hairy')

		# hairy = 7
		tool.set_width_via_ui(7)
		tool.switch_brush_to('calligraphic')

		# calligraphic = 12
		tool.set_width_via_ui(12)

		# Now verify each restores its own width
		tool.switch_brush_to('simple')
		self.assertEqual(tool.tool_width, 15, "simple should restore to 15")

		tool.switch_brush_to('airbrush')
		self.assertEqual(tool.tool_width, 30, "airbrush should restore to 30")

		tool.switch_brush_to('hairy')
		self.assertEqual(tool.tool_width, 7, "hairy should restore to 7")

		tool.switch_brush_to('calligraphic')
		self.assertEqual(tool.tool_width, 12, "calligraphic should restore to 12")

	# -- First visit (no saved params) -------------------------------------

	def test_first_visit_does_not_crash(self):
		"""Switching to a never-visited brush type doesn't crash or change width."""
		tool, spin, _ = self._make_tool(initial_width=10)

		# Switching to airbrush (no saved params yet) should keep current width
		tool.switch_brush_to('airbrush')
		self.assertEqual(tool.tool_width, 10)

	def test_no_saved_params_does_not_modify_width(self):
		"""When no params are saved for the target brush, width is unchanged."""
		tool, spin, _ = self._make_tool(initial_width=42)
		tool.switch_brush_to('hairy')  # hairy has no saved params
		self.assertEqual(tool.tool_width, 42)

	# -- Recursion guard ---------------------------------------------------

	def test_recursion_guard_prevents_reentry(self):
		"""The _restoring_brush_params flag prevents recursive save/restore."""
		tool, spin, _ = self._make_tool(initial_width=20)
		tool.set_width_via_ui(20)
		tool.switch_brush_to('airbrush')
		tool.set_width_via_ui(5)

		# Before switching back, flag should be False
		self.assertFalse(tool._restoring_brush_params)

		# Switch back — _restore_brush_params sets flag=True, then set_value()
		# fires value-changed → on_options_changed() sees flag=True → returns early
		tool.switch_brush_to('simple')

		# After full completion, flag should be reset
		self.assertFalse(tool._restoring_brush_params)
		self.assertEqual(tool.tool_width, 20)

	# -- Brush direction sensitivity ----------------------------------------

	def test_calligraphic_enables_direction(self):
		"""Direction option is enabled only for calligraphic brush."""
		tool, _, _ = self._make_tool()
		tool.switch_brush_to('calligraphic')
		self.assertTrue(tool._sensitivity_calls[-1][1])

	def test_non_calligraphic_disables_direction(self):
		"""Direction option is disabled for non-calligraphic brushes."""
		tool, _, _ = self._make_tool()
		tool.switch_brush_to('simple')
		self.assertFalse(tool._sensitivity_calls[-1][1])

		tool.switch_brush_to('airbrush')
		self.assertFalse(tool._sensitivity_calls[-1][1])

	# -- Overwrite behavior -------------------------------------------------

	def test_width_overwrite_on_revisit(self):
		"""Changing width after returning to a brush overwrites the saved value."""
		tool, spin, _ = self._make_tool(initial_width=20)
		tool.set_width_via_ui(20)

		tool.switch_brush_to('airbrush')
		tool.switch_brush_to('simple')  # restores 20
		self.assertEqual(tool.tool_width, 20)

		# Now change width while on simple
		tool.set_width_via_ui(50)
		# Save again by switching away
		tool.switch_brush_to('airbrush')
		tool.switch_brush_to('simple')
		# Should restore the NEW value (50), not the old (20)
		self.assertEqual(tool.tool_width, 50)

	# -- Params dict structure ----------------------------------------------

	def test_params_dict_structure(self):
		"""_brushes_params stores width in a dict keyed by brush type."""
		tool, _, _ = self._make_tool(initial_width=33)
		tool.set_width_via_ui(33)
		tool.switch_brush_to('airbrush')

		self.assertIn('simple', tool._brushes_params)
		self.assertEqual(tool._brushes_params['simple'], {'width': 33})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
	unittest.main(verbosity=2)
