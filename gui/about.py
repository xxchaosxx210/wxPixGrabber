import wx
import os
import logging
import time
from collections import namedtuple

from vector import approach

if os.name == "nt":
    # Import our C compiled classes
    from gui.about_c import C_LineText as LineText
    from gui.about_c import C_BackgroundBox as CoolEffect

_Log = logging.getLogger(__name__)

# defines the spacing between the lines
_LINE_SPACING = 20

# default
_FRAME_RATE = 1/30

def _define_size(abouttext, dc):
    """gets the size of the line in pixel count and sets maximum scoll x

    Args:
        abouttext (object): Is a LineText object
        dc (object): The Device Context to be used to define the size of the text
    """
    text_size = dc.GetFullTextExtent(abouttext.text, abouttext.font)
    abouttext.width, abouttext.height = (text_size[0], text_size[1])
    width, height = dc.Size
    abouttext.max_x = round(int(width/2) - int(abouttext.width/2))
    

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

        vs = wx.BoxSizer(wx.VERTICAL)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.panel, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 1, wx.EXPAND|wx.ALL, 0)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(btn_close, 0, wx.ALIGN_CENTER, 0)
        vs.Add(hs, 0, wx.ALIGN_CENTER, 0)

        self.SetSizerAndFit(vs)

        self.SetSize((400, 400))

        self.CenterOnParent()

class AboutPanel(wx.Panel):

    def __init__(self, parent, id, text):
        super().__init__(parent=parent, id=id)

        # Set the FrameRate to the Monitor Refresh rate
        global _FRAME_RATE
        videomode = wx.Display().GetCurrentMode()
        _FRAME_RATE = 1/videomode.refresh

        self.SetDoubleBuffered(True)
        self._create_buffer()
        self._initialize_colours()
        self._background_brush = wx.Brush(self.GetBackgroundColour())
        self._background_pen = wx.Pen(self.GetBackgroundColour())

        h1_font = wx.Font(pointSize=16, family=wx.FONTFAMILY_DECORATIVE,
        style=wx.FONTSTYLE_MAX, weight=wx.FONTWEIGHT_MAX, underline=False,
        faceName="Calibri", encoding=wx.FONTENCODING_DEFAULT)

        h2_font = wx.Font(pointSize=11, family=wx.FONTFAMILY_SCRIPT,
        style=wx.FONTSTYLE_MAX, weight=wx.FONTWEIGHT_LIGHT, underline=False,
        faceName="Tahoma", encoding=wx.FONTENCODING_DEFAULT)

        h3_font = wx.Font(pointSize=9, family=wx.FONTFAMILY_SCRIPT,
        style=wx.FONTSTYLE_MAX, weight=wx.FONTWEIGHT_LIGHT, underline=False,
        faceName="Tahoma", encoding=wx.FONTENCODING_DEFAULT)

        lines = (
            LineText(font=h1_font, text=text[0]),
            LineText(font=h2_font, text=f"Developed by {text[1]}"),
            LineText(font=h3_font, text=text[2]),
            LineText(font=h3_font, text=f"Version - {text[3]}")
        )

        self._lines = namedtuple("TextGroup", ["name", "author", "description", "version"])(*lines)

        self._cooleffect = CoolEffect(colour=wx.Colour(255, 255, 255, 255),
                                      border=wx.Colour(200, 200, 200, 255))

        self.Bind(wx.EVT_PAINT, self._on_paint, self)
        self.Bind(wx.EVT_SIZE, self._on_size, self)
        self.Bind(wx.EVT_TIMER, self._animation_loop)

        self.prev_time = 0
        self.current_time = time.monotonic()
    
    def _initialize_colours(self):
        colour = self.GetBackgroundColour()
        self._grad1_colour = colour
        self._grad2_colour = wx.Colour(colour.red - 50, colour.blue - 50, colour.green - 50, colour.alpha)
    
    def start_animation(self, evt):
        self._timer = wx.Timer(self)
        self._timer.Start(_FRAME_RATE)
    
    def stop_animation(self, evt):
        self._timer.Stop()
    
    def _create_buffer(self):
        self._buffer = wx.Bitmap()
        self._buffer.Create(self.GetSize(), wx.BITMAP_SCREEN_DEPTH)

    def _on_size(self, evt):
        self._create_buffer()
        self._width, self._height = evt.GetSize()
        dc = wx.ClientDC(self)

        # Get the dialog and resize if text is longer than the dialog
        dlg = self.GetParent()
        dlgsize = dlg.GetSize()
        for line in self._lines:
            _define_size(line, dc)
            if line.width > dlgsize[0]:
                dlg.SetSize((line.width+(_LINE_SPACING), dlgsize[1]))
            line.x = 0 - line.width

        # define the Y starting position
        lines_height = (line.height * len(self._lines)) + (_LINE_SPACING * len(self._lines))
        starting_y = round((self._height/2) - (lines_height/2))
        for line in self._lines:
            line.y = starting_y
            starting_y = starting_y + line.height + _LINE_SPACING
        
        # cooleffect
        # Set the height of the rectangle plus extra spacing around the text
        self._cooleffect.height = lines_height + _LINE_SPACING
        # Get the largest line width and set the rectangle width to that plus spacing
        line_widths = list(map(lambda line : line.width, self._lines))
        self._cooleffect.width = max(line_widths) + _LINE_SPACING
        # Set the x bounds of our box
        self._cooleffect.min_x = round((self._width/2) - (self._cooleffect.width/2))
        self._cooleffect.y = round((self._height/2) - (self._cooleffect.height/2))
        # start the box at the right side off screen
        self._cooleffect.x = self._width
    
    def _on_paint(self, evt):
        dc = wx.BufferedPaintDC(self, self._buffer)
        dc.Clear()
        # Give a nice gradient fill for our background
        dc.GradientFillLinear(self.GetRect(), 
                              self._grad1_colour, self._grad2_colour, wx.TOP)
        # Draw the background box
        dc.SetBrush(wx.Brush(self._cooleffect.colour))
        dc.SetPen(wx.Pen(self._cooleffect.border, width=2))
        dc.DrawRectangle(self._cooleffect.x, self._cooleffect.y, 
                         self._cooleffect.width, self._cooleffect.height)
        # draw the lines
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        for line in self._lines:
            if line.text:
                dc.SetFont(line.font)
                dc.DrawText(line.text, line.x, line.y)
    
    def _update_positions(self, dt):
        # Update the text lines and background box positions before rendering next frame

        # make sure all lines are still within their maximum range
        lines_still_scrolling = list(filter(lambda line : line.finished_scrolling == 0, self._lines))
        if not lines_still_scrolling and self._cooleffect.finished_scrolling:
            # no more positions to alter, quit the frame loop
            self.stop_animation(None)

        # loop through lines of text increasing the x position to the right of the screen
        for line in self._lines:
            # check we're in bounds. If not then flag no more scrolling
            if line.x < line.max_x:
                goal_x = line.x + line.velocity * dt
                line.x = approach(goal_x, line.x, dt)
            else:
                # reseat the x position slightly so it fits centre
                line.x = line.max_x
                line.finished_scrolling = 1
        
        # scroll our background box
        if self._cooleffect.x > self._cooleffect.min_x:
            goal_x = self._cooleffect.x - self._cooleffect.velocity * dt
            self._cooleffect.x = approach(goal_x, self._cooleffect.x, dt)
        else:
            # box has stopped
            self._cooleffect.finished_scrolling = 1

    def _animation_loop(self, evt):
        self._update_frame()

    def _update_frame(self):
        self.prev_time = self.current_time
        self.current_time = time.monotonic()
        dt = self.current_time - self.prev_time
        if dt > 0.15:
            dt = 0.15
        # may cause runtime error if dialog has been deleted
        try:
            # update our lines and box positions
            self._update_positions(dt * 600)
            # blit the screen
            self.Refresh()
        except RuntimeError as err:
            _Log.error(err.__str__())