import os

import wx

import crawler.message as const


APP_BACKGROUND = wx.Colour(244, 246, 249)
CARD_BACKGROUND = wx.Colour(255, 255, 255)
BORDER_COLOUR = wx.Colour(216, 221, 228)
TEXT_COLOUR = wx.Colour(45, 49, 55)
MUTED_TEXT = wx.Colour(105, 112, 122)
PRIMARY = wx.Colour(30, 111, 232)
SUCCESS = wx.Colour(37, 157, 78)
IGNORED = wx.Colour(166, 105, 0)
ERROR = wx.Colour(190, 45, 45)


def _font(window, size=None, bold=False):
    font = window.GetFont()
    if size is not None:
        font.SetPointSize(size)
    if bold:
        font.SetWeight(wx.FONTWEIGHT_BOLD)
    return font


def _format_size(path):
    if not path:
        return "-"
    try:
        size = os.path.getsize(path)
    except (OSError, TypeError):
        return "-"

    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


def _filename_from_message(msg):
    data = getattr(msg, "data", {}) or {}
    value = data.get("path") or data.get("url") or ""
    return os.path.basename(value) or value


class DetachableFrame(wx.Frame):

    def __init__(self, parent, id, title="PixGrabber - Download Progress", range=100):
        super().__init__(
            parent,
            id,
            title or "PixGrabber - Download Progress",
            style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP
        )

        self.SetBackgroundColour(APP_BACKGROUND)
        self.SetMinSize((500, 260))
        self.SetSize((620, 360))

        try:
            icon = wx.Icon()
            icon.CopyFromBitmap(wx.GetApp().bitmaps["icon"])
            self.SetIcon(icon)
        except Exception:
            pass

        self.panel = ProgressPanel(self, -1, range)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(layout)

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_SHOW, self._on_show)

        self._position_bottom_right()

    def _on_close(self, evt):
        # The frame is reused throughout the application lifetime.
        self.Hide()
        evt.Veto()

    def _on_show(self, evt):
        if evt.IsShown():
            self._position_bottom_right()
        evt.Skip()

    def _position_bottom_right(self):
        try:
            display = wx.Display.GetFromWindow(self.GetParent())
            if display == wx.NOT_FOUND:
                display = 0
            area = wx.Display(display).GetClientArea()
            width, height = self.GetSize()
            x = area.x + area.width - width - 18
            y = area.y + area.height - height - 18
            self.SetPosition((max(area.x, x), max(area.y, y)))
        except Exception:
            pass

    def add_error(self, msg=None):
        self.panel.increment_error()
        if msg is not None:
            self.panel.add_result(msg)

    def add_saved(self, msg=None):
        self.panel.increment_saved()
        if msg is not None:
            self.panel.add_result(msg)

    def add_ignored(self, msg=None):
        self.panel.increment_ignored()
        if msg is not None:
            self.panel.add_result(msg)

    def add_progress(self):
        self.panel.increment_progress()

    def reset(self, range):
        self.panel.reset(range)

    def set_source(self, url, title=""):
        self.panel.set_source(url, title)

    def set_elapsed(self, elapsed):
        self.panel.set_elapsed(elapsed)

    def set_paused(self, paused):
        self.panel.set_paused(paused)


class ProgressPanel(wx.Panel):

    MAX_RECENT_ROWS = 100

    def __init__(self, parent, id, range):
        super().__init__(parent, id)
        self.SetBackgroundColour(APP_BACKGROUND)

        self.saved_count = 0
        self.ignored_count = 0
        self.error_count = 0
        self.details_shown = True

        self._build_header()
        self._build_progress()
        self._build_details()
        self._build_actions()

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.header_card, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(self.progress_card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        layout.Add(self.details_card, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        layout.Add(self.actions_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(layout)

        self.progress.SetRange(max(1, range))
        self._update_summary()

    def _build_header(self):
        self.header_card = wx.Panel(self, style=wx.BORDER_THEME)
        self.header_card.SetBackgroundColour(CARD_BACKGROUND)

        self.heading = wx.StaticText(self.header_card, label="Downloading images...")
        self.heading.SetBackgroundColour(CARD_BACKGROUND)
        self.heading.SetForegroundColour(TEXT_COLOUR)
        self.heading.SetFont(_font(self.heading, 11, True))

        self.source = wx.StaticText(
            self.header_card,
            label="Waiting for a download...",
            style=wx.ST_ELLIPSIZE_END
        )
        self.source.SetBackgroundColour(CARD_BACKGROUND)
        self.source.SetForegroundColour(MUTED_TEXT)

        stats = wx.BoxSizer(wx.HORIZONTAL)
        self.saved_label = self._stat_block(self.header_card, "Saved", "0", SUCCESS)
        self.ignored_label = self._stat_block(self.header_card, "Ignored", "0", IGNORED)
        self.error_label = self._stat_block(self.header_card, "Errors", "0", ERROR)
        self.elapsed_label = self._stat_block(self.header_card, "Elapsed", "00:00:00", TEXT_COLOUR)

        stats.Add(self.saved_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.ignored_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.error_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.elapsed_label[0], 1)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.Add(self.source, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.Add(stats, 0, wx.EXPAND | wx.ALL, 10)
        self.header_card.SetSizer(layout)

    def _stat_block(self, parent, title, value, colour):
        panel = wx.Panel(parent, style=wx.BORDER_THEME)
        panel.SetBackgroundColour(wx.Colour(248, 249, 251))

        title_label = wx.StaticText(panel, label=title)
        title_label.SetBackgroundColour(panel.GetBackgroundColour())
        title_label.SetForegroundColour(MUTED_TEXT)

        value_label = wx.StaticText(panel, label=value)
        value_label.SetBackgroundColour(panel.GetBackgroundColour())
        value_label.SetForegroundColour(colour)
        value_label.SetFont(_font(value_label, 10, True))

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(title_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        layout.Add(value_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        panel.SetSizer(layout)
        panel.SetMinSize((78, 44))
        return panel, value_label

    def _build_progress(self):
        self.progress_card = wx.Panel(self, style=wx.BORDER_THEME)
        self.progress_card.SetBackgroundColour(CARD_BACKGROUND)

        top = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(self.progress_card, label="Progress")
        title.SetBackgroundColour(CARD_BACKGROUND)
        title.SetForegroundColour(TEXT_COLOUR)
        title.SetFont(_font(title, 9, True))

        self.progress_summary = wx.StaticText(self.progress_card, label="0 / 0 tasks")
        self.progress_summary.SetBackgroundColour(CARD_BACKGROUND)
        self.progress_summary.SetForegroundColour(MUTED_TEXT)

        self.percent = wx.StaticText(self.progress_card, label="0%")
        self.percent.SetBackgroundColour(CARD_BACKGROUND)
        self.percent.SetForegroundColour(TEXT_COLOUR)
        self.percent.SetFont(_font(self.percent, 10, True))

        top.Add(title, 0, wx.ALIGN_CENTER_VERTICAL)
        top.AddStretchSpacer(1)
        top.Add(self.progress_summary, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        top.Add(self.percent, 0, wx.ALIGN_CENTER_VERTICAL)

        self.progress = wx.Gauge(
            self.progress_card,
            -1,
            100,
            style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH
        )
        self.progress.SetForegroundColour(PRIMARY)
        self.progress.SetMinSize((-1, 16))

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 9)
        layout.AddSpacer(5)
        layout.Add(self.progress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 9)
        self.progress_card.SetSizer(layout)

    def _build_details(self):
        self.details_card = wx.Panel(self, style=wx.BORDER_THEME)
        self.details_card.SetBackgroundColour(CARD_BACKGROUND)

        title = wx.StaticText(self.details_card, label="Recent activity")
        title.SetBackgroundColour(CARD_BACKGROUND)
        title.SetForegroundColour(TEXT_COLOUR)
        title.SetFont(_font(title, 9, True))

        self.results = wx.ListCtrl(
            self.details_card,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE
        )
        self.results.InsertColumn(0, "Filename", width=170)
        self.results.InsertColumn(1, "Status", width=120)
        self.results.InsertColumn(2, "Size", width=70)
        self.results.InsertColumn(3, "URL", width=220)
        self.results.Bind(wx.EVT_SIZE, self._on_results_size)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)
        layout.Add(wx.StaticLine(self.details_card), 0, wx.EXPAND)
        layout.Add(self.results, 1, wx.EXPAND)
        self.details_card.SetSizer(layout)

    def _build_actions(self):
        self.actions_panel = wx.Panel(self)
        self.actions_panel.SetBackgroundColour(APP_BACKGROUND)

        self.btn_details = wx.Button(self.actions_panel, label="Hide details", size=(88, -1))
        self.btn_pause = wx.Button(self.actions_panel, label="Pause", size=(72, -1))
        self.btn_stop = wx.Button(self.actions_panel, label="Stop", size=(72, -1))
        self.btn_hide = wx.Button(self.actions_panel, label="Hide", size=(72, -1))

        self.btn_details.Bind(wx.EVT_BUTTON, self._toggle_details)
        self.btn_pause.Bind(
            wx.EVT_BUTTON,
            lambda evt: wx.GetApp().window.dld_panel.pause_tasks()
        )
        self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
        self.btn_hide.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().Hide())

        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(self.btn_details, 0)
        layout.AddStretchSpacer(1)
        layout.Add(self.btn_pause, 0, wx.RIGHT, 7)
        layout.Add(self.btn_stop, 0, wx.RIGHT, 7)
        layout.Add(self.btn_hide, 0)
        self.actions_panel.SetSizer(layout)

    def _toggle_details(self, evt):
        self.details_shown = not self.details_shown
        self.details_card.Show(self.details_shown)
        self.btn_details.SetLabel("Hide details" if self.details_shown else "Show details")
        self.GetSizer().Layout()

        frame = self.GetParent()
        width = frame.GetSize().width
        frame.SetSize((width, 360 if self.details_shown else 225))
        frame.Layout()
        frame._position_bottom_right()

    def _on_results_size(self, evt):
        width = self.results.GetClientSize().width
        if width > 0:
            filename = max(135, int(width * 0.28))
            status = max(105, int(width * 0.20))
            size = max(65, int(width * 0.12))
            url = max(160, width - filename - status - size - 8)

            self.results.SetColumnWidth(0, filename)
            self.results.SetColumnWidth(1, status)
            self.results.SetColumnWidth(2, size)
            self.results.SetColumnWidth(3, url)
        evt.Skip()

    def _on_stop(self, evt):
        wx.GetApp().window.dld_panel.stop_tasks()
        self.btn_stop.Enable(False)
        self.heading.SetLabel("Stopping downloads...")

    def increment_saved(self):
        self.saved_count += 1
        self.saved_label[1].SetLabel(str(self.saved_count))

    def increment_ignored(self):
        self.ignored_count += 1
        self.ignored_label[1].SetLabel(str(self.ignored_count))

    def increment_error(self):
        self.error_count += 1
        self.error_label[1].SetLabel(str(self.error_count))

    def increment_progress(self):
        value = self.progress.GetValue()
        if value < self.progress.GetRange():
            self.progress.SetValue(value + 1)
        self._update_summary()

    def reset(self, range):
        self.progress.SetRange(max(1, range))
        self.progress.SetValue(0)
        self.saved_count = 0
        self.ignored_count = 0
        self.error_count = 0
        self.saved_label[1].SetLabel("0")
        self.ignored_label[1].SetLabel("0")
        self.error_label[1].SetLabel("0")
        self.elapsed_label[1].SetLabel("00:00:00")
        self.results.DeleteAllItems()
        self.btn_stop.Enable(True)
        self.btn_pause.Enable(True)
        self.btn_pause.SetLabel("Pause")
        self.heading.SetLabel("Downloading images...")
        self._update_summary()

    def set_source(self, url, title=""):
        self.heading.SetLabel(title or "Downloading images...")
        self.source.SetLabel(url or "Waiting for a download...")
        self.Layout()

    def set_elapsed(self, elapsed):
        self.elapsed_label[1].SetLabel(elapsed)

    def set_paused(self, paused):
        self.btn_pause.SetLabel("Resume" if paused else "Pause")
        self.heading.SetLabel("Paused" if paused else "Downloading images...")

    def add_result(self, msg):
        data = getattr(msg, "data", {}) or {}
        filename = _filename_from_message(msg)
        url = data.get("url", "")
        size = _format_size(data.get("path", ""))

        if msg.status == const.STATUS_OK:
            status = "Saved"
            colour = SUCCESS
        elif msg.status == const.STATUS_ERROR:
            status = "Error"
            colour = ERROR
        else:
            detail = data.get("message", "").lower()
            if "duplicate" in detail:
                status = "Ignored (duplicate)"
            elif "too small" in detail:
                status = "Ignored (too small)"
            else:
                status = "Ignored"
            colour = IGNORED

        row = self.results.InsertItem(self.results.GetItemCount(), filename)
        self.results.SetItem(row, 1, status)
        self.results.SetItem(row, 2, size)
        self.results.SetItem(row, 3, url)
        self.results.SetItemTextColour(row, colour)

        while self.results.GetItemCount() > self.MAX_RECENT_ROWS:
            self.results.DeleteItem(0)

        self.results.EnsureVisible(self.results.GetItemCount() - 1)

    def _update_summary(self):
        maximum = max(1, self.progress.GetRange())
        value = self.progress.GetValue()
        percent = int((value / maximum) * 100)
        self.progress_summary.SetLabel(f"{value} / {maximum} tasks")
        self.percent.SetLabel(f"{percent}%")
