# Static Types

import wx

from functools import partial

hboxsizer = partial(wx.BoxSizer, wx.HORIZONTAL)
vboxsizer = partial(wx.BoxSizer, wx.VERTICAL)

WX_BORDER = 5
WX_BUTTON_SIZE = (68, -1)

DIALOG_BORDER = 30

class ThemedStaticText(wx.TextCtrl):

    def __init__(self, *args, **kw):
        super(ThemedStaticText, self).__init__(*args, **kw)
        font = self.GetFont()
        font.SetPointSize(14)
        font.SetFamily(wx.FONTFAMILY_MODERN)
        self.SetFont(font)

class ThemedButton(wx.Button):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        font = self.GetFont()
        font.SetPointSize(12)
        #font.SetFamily(wx.FONTFAMILY_MAX)
        font.SetWeight(wx.FONTWEIGHT_MEDIUM)
        self.SetFont(font)