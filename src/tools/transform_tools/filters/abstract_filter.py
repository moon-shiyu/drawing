# Licensed under GPL3 https://github.com/maoschanz/drawing/blob/master/LICENSE

class AbstractFilter():
	__gtype_name__ = 'AbstractFilter'

	# Short description of the filter effect (for UI hint display)
	filter_description = ""
	# Parameter range hint string (for UI hint display)
	filter_params_hint = ""

	def __init__(self, filter_id, filters_tool, *args):
		self._id = filter_id
		self._tool = filters_tool

	def get_filter_hint(self):
		"""Return a combined description and parameter hint for the optionsbar."""
		parts = []
		if self.filter_description:
			parts.append(self.filter_description)
		if self.filter_params_hint:
			parts.append(self.filter_params_hint)
		return " — ".join(parts)

	def get_preferred_minimum_width(self):
		return 0

	def set_filter_compact(self, is_active, is_compact):
		pass

	def set_attributes_values(self):
		pass

	def build_filter_op(self):
		return {}

	def do_filter_operation(self, source_pixbuf, operation):
		pass

	############################################################################
################################################################################

