# Licensed under GPL3 https://github.com/maoschanz/drawing/blob/master/LICENSE

from .abstract_optionsbar import AbstractOptionsBar

class OptionsBarSelection(AbstractOptionsBar):
	__gtype_name__ = 'OptionsBarSelection'

	def __init__(self, window):
		super().__init__()
		self.window = window
		builder = self._build_ui('selection/optionsbar-selection.ui')

		self.import_box = builder.get_object('import_box')
		self.clipboard_box = builder.get_object('clipboard_box')
		self.actions_btn = builder.get_object('actions_btn')
		self.actions_btn_long = builder.get_object('actions_btn_long')
		self._togglable_btn = self.actions_btn

		self.options_long_box = builder.get_object('options_long_box')
		self.options_short_box = builder.get_object('options_short_box')

		self.selection_info_sep = builder.get_object('selection_info_sep')
		self.selection_info_label = builder.get_object('selection_info_label')
		self._has_selection_info = False

		self.minimap_btn = builder.get_object('minimap_btn')
		self.minimap_label = builder.get_object('minimap_label')
		self.minimap_arrow = builder.get_object('minimap_arrow')

	def get_minimap_btn(self):
		return self.minimap_btn

	def set_minimap_label(self, label):
		self.minimap_label.set_label(label)

	def set_selection_info(self, x, y, width, height):
		"""Display the selection's top-left coordinates and dimensions in the bar."""
		# Context: shown in the bottom options bar when a selection is active
		text = _("Position: (%d, %d)  Size: %d x %d") % (int(x), int(y), int(width), int(height))
		self.selection_info_label.set_text(text)
		self._has_selection_info = True
		self.selection_info_label.set_visible(not self._is_narrow)
		self.selection_info_sep.set_visible(not self._is_narrow)

	def clear_selection_info(self):
		"""Hide the selection info label and its separator."""
		self._has_selection_info = False
		self.selection_info_label.set_visible(False)
		self.selection_info_sep.set_visible(False)

	def middle_click_action(self):
		self.window.lookup_action('new_tab_selection').activate()

	############################################################################

	def init_adaptability(self):
		super().init_adaptability()
		# Set a representative sample text so preferred_width is realistic
		self.selection_info_label.set_text("Position: (0000, 0000)  Size: 0000 x 0000")
		temp_limit_size = self.import_box.get_preferred_width()[0] + \
		                    self.clipboard_box.get_preferred_width()[0] + \
		                      self.actions_btn.get_preferred_width()[0] + \
		                 self.options_long_box.get_preferred_width()[0] + \
		              self.selection_info_label.get_preferred_width()[0] + \
		                 self.selection_info_sep.get_preferred_width()[0] + \
		                         self.help_btn.get_preferred_width()[0] + \
		                      self.minimap_btn.get_preferred_width()[0]
		self.selection_info_label.set_text("")
		self._set_limit_size(temp_limit_size)

	def set_compact(self, state):
		super().set_compact(state)
		self.actions_btn_long.set_visible(state)
		self.import_box.set_visible(not state)
		self.actions_btn.set_visible(not state)

		self.options_long_box.set_visible(not state)
		self.options_short_box.set_visible(state)
		if state:
			self._togglable_btn = self.actions_btn_long
		else:
			self._togglable_btn = self.actions_btn

		self.selection_info_label.set_visible(not state and self._has_selection_info)
		self.selection_info_sep.set_visible(not state and self._has_selection_info)
		self.minimap_arrow.set_visible(not state)

	############################################################################
################################################################################

