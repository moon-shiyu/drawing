# Licensed under GPL3 https://github.com/maoschanz/drawing/blob/master/LICENSE

import os

from gi.repository import Gtk, Gio

################################################################################

# Canonical mapping: each filter name -> set of valid lowercase extensions.
# The names MUST stay in sync with the filters added in
# utilities_add_filechooser_filters() below.
FILTER_EXTENSIONS = {
	_("All pictures"):  {'png', 'jpg', 'jpeg', 'jpe', 'bmp', 'svg'},
	_("PNG images"):    {'png'},
	_("JPEG images"):   {'jpg', 'jpeg', 'jpe'},
	_("BMP images"):    {'bmp'},
	_("SVG images"):    {'svg'},
}

def utilities_add_filechooser_filters(dialog):
	"""Add file filters for images to file chooser dialogs.
	Return the FILTER_EXTENSIONS dict so callers can look up which extensions
	are valid for the filter the user eventually selects."""
	allPictures = Gtk.FileFilter()
	allPictures.set_name(_("All pictures"))
	allPictures.add_mime_type('image/png')
	allPictures.add_mime_type('image/jpeg')
	allPictures.add_mime_type('image/bmp')
	allPictures.add_mime_type('image/svg+xml')

	pngPictures = Gtk.FileFilter()
	pngPictures.set_name(_("PNG images"))
	pngPictures.add_mime_type('image/png')

	jpegPictures = Gtk.FileFilter()
	jpegPictures.set_name(_("JPEG images"))
	jpegPictures.add_mime_type('image/jpeg')

	bmpPictures = Gtk.FileFilter()
	bmpPictures.set_name(_("BMP images"))
	bmpPictures.add_mime_type('image/bmp')

	svgPictures = Gtk.FileFilter()
	svgPictures.set_name(_("SVG images"))
	svgPictures.add_mime_type('image/svg+xml')

	dialog.add_filter(allPictures)
	dialog.add_filter(pngPictures)
	dialog.add_filter(jpegPictures)
	dialog.add_filter(bmpPictures)
	dialog.add_filter(svgPictures)

	return FILTER_EXTENSIONS

################################################################################

def utilities_check_format_mismatch(file_path, active_filter):
	"""Check whether *file_path*'s extension is compatible with the file-type
	filter the user selected in the file-chooser dialog.

	Returns a tuple ``(is_consistent, filter_name, file_ext)`` where
	*is_consistent* is ``True`` when the extension is accepted by the active
	filter (or the filter cannot be determined).
	"""
	if active_filter is None:
		return True, None, None

	filter_name = active_filter.get_name()
	valid_exts = FILTER_EXTENSIONS.get(filter_name)
	if valid_exts is None:
		# Unknown filter – cannot validate, assume OK
		return True, filter_name, None

	basename = os.path.basename(file_path)
	if '.' not in basename:
		# No extension at all – flag as mismatch so the caller can fix it
		return False, filter_name, ''

	file_ext = basename.rsplit('.', 1)[-1].lower()
	if file_ext in valid_exts:
		return True, filter_name, file_ext

	return False, filter_name, file_ext

################################################################################

def utilities_gfile_is_image(gfile, error_msg=""):
	try:
		infos = gfile.query_info('standard::*', Gio.FileQueryInfoFlags.NONE, None)
		if 'image/' in infos.get_content_type():
			# The exact file format of the image isn't validated here because i
			# can't assume what gdkpixbuf is able to read (it's modular, and it
			# evolves). An InvalidFileFormatException will be raised by DrImage
			# if the file can't be loaded.
			return True, error_msg
		else:
			error_msg = error_msg + _("%s isn't an image.") % gfile.get_path()
	except Exception as err:
		error_msg = error_msg + err.message
	return False, error_msg

class InvalidFileFormatException(Exception):
	def __init__(self, initial_message, fpath):
		self.message = initial_message
		cpt = 0
		with open(fpath, 'rb') as f:
			riff_bytes = f.read(4)
			size_bytes = f.read(4)
			webp_bytes = f.read(4)
			if riff_bytes == b'RIFF' and webp_bytes == b'WEBP':
				msg = _("Sorry, WEBP images can't be loaded by this app.") + " 😢 "
				if fpath[-5:] != '.webp':
					# Context: an error message, %s is a file path
					msg = msg + _("Despite its name, %s is a WEBP file.") % fpath
				self.message = msg
		super().__init__(self.message)
	# This exception is meant to be raised when a file is detected as an image
	# by Gio (see utility function above) BUT can't be loaded into a GdkPixbuf.
	# It usually means the file is corrupted, or has a deceptive name (for
	# example "xxx.jpeg" despite being a text file), or is just an image format
	# not supported by the GdkPixbuf version installed by the user.

################################################################################

