import wx
import wx.html2 as webview

class ServerFrame(wx.Frame):

    def __init__(self, parent, app):
        super().__init__(parent=parent, id=-1, title="PixGrabber Helper")
        self.app = app

        self.sbar = wx.StatusBar(parent=self, id=-1)
        self.sbar.SetFieldsCount(1)
        self.SetStatusBar(self.sbar)

        self.panel = ServerPanel(self, -1)

        gs = wx.GridSizer(rows=1, cols=1, gap=(0, 0))
        gs.Add(self.panel, 1, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(gs)

        self.Bind(wx.EVT_CLOSE, self.app.on_server_close, self)
        self.SetSize((800, 600))
        self.CenterOnParent()


class ServerPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        webview.WebView.MSWSetEmulationLevel(webview.WEBVIEWIE_EMU_IE11)
        self.webview = webview.WebView.New(self, -1)
        self.webview.SetPage("""
        <html><head></head><body><h1>Welcome PixGrabber Helper</h1></br><h2>Please use one of the Apps User-Scripts</h2></body></html>
        """, '')

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.webview, 1, wx.ALL|wx.EXPAND, 0)
        vbox.Add(hbox, 1, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(vbox)

