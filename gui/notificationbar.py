import wx
from geometry.vector import Vector
import time
import threading
import queue

_BORDER = 10

NOTIFY_SHORT = 0
NOTIFY_LONG = 1


def get_display_rate():
    video_mode = wx.Display().GetCurrentMode()
    return 1 / video_mode.refresh


def _fade_frame(frame: wx.Frame):
    time.sleep(1.5)
    for alpha in range(255, 0, -10):
        frame.SetTransparent(alpha)
        time.sleep(0.001000)


class NotificationBar(wx.Frame):

    def __init__(self, parent, _id, title="", message="", timeout=NOTIFY_SHORT):
        super().__init__(parent=parent, id=_id, title=title,
                         style=wx.FRAME_NO_WINDOW_MENU|wx.STAY_ON_TOP)
        self.SetDoubleBuffered(True)
        pnl = _NotificationPanel(self, -1, message)
        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(pnl, 1, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(gs)

        self._time_out = get_display_rate()
        self._queue = queue.Queue()

        dc = wx.ClientDC(pnl)
        text_size = dc.GetFullTextExtent(message, pnl.GetFont())

        client_width = text_size[0] + 10
        client_height = text_size[1] + 100

        screen_width, screen_height = wx.DisplaySize()
        self.end_point = wx.Point(screen_width - (client_width+20), screen_height - (client_height+20))

        self.position = Vector(self.end_point.x, screen_height)
        if timeout == NOTIFY_SHORT:
            vel_y = 20
        elif timeout == NOTIFY_LONG:
            vel_y = 10
        else:
            raise AttributeError("timeout should be either NOTIFY_SHORT or NOTIFY_LONG")
        self.velocity = Vector(self.position.x, vel_y)

        self.SetPosition(wx.Point(self.position.x, self.position.y))

        self.SetSize((client_width, client_height))
        threading.Thread(target=self.loop, daemon=True).start()
        self.Show()

    def loop(self):
        _quit = threading.Event()
        while not _quit.is_set():
            try:
                if self._queue.get(timeout=self._time_out) == "quit":
                    _quit.set()
            except queue.Empty:
                dt = time.monotonic() / 1000000
                if dt > 0.16:
                    dt = 0.16
                if self.position.y > self.end_point.y:
                    self.move_frame(dt)
                else:
                    _fade_frame(self)
                    _quit.set()
        wx.CallAfter(self.Destroy)

    def move_frame(self, dt: float):
        self.position.y = self.position.y - self.velocity.y * dt
        pt = wx.Point(self.position.x, self.position.y)
        wx.CallAfter(self.SetPosition, pt)


class _NotificationPanel(wx.Panel):

    def __init__(self, parent, _id, message):
        super().__init__(parent, _id)

        font = self.GetFont()
        font.SetPointSize(12)
        self.SetFont(font)

        txt = wx.StaticText(self, -1, message)
        txt.SetFont(font)
        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(txt, 1, wx.ALIGN_CENTER, 20)
        self.SetSizer(gs)
