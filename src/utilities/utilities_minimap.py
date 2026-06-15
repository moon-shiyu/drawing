# utilities_minimap.py
#
# Pure computation for the minimap visible-area overlay rectangle.
# No GTK or cairo dependencies — testable without a display server.
#
# Licensed under GPL3 https://github.com/maoschanz/drawing/blob/master/LICENSE

import math

# Minimum pixel size for the overlay rectangle on the minimap.
# Ensures visibility even at extreme zoom levels (e.g. 2000% on a large image).
MIN_OVERLAY_RECT_SIZE = 3

# Threshold below which the overlay line width increases for visibility.
SMALL_RECT_THRESHOLD = 20

# Line width to use when the rectangle is smaller than the threshold.
THICK_LINE_WIDTH = 2


def compute_minimap_rect(
	scroll_x,
	scroll_y,
	zoom_level,
	image_width,
	image_height,
	widget_width,
	widget_height,
	mini_pixbuf_width,
	mini_pixbuf_height,
):
	"""Compute the visible-area rectangle on the minimap thumbnail.

	All parameters are plain numbers (int or float). No GTK objects.

	The function:
	1. Computes the size ratio from image dimensions to minimap dimensions.
	2. Calculates the visible area in image pixels (float precision).
	3. Clamps the visible area to not exceed actual image bounds.
	4. Maps everything to minimap coordinates.
	5. Uses math.ceil for rectangle sizing (replacing the old int()+2 hack).
	6. Enforces a minimum rectangle size for high-zoom visibility.
	7. Clamps the final rectangle to never exceed minimap bounds.
	8. Suggests a thicker line width when the rectangle is small.

	Returns:
		tuple: (mini_x, mini_y, mini_width, mini_height, line_width)
			All integers. The rectangle is guaranteed to fit within
			(0, 0, mini_pixbuf_width, mini_pixbuf_height).
	"""
	# --- Size ratio (image pixels -> minimap pixels) ---
	# The minimap preserves aspect ratio, so one ratio suffices for both axes.
	size_ratio = mini_pixbuf_width / image_width

	# --- Visible area in image pixels (float, not truncated) ---
	visible_width = widget_width / zoom_level
	visible_height = widget_height / zoom_level

	# Clamp: you cannot see more of the image than the image itself.
	# This prevents overflow when the widget is larger than the image
	# on one axis but the overlay is still needed on the other axis.
	visible_width = min(visible_width, image_width)
	visible_height = min(visible_height, image_height)

	# --- Map to minimap coordinates ---
	mini_x = int(scroll_x * size_ratio)
	mini_y = int(scroll_y * size_ratio)

	# math.ceil instead of int() + 2: rounds up to ensure full coverage
	# without the crude 2-pixel overshoot.
	mini_width = math.ceil(visible_width * size_ratio)
	mini_height = math.ceil(visible_height * size_ratio)

	# --- Enforce minimum rectangle size for visibility at high zoom ---
	mini_width = max(mini_width, MIN_OVERLAY_RECT_SIZE)
	mini_height = max(mini_height, MIN_OVERLAY_RECT_SIZE)

	# --- Clamp position to minimap bounds ---
	mini_x = max(0, min(mini_x, mini_pixbuf_width - 1))
	mini_y = max(0, min(mini_y, mini_pixbuf_height - 1))

	# --- Clamp size so rectangle never exceeds minimap ---
	mini_width = min(mini_width, mini_pixbuf_width - mini_x)
	mini_height = min(mini_height, mini_pixbuf_height - mini_y)

	# --- Adaptive line width ---
	if mini_width < SMALL_RECT_THRESHOLD or mini_height < SMALL_RECT_THRESHOLD:
		line_width = THICK_LINE_WIDTH
	else:
		line_width = 1

	return (mini_x, mini_y, mini_width, mini_height, line_width)
