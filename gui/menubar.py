import wx
import logging

_Log = logging.getLogger()

ID_OPEN_URL = 101
ID_OPEN_HTML = 102

class PixGrabberMenuBar(wx.MenuBar):

    def __init__(self, parent=None, style=0):
        super().__init__(style=style)
        self.parent = parent
        menu = wx.Menu()
        menu.Append(ID_OPEN_URL, "Open &Url", "Enter a Url address to scan")
        menu.Append(ID_OPEN_HTML, "Open &HTML", "Open an HTML document from local disk")
        self.Append(menu, "&File")
        

        parent.Bind(wx.EVT_MENU, self._on_open_url, id=ID_OPEN_URL)
        parent.Bind(wx.EVT_MENU, self._on_open_html, id=ID_OPEN_HTML)
    
    def _on_open_url(self, evt):
        _Log.info("Open URL Pressed")
    
    def _on_open_html(self, evt):
        _Log.info("Open HTML File pressed")
