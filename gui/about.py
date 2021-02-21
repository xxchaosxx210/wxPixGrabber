import wx
import threading
import queue
import logging
from collections import namedtuple
import random

from gui.theme import (
    vboxsizer,
    hboxsizer
)

_Log = logging.getLogger(__name__)

_FRAME_RATE = 1/60 # 60 FPS

_RANDOM_SPEED_RANGE = (3, 6)

class _AboutText:

    def __init__(self, text=""):
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.text = text
        self.max_x = 0
        self.velocity = random.randint(*_RANDOM_SPEED_RANGE)
    
    def define_size(self, dc):
        self.width, self.height = dc.GetTextExtent(self.text)
        width, height = dc.Size
        self.max_x = round(int(width/2) - int(self.width/2))


class AnimatedDialog(wx.Dialog):

    def __init__(self, parent=None, id=-1, title="About", 
                 text=["My Program", "Paul Millar", 
                 "This is a brief description", "0.1"]):
        """Animated AboutDialog

        Args:
            parent (wxWindow, optional): The wxWindow Parent. Defaults to None.
            id (int, optional): The unique identifier window number. Defaults to -1.
            title (str, optional): Title of the AboutDialog. Defaults to "About".
            text (list, optional): App name, Author, description and Version. Defaults to ["My Program", "Paul Millar", "This is a brief description", "0.1"].
        """
        super().__init__()
        self.Create(parent=parent, id=id, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        self.panel = AboutPanel(self, -1, text)
        btn_close = wx.Button(self, wx.ID_OK, "Close", size=(68, -1))

        self.Bind(wx.EVT_INIT_DIALOG, self.panel.start_animation, self)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.panel.stop_animation, self)

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

    def __init__(self, parent, id, text):
        super().__init__(parent=parent, id=id)

        self._app = wx.GetApp()
        self._buffer = wx.EmptyBitmap(*self.GetSize())

        self._text = namedtuple("TextGroup", ["name", "author", "description", "version"])(
            _AboutText(text[0]),
            _AboutText(f"Developed by {text[1]}"),
            _AboutText(text[2]),
            _AboutText(f"Version - {text[3]}"))

        self.Bind(wx.EVT_PAINT, self._on_paint, self)
        self.Bind(wx.EVT_SIZE, self._on_size, self)
    
    def start_animation(self, evt):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._animation_loop)
        self._thread.start()
        evt.Skip()
    
    def stop_animation(self, evt):
        if self._thread.is_alive():
            self._queue.put("quit")
        evt.Skip()

    def _on_size(self, evt):
        self._buffer = wx.EmptyBitmap(*evt.GetSize())
        self._width, self._height = evt.GetSize()
        dc = wx.ClientDC(self)
        for line in self._text:
            line.define_size(dc)
            line.x = 0 - line.width
        lines_height = line.height * len(self._text)
        starting_y = round((self._height/2) - (lines_height/2))
        for line in self._text:
            line.y = starting_y
            starting_y += line.height
    
    def _on_paint(self, evt):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self._buffer, 0, 0)
    
    def _update_positions(self):
        for line in self._text:
            if line.x < line.max_x:
                line.x += line.velocity
        
    def _animation_loop(self):
        quit = threading.Event()
        while not quit.is_set():
            try:
                msg = self._queue.get(timeout=_FRAME_RATE)
                if msg == "quit":
                    quit.set()
            except queue.Empty:
                # update next frame animation
                wx.CallAfter(self._update_frame)
    
    def _update_frame(self):
        self._update_positions()
        dc = wx.MemoryDC()
        dc.SelectObject(self._buffer)
        self._draw(dc)
        del dc
        self.Refresh()
        self.Update()

    def _draw(self, dc):
        dc.Clear()
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, self._width, self._height)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        # draw text here
        for line in self._text:
            dc.DrawText(line.text, line.x, line.y)