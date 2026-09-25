import wx
from wx.lib.buttons import GenButton

# Shared PixGrabber palette.
APP_BACKGROUND = wx.Colour(244, 246, 249)
CARD_BACKGROUND = wx.Colour(255, 255, 255)
BORDER_COLOUR = wx.Colour(216, 221, 228)
PRIMARY = wx.Colour(30, 111, 232)
SUCCESS = wx.Colour(37, 157, 78)
NEUTRAL_BUTTON = wx.Colour(232, 235, 239)
NEUTRAL_TEXT = wx.Colour(55, 61, 69)
IGNORED_TEXT = wx.Colour(166, 105, 0)
ERROR_TEXT = wx.Colour(190, 45, 45)

# Shared desktop spacing. These remain logical values and should be passed
# through dip() when exact pixel values are needed.
H_GAP = 8
V_GAP = 6
OUTER_X = 12
OUTER_Y = 8


def bold_font(window, point_size=None):
    """Return the control's native font with bold weight applied."""
    font = window.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)
    if point_size is not None:
        font.SetPointSize(point_size)
    return font


def dip(window, value):
    """Convert a logical size to device pixels using the current display DPI."""
    try:
        return window.FromDIP(value)
    except (AttributeError, TypeError):
        return value


def primary_button(parent, label, size, background, foreground, bold=False):
    """Coloured PixGrabber primary action button."""
    width, height = size
    button = GenButton(
        parent,
        -1,
        label,
        size=(dip(parent, width), dip(parent, height))
    )
    button.SetBackgroundColour(background)
    button.SetForegroundColour(foreground)
    button.SetBezelWidth(1)
    button.SetUseFocusIndicator(False)
    if bold:
        button.SetFont(bold_font(button))
    return button


def native_button(parent, label, width=None):
    """Standard Windows desktop button using the native wx.Button renderer."""
    size = (dip(parent, width), -1) if width else wx.DefaultSize
    return wx.Button(parent, -1, label, size=size)
