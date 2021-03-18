import wx
from geometry.vector import Vector
import time
import threading

_BORDER = 10


class NotificationBar(wx.Frame):

    def __init__(self, parent, id, title="", message=""):
        super().__init__(parent=parent, id=id, title=title, 
                         style=wx.FRAME_NO_WINDOW_MENU|wx.STAY_ON_TOP)
        d_width, d_height = wx.DisplaySize()
        pnl = _NotificationPanel(self, -1, message)
        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(pnl, 1, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(gs)

        dc = wx.ClientDC(pnl)
        tsize = dc.GetFullTextExtent(message, pnl.GetFont())

        CLIENT_WIDTH = tsize[0] + 10
        CLIENT_HEIGHT = tsize[1] + 100

        self.SetDoubleBuffered(True)
        self._svector = Vector(d_width - CLIENT_WIDTH, d_height - CLIENT_HEIGHT - 50)
        self._cvector = Vector(d_width - CLIENT_WIDTH, d_height)
        self.SetPosition(wx.Point(self._cvector.x, self._cvector.y))
        
        self.Bind(wx.EVT_TIMER, self._loop)
        self._timer = wx.Timer(self)
        self.SetSize((CLIENT_WIDTH, CLIENT_HEIGHT))
        self.Show()
        self._timer.Start(1000/60)
    
    def _loop(self, evt):
        p = self._svector - self._cvector
        length = p.length()
        if length <= 5:
            threading.Thread(target=self._on_kill).start()
            self._timer.Stop()
        else:
            self._cvector.y -= 5
            self.SetPosition(wx.Point(self._cvector.x, self._cvector.y))
    
    def _on_kill(self):
        time.sleep(3)
        for alpha in range(255, 0, -10):
            self.SetTransparent(alpha)
            time.sleep(0.001000)
        self.Destroy()


class _NotificationPanel(wx.Panel):

    def __init__(self, parent, id, message):
        super().__init__(parent, id)

        font = self.GetFont()
        font.SetPointSize(12)
        self.SetFont(font)

        txt = wx.StaticText(self, -1, message)
        txt.SetFont(font)
        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(txt, 1, wx.ALIGN_CENTER, 20)
        self.SetSizer(gs)
