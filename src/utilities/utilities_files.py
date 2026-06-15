# Licensed under GPL3 https://github.com/maoschanz/drawing/blob/master/LICENSE

from gi.repository import Gtk, Gio

################################################################################

def utilities_add_filechooser_filters(dialog):
	"""Add file filters for images to file chooser dialogs. Each filter carries
	an `_expected_extensions` attribute listing the extensions it covers, or
	None for the catch-all "All pictures" filter."""
	allPictures = Gtk.FileFilter()
	allPictures.set_name(_("All pictures"))
	allPictures.add_mime_type('image/png')
	allPictures.add_mime_type('image/jpeg')
	allPictures.add_mime_type('image/bmp')
	allPictures.add_mime_type('image/svg+xml')
	allPictures._expected_extensions = None

	pngPictures = Gtk.FileFilter()
	pngPictures.set_name(_("PNG images"))
	pngPictures.add_mime_type('image/png')
	pngPictures._expected_extensions = ['png']

	jpegPictures = Gtk.FileFilter()
	jpegPictures.set_name(_("JPEG images"))
	jpegPictures.add_mime_type('image/jpeg')
	jpegPictures._expected_extensions = ['jpeg', 'jpg', 'jpe']

	bmpPictures = Gtk.FileFilter()
	bmpPictures.set_name(_("BMP images"))
	bmpPictures.add_mime_type('image/bmp')
	bmpPictures._expected_extensions = ['bmp']

	svgPictures = Gtk.FileFilter()
	svgPictures.set_name(_("SVG images"))
	svgPictures.add_mime_type('image/svg+xml')
	svgPictures._expected_extensions = ['svg']

	dialog.add_filter(allPictures)
	dialog.add_filter(pngPictures)
	dialog.add_filter(jpegPictures)
	dialog.add_filter(bmpPictures)
	dialog.add_filter(svgPictures)

def utilities_get_filter_expected_extensions(file_filter):
	"""Return the list of expected extensions for a file filter, or None if the
	filter accepts all image types (no specific extension expected)."""
	return getattr(file_filter, '_expected_extensions', None)

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

