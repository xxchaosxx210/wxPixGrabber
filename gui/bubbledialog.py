import wx
import time
import random
import threading
import queue
from collections import namedtuple

from geometry.vector import (
    Vector,
    random_direction,
    rotate
)

_MIN_VELOCITY = 20
_MAX_VELOCITY = 100

_MIN_BUBBLE_SIZE = 2
_MAX_BUBBLE_SIZE = 10

_MIN_BUBBLE_AMOUNT = 100
_MAX_BUBBLE_AMOUNT = 200

_BACKGROUND_COLOUR = (173,216,230)
_BUBBLE_COLOUR_FILL = (173, 216, 230)
_BUBBLE_COLOUR_OUTLINE = (255, 255, 255)
_TEXT_BOX_COLOUR_FILL = (200, 200, 200, 100)
_TEXT_BOX_COLOUR_OUTLINE = (100, 100, 100, 255)
_DCColour = namedtuple("Colour", ["pen", "brush"])


class Bubble:

    brush: wx.Brush
    pen: wx.Pen

    def __init__(self, canvas: wx.Panel, x: int, y: int, radius: int):
        self.diameter = radius * 2
        self.radius = radius
        self.position = Vector(x, y)
        self.canvas = canvas
        self.rect = wx.Rect(x, y, self.diameter, self.diameter)
        self.velocity = Vector(0, _random_velocity())
        self.velocity.x = rotate(random.randint(0, 360)).x * _random_velocity(100, 200)
        self.off_screen = False

    def update(self, dt: float):
        self.position.y = self.position.y - self.velocity.y * dt
        self.position.x = self.position.x + self.velocity.x * dt
        self.rect.x = self.position.x
        self.rect.y = self.position.y
        self.check_bounds()

    def check_bounds(self):
        threshold = 5
        rect = self.canvas.GetRect()
        if self.rect.bottom <= rect.top:
            self.off_screen = True
        elif self.rect.left < rect.left + threshold and self.velocity.x < 0.0:
            self.velocity.x = -self.velocity.x
        elif self.rect.right > rect.right - threshold and self.velocity.x > 0.0:
            self.velocity.x = -self.velocity.x

    def move(self, x: int, y: int):
        if self.rect.left < x < self.rect.right:
            if self.rect.top < y < self.rect.bottom:
                self.velocity.x = random_direction().x * 300


def get_display_rate() -> float:
    video_mode = wx.Display().GetCurrentMode()
    return 1 / video_mode.refresh


def _random_velocity(_min: int = _MIN_VELOCITY, _max: int = _MAX_VELOCITY) -> int:
    return random.randint(_min, _max)


def generate_random_bubble(canvas: wx.Panel, rect: wx.Rect) -> Bubble:
    start_x = random.randint(0, int(round(rect.width)))
    start_y = random.randint(rect.height, rect.height + 100)
    radius = random.randint(3, 17)
    return Bubble(canvas, start_x, start_y, radius)


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

    def _on_close(self, evt: wx.CloseEvent):
        self.canvas.queue.put("quit")
        evt.Skip()


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
        self.bck_pen = wx.Pen(wx.Colour(*_TEXT_BOX_COLOUR_OUTLINE), 2)
        self.bck_brush = wx.Brush(wx.Colour(*_TEXT_BOX_COLOUR_FILL))

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
        self.dc_bck = _DCColour(wx.Pen(wx.Colour(*_BACKGROUND_COLOUR)),
                                wx.Brush(wx.Colour(*_BACKGROUND_COLOUR)))
        Bubble.brush = wx.Brush(wx.Colour(*_BUBBLE_COLOUR_FILL))
        Bubble.pen = wx.Pen(wx.Colour(*_BUBBLE_COLOUR_OUTLINE))
        self.textbox = TextBox(self, lines)
        self.bubbles = []
        self.frame_rate = get_display_rate()
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.loop)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up, self)

    def _on_left_up(self, evt: wx.MouseEvent):
        for bubble in self.bubbles:
            bubble.move(*evt.GetPosition())

    def _on_size(self, evt: wx.SizeEvent):
        self._bitmap = wx.Bitmap()
        self._bitmap.Create(evt.GetSize())
        self.textbox.resize(self.GetRect())

    def start_frame_loop(self, evt: wx.InitDialogEvent):
        rect = self.GetParent().default_size
        for i in range(random.randint(_MIN_BUBBLE_AMOUNT, _MAX_BUBBLE_AMOUNT)):
            start_x = random.randint(0, int(round(rect.width)))
            start_y = random.randint(int(round(rect.height / 2)), rect.height + 100)
            radius = random.randint(_MIN_BUBBLE_SIZE, _MAX_BUBBLE_SIZE)
            self.bubbles.append(Bubble(self, start_x, start_y, radius))
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
                        self.bubbles.append(generate_random_bubble(self, self.GetRect()))
                self.Refresh()

    def _on_paint(self, evt: wx.PaintEvent):
        dc = wx.GCDC(wx.BufferedPaintDC(self, self._bitmap))
        dc.Clear()
        # Draw Backgrounds
        dc.SetPen(self.dc_bck.pen)
        dc.SetBrush(self.dc_bck.brush)
        dc.DrawRectangle(0, 0, *self.GetSize())
        # Draw Bubbles
        dc.SetPen(Bubble.pen)
        dc.SetBrush(Bubble.brush)
        for bubble in self.bubbles:
            dc.DrawCircle(bubble.rect.x, bubble.rect.y, bubble.radius)
        # Draw Text Box
        dc.SetPen(self.textbox.bck_pen)
        dc.SetBrush(self.textbox.bck_brush)
        dc.DrawRectangle(rect=self.textbox.rect)
        # Draw Lines
        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)
        for line in self.textbox.lines:
            dc.SetFont(line.font)
            dc.DrawText(line.text, line.rect.x, line.rect.y)

