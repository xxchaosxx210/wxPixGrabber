import wx
import time
import random
import threading
import queue
from collections import namedtuple

from geometry.vector import Vector

_MIN_VELOCITY = 20
_MAX_VELOCITY = 100

_MIN_BUBBLE_SIZE = 2
_MAX_BUBBLE_SIZE = 10

_MIN_BUBBLE_AMOUNT = 100
_MAX_BUBBLE_AMOUNT = 200

_DCColour = namedtuple("Colour", ["pen", "brush"])


def get_display_rate():
    video_mode = wx.Display().GetCurrentMode()
    return 1 / video_mode.refresh


def _random_velocity(_min=_MIN_VELOCITY, _max=_MAX_VELOCITY):
    return random.randint(_min, _max)


def generate_random_bubble(rect: wx.Rect):
    start_x = random.randint(0, int(round(rect.width)))
    start_y = random.randint(rect.height, rect.height + 100)
    radius = random.randint(3, 17)
    return Bubble(start_x, start_y, radius)


class BubbleDialog(wx.Dialog):

    def __init__(self, parent: wx.Window, _id: int, title: str,
                 lines: list, size: tuple = wx.DefaultSize, pos: tuple = wx.DefaultPosition):
        super().__init__()
        self.Create(parent=parent, id=_id, title=title, size=size, pos=pos, style=wx.DEFAULT_DIALOG_STYLE)

        self.canvas = Canvas(self, -1, lines)

        gs = wx.GridSizer(cols=1, rows=1, hgap=0, vgap=0)
        gs.Add(self.canvas, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(gs)

        self.Bind(wx.EVT_INIT_DIALOG, self.canvas.start_frame_loop, self)
        self.Bind(wx.EVT_CLOSE, self._on_close, self)
        self.SetSize(size)

        self.default_size = wx.Rect(0, 0, *size)

    def _on_close(self, evt):
        self.canvas.queue.put("quit")
        evt.Skip()


class Bubble:

    def __init__(self, x, y, radius):
        self.diameter = radius * 2
        self.radius = radius
        self.position = Vector(x, y)
        self.velocity = Vector(x, y)
        self.velocity.y = _random_velocity()
        self.off_screen = False
        self.brush = wx.Brush(wx.Colour(255, 255, 255))
        self.pen = wx.Pen(wx.Colour(0, 0, 0), 1)

    def update(self, dt: float):
        self.position.y = self.position.y - self.velocity.y * dt
        self.check_bounds()

    def check_bounds(self):
        if self.position.y <= 0:
            self.off_screen = True


class TextBox:

    def __init__(self, canvas: wx.Panel, lines: list):
        self.lines = []
        for index, line in enumerate(lines):
            if index == 0:
                header = "h1"
            else:
                header = "h2"
            self.lines.append(Line(canvas, line, header))
        self.PADDING = 40
        self.rect = wx.Rect(0, 0, 0, 0)
        self.bck_pen = wx.Pen(wx.Colour(100, 100, 100, 100), 2)
        self.bck_brush = wx.Brush(wx.Colour(200, 200, 200, 220))

    def resize(self, rect: wx.Rect):
        for line in self.lines:
            line.update()
        self._define_size()
        self.rect.x = (rect.width/2) - (self.rect.width/2)
        self.rect.y = (rect.height/2) - (self.rect.height/2)
        self.centre_lines()

    def _define_size(self):
        rect = wx.Rect(0, 0, 0, 0)
        self.rect.height = self.PADDING
        for line in self.lines:
            if line.rect.width > rect.width:
                rect.width = line.rect.width + self.PADDING
            if line.rect.height > rect.height:
                rect.height = line.rect.height
            self.rect.height += line.rect.height
            self.rect.height += self.PADDING
        self.rect.width = rect.width

    def centre_lines(self):
        y_offset = self.rect.y + self.PADDING
        for line in self.lines:
            line.rect.y = y_offset
            line.rect.x = self.rect.x + ((self.rect.width / 2) - (line.rect.width / 2))
            y_offset = y_offset + self.PADDING + line.rect.height

    def __str__(self):
        return f"x = {self.rect.x}, y = {self.rect.y}, width = {self.rect.width}, height = {self.rect.height}"


class Line:

    def __init__(self, canvas: wx.Panel, text: str, header: str):
        self.text = text
        self.canvas = canvas
        self.font = canvas.GetFont()
        if header == "h1":
            self.font.SetPointSize(16)
        elif header == "h2":
            self.font.SetPointSize(12)
        else:
            raise KeyError("Unknown header type. Either h1 or h2")
        self.rect = wx.Rect(0, 0, 0, 0)

    def update(self):
        dc = wx.ClientDC(self.canvas)
        size = dc.GetFullTextExtent(self.text, self.font)
        self.rect.width = size[0]
        self.rect.height = size[1]

    def __str__(self):
        return f"x = {self.rect.x}, y = {self.rect.y}, width = {self.rect.width}, height = {self.rect.height}"


class Canvas(wx.Panel):

    def __init__(self, parent: wx.Dialog, _id: int, lines: list):
        super().__init__(parent, _id)
        self.SetDoubleBuffered(True)
        self._bitmap = wx.Bitmap()
        self.dc_bck = _DCColour(wx.Pen(wx.Colour(255, 255, 255)),
                                wx.Brush(wx.Colour(255, 255, 255)))
        self.textbox = TextBox(self, lines)
        self.bubbles = []
        self.frame_rate = get_display_rate()
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.loop)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def _on_size(self, evt: wx.SizeEvent):
        self._bitmap = wx.Bitmap()
        self._bitmap.Create(evt.GetSize())
        self.textbox.resize(self.GetRect())

    def start_frame_loop(self, evt):
        rect = self.GetParent().GetSize()
        for i in range(random.randint(_MIN_BUBBLE_AMOUNT, _MAX_BUBBLE_AMOUNT)):
            start_x = random.randint(0, int(round(rect.width)))
            start_y = random.randint(int(round(rect.height / 2)), rect.height + 100)
            radius = random.randint(_MIN_BUBBLE_SIZE, _MAX_BUBBLE_SIZE)
            self.bubbles.append(Bubble(start_x, start_y, radius))
        self.thread.start()

    def loop(self):
        _quit = threading.Event()
        while not _quit.is_set():
            try:
                msg = self.queue.get(timeout=self.frame_rate)
                if msg == "quit":
                    _quit.set()
            except queue.Empty:
                dt = time.monotonic() / 10000000
                if dt > 0.16:
                    dt = 0.16
                for bubble in reversed(self.bubbles):
                    bubble.update(dt)
                    if bubble.off_screen:
                        self.bubbles.remove(bubble)
                        self.bubbles.append(generate_random_bubble(self.GetRect()))
                self.Refresh()

    def _on_paint(self, evt):
        dc = wx.GCDC(wx.BufferedPaintDC(self, self._bitmap))
        dc.Clear()
        dc.SetPen(self.dc_bck.pen)
        dc.SetBrush(self.dc_bck.brush)
        dc.DrawRectangle(0, 0, *self.GetSize())
        for bubble in self.bubbles:
            dc.SetPen(bubble.pen)
            dc.SetBrush(bubble.brush)
            dc.DrawCircle(bubble.position.x, bubble.position.y, bubble.radius)
        dc.SetPen(self.textbox.bck_pen)
        dc.SetBrush(self.textbox.bck_brush)
        dc.DrawRectangle(rect=self.textbox.rect)
        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)
        for line in self.textbox.lines:
            dc.SetFont(line.font)
            dc.DrawText(line.text, line.rect.x, line.rect.y)

