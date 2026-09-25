import wx
import logging
from wx.lib.buttons import GenButton

from gui.statustreeview import StatusTreeView
from crawler.message import Message
import crawler.message as const

BORDER = 6
SECTION_GAP = 10
OUTER_PADDING = 12

APP_BACKGROUND = wx.Colour(244, 246, 249)
CARD_BACKGROUND = wx.Colour(255, 255, 255)
BORDER_COLOUR = wx.Colour(216, 221, 228)
PRIMARY = wx.Colour(30, 111, 232)
SUCCESS = wx.Colour(37, 157, 78)
NEUTRAL_BUTTON = wx.Colour(232, 235, 239)
NEUTRAL_TEXT = wx.Colour(55, 61, 69)
IGNORED_TEXT = wx.Colour(166, 105, 0)
ERROR_TEXT = wx.Colour(190, 45, 45)

_Log = logging.getLogger(__name__)


def _bold_font(window, point_size=None):
    font = window.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)
    if point_size is not None:
        font.SetPointSize(point_size)
    return font


def _action_button(parent, label, size, background, foreground, bold=False):
    button = GenButton(parent, -1, label, size=size)
    button.SetBackgroundColour(background)
    button.SetForegroundColour(foreground)
    button.SetBezelWidth(1)
    button.SetUseFocusIndicator(False)
    if bold:
        button.SetFont(_bold_font(button))
    return button


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.app = wx.GetApp()
        self.SetBackgroundColour(APP_BACKGROUND)

        self.addressbar = AddressBar(self, -1)
        self.treeview = StatusTreeView(self, -1)
        self.treeview.SetIndent(20)

        tree_font = self.treeview.GetFont()
        if tree_font.GetPointSize() < 10:
            tree_font.SetPointSize(10)
            self.treeview.SetFont(tree_font)

        btn_detach = _action_button(
            self, "Progress Window", (122, 30),
            NEUTRAL_BUTTON, NEUTRAL_TEXT
        )

        self.errors = StatsPanel(
            parent=self, stat_name="Errors", stat_value="0", value_colour=ERROR_TEXT
        )
        self.ignored = StatsPanel(
            parent=self, stat_name="Ignored", stat_value="0", value_colour=IGNORED_TEXT
        )
        self.imgsaved = StatsPanel(
            parent=self, stat_name="Saved", stat_value="0", value_colour=SUCCESS
        )
        self.progressbar = ProgressPanel(self, -1)

        btn_detach.Bind(wx.EVT_BUTTON, self._on_detach_button, btn_detach)
        btn_detach.Bind(wx.EVT_ENTER_WINDOW,
                        lambda evt: self.app.window.SetStatusText("Show/Hide Detachable Progress Window"))

        vs = wx.BoxSizer(wx.VERTICAL)

        vs.Add(self.addressbar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, OUTER_PADDING)
        vs.AddSpacer(SECTION_GAP)

        summary = wx.BoxSizer(wx.HORIZONTAL)
        summary.Add(self.imgsaved, 0, wx.EXPAND | wx.RIGHT, BORDER)
        summary.Add(self.ignored, 0, wx.EXPAND | wx.RIGHT, BORDER)
        summary.Add(self.errors, 0, wx.EXPAND | wx.RIGHT, BORDER)
        summary.Add(self.progressbar, 1, wx.EXPAND | wx.RIGHT, BORDER)
        summary.Add(btn_detach, 0, wx.ALIGN_CENTER_VERTICAL)
        vs.Add(summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, OUTER_PADDING)

        vs.AddSpacer(SECTION_GAP)

        results_label = wx.StaticText(self, -1, "Results")
        results_label.SetBackgroundColour(APP_BACKGROUND)
        results_label.SetForegroundColour(NEUTRAL_TEXT)
        results_label.SetFont(_bold_font(results_label, 10))
        vs.Add(results_label, 0, wx.LEFT | wx.RIGHT, OUTER_PADDING)
        vs.AddSpacer(4)

        vs.Add(self.treeview, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, OUTER_PADDING)
        vs.AddSpacer(OUTER_PADDING)

        self.SetSizer(vs)

    def _on_detach_button(self, evt):
        if self.app.window.detached_frame.IsShown():
            self.app.window.detached_frame.Hide()
        else:
            self.app.window.detached_frame.Show()

    def fetch_link(self):
        if self.addressbar.txt_address.GetValue():
            data = {"url": self.addressbar.txt_address.GetValue()}
            self.app.commander.queue.put_nowait(
                Message(thread=const.THREAD_MAIN, event=const.EVENT_FETCH, data=data))

    def start_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_START))

    def stop_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_CANCEL))
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_FETCH_CANCEL))

    def pause_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_PAUSE))

    def open_dir_dialog(self):
        dlg = wx.FileDialog(
            parent=self, message="Choose an HTML Document to Search",
            wildcard="(*.html,*.xhtml)|*.html;*.xhtml",
            style=-wx.FD_FILE_MUST_EXIST | wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.set_address_bar(dlg.GetPaths()[0])
        dlg.Destroy()

    def on_mouse_enter(self, text):
        self.app.window.sbar.SetStatusText(text)

    def enable_controls(self, state):
        """enabled or disables the download controls

        Args:
            state (bool): if True then Buttons are enabled
        """
        self.addressbar.btn_fetch.Enable(state)
        self.addressbar.btn_start.Enable(state)
        self.addressbar.btn_pause.Enable(not state)

    def set_address_bar(self, text: str):
        self.addressbar.txt_address.SetValue(text)

    def set_progress_indeterminate(self):
        self.progressbar.save_state()
        self.progressbar.gauge.Pulse()

    def set_progress_determinate(self):
        self.progressbar.restore_state()


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)

        self.app = wx.GetApp()
        self.SetBackgroundColour(CARD_BACKGROUND)

        heading = wx.StaticText(self, -1, "Source")
        heading.SetBackgroundColour(CARD_BACKGROUND)
        heading.SetForegroundColour(NEUTRAL_TEXT)
        heading.SetFont(_bold_font(heading, 10))

        self.txt_address = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.txt_address.SetMinSize((-1, 30))

        btn_open = _action_button(
            self, "Open HTML", (104, 32),
            NEUTRAL_BUTTON, NEUTRAL_TEXT
        )

        self.btn_fetch = _action_button(
            self, "Fetch Links", (110, 32),
            PRIMARY, wx.WHITE, bold=True
        )

        self.btn_start = _action_button(
            self, "Start", (88, 32),
            SUCCESS, wx.WHITE, bold=True
        )

        self.btn_pause = _action_button(
            self, "Pause", (88, 32),
            NEUTRAL_BUTTON, NEUTRAL_TEXT
        )
        self.btn_pause.Enable(False)

        self.btn_stop = _action_button(
            self, "Stop", (88, 32),
            NEUTRAL_BUTTON, NEUTRAL_TEXT
        )

        self.txt_address.Bind(wx.EVT_TEXT_ENTER, lambda evt: self.GetParent().fetch_link(), self.txt_address)
        self.btn_fetch.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().fetch_link(), self.btn_fetch)
        self.btn_pause.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().pause_tasks(), self.btn_pause)
        self.btn_stop.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().stop_tasks(), self.btn_stop)
        self.btn_start.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().start_tasks(), self.btn_start)
        btn_open.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().open_dir_dialog(), btn_open)

        self.set_help_text(self.btn_fetch, "Fetch Links found from the Url")
        self.set_help_text(self.btn_start, "Start scanning the fetched Urls")
        self.set_help_text(self.btn_pause, "Pause the running Tasks")
        self.set_help_text(self.btn_stop, "Stop the current Scan")
        self.set_help_text(self.txt_address, "Enter a Url or File path to go fetch")
        self.set_help_text(btn_open, "Open an HTML file from local drive to go fetch")

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 6)

        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(self.txt_address, 1, wx.EXPAND | wx.RIGHT, BORDER)
        source_row.Add(btn_open, 0, wx.EXPAND)
        vs.Add(source_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        vs.AddSpacer(2)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        actions.AddStretchSpacer(1)
        actions.Add(self.btn_fetch, 0, wx.RIGHT, BORDER)
        actions.Add(self.btn_start, 0, wx.RIGHT, BORDER)
        actions.Add(self.btn_pause, 0, wx.RIGHT, BORDER)
        actions.Add(self.btn_stop, 0)
        vs.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.SetSizer(vs)

    def set_help_text(self, button, text):
        button.Bind(wx.EVT_ENTER_WINDOW,
                    lambda evt: self.on_mouse_over_button(text),
                    button)

    def on_mouse_over_button(self, text):
        self.app.window.sbar.SetStatusText(text)


class StatsPanel(wx.Panel):

    def __init__(self, stat_name, stat_value, value_colour=NEUTRAL_TEXT, *args, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)
        self.SetBackgroundColour(CARD_BACKGROUND)

        lbl = wx.StaticText(self, -1, stat_name)
        lbl.SetBackgroundColour(CARD_BACKGROUND)
        lbl.SetForegroundColour(NEUTRAL_TEXT)
        self.value = wx.StaticText(self, -1, stat_value)
        self.value.SetBackgroundColour(CARD_BACKGROUND)
        self.value.SetForegroundColour(value_colour)

        lbl_font = lbl.GetFont()
        if lbl_font.GetPointSize() < 9:
            lbl_font.SetPointSize(9)
            lbl.SetFont(lbl_font)

        self.value.SetFont(_bold_font(self.value, 14))

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        vs.Add(self.value, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(vs)
        self.SetMinSize((82, 52))

        self.stat = 0

    def reset_stat(self):
        self.stat = 0
        self.value.SetLabel("0")

    def add_stat(self):
        self.stat += 1
        self.value.SetLabel(self.stat.__str__())


class ProgressPanel(wx.Panel):

    def __init__(self, *args, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)
        self.SetBackgroundColour(CARD_BACKGROUND)

        self.gauge = wx.Gauge(self, -1, 100, style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH)
        self.gauge.SetForegroundColour(SUCCESS)
        self.gauge.SetMinSize((-1, 18))
        self.time = wx.StaticText(self, -1, "00:00:00")

        self.stored_value = 0
        self.stored_range = 100

        title = wx.StaticText(self, -1, "Progress")
        title.SetBackgroundColour(CARD_BACKGROUND)
        title.SetForegroundColour(NEUTRAL_TEXT)
        title.SetFont(_bold_font(title, 9))

        elapsed = wx.StaticText(self, -1, "Elapsed")
        elapsed.SetBackgroundColour(CARD_BACKGROUND)
        elapsed.SetForegroundColour(NEUTRAL_TEXT)
        self.time.SetBackgroundColour(CARD_BACKGROUND)
        self.time.SetForegroundColour(NEUTRAL_TEXT)
        self.time.SetFont(_bold_font(self.time, 9))

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(title, 0, wx.ALIGN_CENTER_VERTICAL)
        top.AddStretchSpacer(1)
        top.Add(elapsed, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        top.Add(self.time, 0, wx.ALIGN_CENTER_VERTICAL)

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        vs.AddSpacer(4)
        vs.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(vs)
        self.SetMinSize((320, 56))

    def reset_progress(self, max_range):
        self.gauge.SetRange(max_range)
        self.gauge.SetValue(0)

    def increment(self):
        value = self.gauge.GetValue()
        if value < self.gauge.GetRange():
            self.gauge.SetValue(value + 1)

    def save_state(self):
        self.stored_value = self.gauge.GetValue()
        self.stored_range = self.gauge.GetRange()

    def restore_state(self):
        self.gauge.SetRange(self.stored_range)
        self.gauge.SetValue(self.stored_value)
