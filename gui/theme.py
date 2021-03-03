# Static Types

import wx

from functools import partial

hboxsizer = partial(wx.BoxSizer, wx.HORIZONTAL)
vboxsizer = partial(wx.BoxSizer, wx.VERTICAL)

WX_BORDER = 5

DIALOG_BORDER = 30