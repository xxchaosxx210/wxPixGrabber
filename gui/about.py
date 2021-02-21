import wx

from gui.theme import (
    vboxsizer,
    hboxsizer
)

class AboutDialog(wx.Dialog):

    def __init__(self, parent):
        super().__init__()
        self.Create(parent, -1, title="About...", style=wx.DEFAULT_DIALOG_STYLE)
        self.panel = AboutPanel(self, -1)
        btn_close = wx.Button(self, wx.ID_OK, "Close", size=(68, -1))

        vs = vboxsizer()

        hs = hboxsizer()
        hs.Add(self.panel, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 1, wx.EXPAND|wx.ALL, 0)

        hs = hboxsizer()
        hs.Add(btn_close, 0, wx.ALIGN_CENTER, 0)
        vs.Add(hs, 0, wx.ALIGN_CENTER, 0)

        self.SetSizerAndFit(vs)

        self.SetSize((400, 400))

        self.CenterOnParent()

class AboutPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self._app = wx.GetApp()
        self._buffer = wx.EmptyBitmap(*self.GetSize())

        self.Bind(wx.EVT_PAINT, self._on_paint, self)
        self.Bind(wx.EVT_SIZE, self._on_size, self)

    def _on_size(self, evt):
        self._buffer = wx.EmptyBitmap(*evt.GetSize())
    
    def _on_paint(self, evt):
        dc = wx.BufferedPaintDC(self, self._buffer)
        dc.Clear()
        dc.DrawBitmap(self._app.bitmaps["icon"], 0, 0)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawText("coded by Paul Millar", 100, 100)

    def _draw(self, dc):
        pass
