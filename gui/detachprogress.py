import json
import os

import wx

import crawler.message as const
import crawler.options as options


APP_BACKGROUND = wx.Colour(244, 246, 249)
CARD_BACKGROUND = wx.Colour(255, 255, 255)
TEXT_COLOUR = wx.Colour(45, 49, 55)
MUTED_TEXT = wx.Colour(105, 112, 122)
PRIMARY = wx.Colour(30, 111, 232)
SUCCESS = wx.Colour(37, 157, 78)
IGNORED = wx.Colour(166, 105, 0)
ERROR = wx.Colour(190, 45, 45)

STATE_PATH = os.path.join(options.PATH, "progress_window.json")
COMPACT_SIZE = (440, 205)
DETAILS_SIZE = (650, 430)


def _font(window, size=None, bold=False):
    font = window.GetFont()
    if size is not None:
        font.SetPointSize(size)
    if bold:
        font.SetWeight(wx.FONTWEIGHT_BOLD)
    return font


def _load_state():
    state = {
        "x": None,
        "y": None,
        "details": False,
        "pinned": True,
    }
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r") as fp:
                saved = json.load(fp)
            if isinstance(saved, dict):
                state.update(saved)
    except (OSError, ValueError, TypeError):
        pass
    return state


def _save_state(state):
    try:
        os.makedirs(options.PATH, exist_ok=True)
        with open(STATE_PATH, "w") as fp:
            json.dump(state, fp)
    except OSError:
        pass


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
        self.state = _load_state()
        style = wx.DEFAULT_FRAME_STYLE
        if self.state.get("pinned", True):
            style |= wx.STAY_ON_TOP

        super().__init__(
            parent,
            id,
            title or "PixGrabber - Download Progress",
            style=style
        )

        self._restoring_position = True
        self.SetBackgroundColour(APP_BACKGROUND)

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
        self.Bind(wx.EVT_MOVE, self._on_move)

        self.panel.set_pinned(bool(self.state.get("pinned", True)))
        self.panel.set_details(bool(self.state.get("details", False)), save=False)

        x = self.state.get("x")
        y = self.state.get("y")
        if isinstance(x, int) and isinstance(y, int):
            self.SetPosition((x, y))
        else:
            self._position_bottom_right()

        self._restoring_position = False

    def _on_close(self, evt):
        self.Hide()
        evt.Veto()

    def _on_move(self, evt):
        if not self._restoring_position and not self.IsIconized():
            x, y = self.GetPosition()
            self.state["x"] = int(x)
            self.state["y"] = int(y)
            self._persist_state()
        evt.Skip()

    def _persist_state(self):
        self.state["details"] = self.panel.details_shown
        self.state["pinned"] = self.panel.pinned
        _save_state(self.state)

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

    def set_pinned(self, pinned):
        style = self.GetWindowStyleFlag()
        if pinned:
            style |= wx.STAY_ON_TOP
        else:
            style &= ~wx.STAY_ON_TOP
        self.SetWindowStyleFlag(style)
        self.panel.set_pinned(pinned)
        if pinned:
            self.Raise()
        self._persist_state()

    def set_details(self, shown):
        self.panel.set_details(shown)
        self._persist_state()

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
        self.details_shown = False
        self.pinned = True

        self._build_compact_card()
        self._build_details()
        self._build_actions()

        self.layout = wx.BoxSizer(wx.VERTICAL)
        self.layout.Add(self.compact_card, 0, wx.EXPAND | wx.ALL, 8)
        self.layout.Add(self.details_card, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.layout.Add(self.actions_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.SetSizer(self.layout)

        self.progress.SetRange(max(1, range))
        self._update_summary()

    def _build_compact_card(self):
        self.compact_card = wx.Panel(self, style=wx.BORDER_THEME)
        self.compact_card.SetBackgroundColour(CARD_BACKGROUND)

        self.heading = wx.StaticText(self.compact_card, label="Downloading images...")
        self.heading.SetBackgroundColour(CARD_BACKGROUND)
        self.heading.SetForegroundColour(TEXT_COLOUR)
        self.heading.SetFont(_font(self.heading, 10, True))

        self.source = wx.StaticText(
            self.compact_card,
            label="Waiting for a download...",
            style=wx.ST_ELLIPSIZE_END
        )
        self.source.SetBackgroundColour(CARD_BACKGROUND)
        self.source.SetForegroundColour(MUTED_TEXT)

        progress_top = wx.BoxSizer(wx.HORIZONTAL)
        self.progress_summary = wx.StaticText(self.compact_card, label="0 / 0 tasks")
        self.progress_summary.SetBackgroundColour(CARD_BACKGROUND)
        self.progress_summary.SetForegroundColour(MUTED_TEXT)

        self.percent = wx.StaticText(self.compact_card, label="0%")
        self.percent.SetBackgroundColour(CARD_BACKGROUND)
        self.percent.SetForegroundColour(TEXT_COLOUR)
        self.percent.SetFont(_font(self.percent, 9, True))

        progress_top.Add(self.progress_summary, 0, wx.ALIGN_CENTER_VERTICAL)
        progress_top.AddStretchSpacer(1)
        progress_top.Add(self.percent, 0, wx.ALIGN_CENTER_VERTICAL)

        self.progress = wx.Gauge(
            self.compact_card,
            -1,
            100,
            style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH
        )
        self.progress.SetForegroundColour(PRIMARY)
        self.progress.SetMinSize((-1, 14))

        stats = wx.BoxSizer(wx.HORIZONTAL)
        self.compact_saved = self._inline_stat(self.compact_card, "Saved", SUCCESS)
        self.compact_ignored = self._inline_stat(self.compact_card, "Ignored", IGNORED)
        self.compact_error = self._inline_stat(self.compact_card, "Errors", ERROR)
        self.compact_elapsed = self._inline_stat(self.compact_card, "Elapsed", TEXT_COLOUR, "00:00:00")

        stats.Add(self.compact_saved, 0, wx.RIGHT, 13)
        stats.Add(self.compact_ignored, 0, wx.RIGHT, 13)
        stats.Add(self.compact_error, 0, wx.RIGHT, 13)
        stats.AddStretchSpacer(1)
        stats.Add(self.compact_elapsed, 0)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.Add(self.source, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.Add(progress_top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.AddSpacer(4)
        layout.Add(self.progress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        layout.AddSpacer(7)
        layout.Add(stats, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.compact_card.SetSizer(layout)

    def _inline_stat(self, parent, title, colour, initial="0"):
        label = wx.StaticText(parent, label=f"{title} {initial}")
        label.SetBackgroundColour(CARD_BACKGROUND)
        label.SetForegroundColour(colour)
        label.SetFont(_font(label, 8, True))
        label.stat_title = title
        return label

    def _build_details(self):
        self.details_card = wx.Panel(self, style=wx.BORDER_THEME)
        self.details_card.SetBackgroundColour(CARD_BACKGROUND)

        stats = wx.BoxSizer(wx.HORIZONTAL)
        self.saved_label = self._stat_block(self.details_card, "Saved", "0", SUCCESS)
        self.ignored_label = self._stat_block(self.details_card, "Ignored", "0", IGNORED)
        self.error_label = self._stat_block(self.details_card, "Errors", "0", ERROR)
        self.elapsed_label = self._stat_block(self.details_card, "Elapsed", "00:00:00", TEXT_COLOUR)

        stats.Add(self.saved_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.ignored_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.error_label[0], 1, wx.RIGHT, 6)
        stats.Add(self.elapsed_label[0], 1)

        title = wx.StaticText(self.details_card, label="Recent activity")
        title.SetBackgroundColour(CARD_BACKGROUND)
        title.SetForegroundColour(TEXT_COLOUR)
        title.SetFont(_font(title, 9, True))

        self.results = wx.ListCtrl(
            self.details_card,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE
        )
        self.results.InsertColumn(0, "Filename", width=180)
        self.results.InsertColumn(1, "Status", width=120)
        self.results.InsertColumn(2, "Size", width=75)
        self.results.InsertColumn(3, "URL", width=240)
        self.results.Bind(wx.EVT_SIZE, self._on_results_size)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(stats, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(title, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 9)
        layout.Add(wx.StaticLine(self.details_card), 0, wx.EXPAND)
        layout.Add(self.results, 1, wx.EXPAND)
        self.details_card.SetSizer(layout)

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

    def _build_actions(self):
        self.actions_panel = wx.Panel(self)
        self.actions_panel.SetBackgroundColour(APP_BACKGROUND)

        self.btn_details = wx.Button(self.actions_panel, label="Details", size=(72, -1))
        self.btn_pin = wx.Button(self.actions_panel, label="Unpin", size=(66, -1))
        self.btn_pause = wx.Button(self.actions_panel, label="Pause", size=(68, -1))
        self.btn_stop = wx.Button(self.actions_panel, label="Stop", size=(64, -1))
        self.btn_hide = wx.Button(self.actions_panel, label="Hide", size=(64, -1))

        self.btn_details.Bind(wx.EVT_BUTTON, self._toggle_details)
        self.btn_pin.Bind(wx.EVT_BUTTON, self._toggle_pin)
        self.btn_pause.Bind(
            wx.EVT_BUTTON,
            lambda evt: wx.GetApp().window.dld_panel.pause_tasks()
        )
        self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
        self.btn_hide.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().Hide())

        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(self.btn_details, 0)
        layout.AddStretchSpacer(1)
        layout.Add(self.btn_pin, 0, wx.RIGHT, 6)
        layout.Add(self.btn_pause, 0, wx.RIGHT, 6)
        layout.Add(self.btn_stop, 0, wx.RIGHT, 6)
        layout.Add(self.btn_hide, 0)
        self.actions_panel.SetSizer(layout)

    def _toggle_details(self, evt):
        self.GetParent().set_details(not self.details_shown)

    def _toggle_pin(self, evt):
        self.GetParent().set_pinned(not self.pinned)

    def set_details(self, shown, save=True):
        self.details_shown = bool(shown)
        self.details_card.Show(self.details_shown)
        self.btn_details.SetLabel("Compact" if self.details_shown else "Details")

        frame = self.GetParent()
        frame.SetMinSize((420, 190) if not self.details_shown else (560, 330))
        frame.SetSize(DETAILS_SIZE if self.details_shown else COMPACT_SIZE)
        self.Layout()
        frame.Layout()

        if save:
            frame._persist_state()

    def set_pinned(self, pinned):
        self.pinned = bool(pinned)
        self.btn_pin.SetLabel("Unpin" if self.pinned else "Pin")

    def _on_results_size(self, evt):
        width = self.results.GetClientSize().width
        if width > 0:
            filename = max(140, int(width * 0.28))
            status = max(105, int(width * 0.20))
            size = max(65, int(width * 0.12))
            url = max(170, width - filename - status - size - 8)

            self.results.SetColumnWidth(0, filename)
            self.results.SetColumnWidth(1, status)
            self.results.SetColumnWidth(2, size)
            self.results.SetColumnWidth(3, url)
        evt.Skip()

    def _on_stop(self, evt):
        wx.GetApp().window.dld_panel.stop_tasks()
        self.btn_stop.Enable(False)
        self.heading.SetLabel("Stopping downloads...")

    def _set_inline_stat(self, control, value):
        control.SetLabel(f"{control.stat_title} {value}")

    def increment_saved(self):
        self.saved_count += 1
        value = str(self.saved_count)
        self.saved_label[1].SetLabel(value)
        self._set_inline_stat(self.compact_saved, value)

    def increment_ignored(self):
        self.ignored_count += 1
        value = str(self.ignored_count)
        self.ignored_label[1].SetLabel(value)
        self._set_inline_stat(self.compact_ignored, value)

    def increment_error(self):
        self.error_count += 1
        value = str(self.error_count)
        self.error_label[1].SetLabel(value)
        self._set_inline_stat(self.compact_error, value)

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
        self._set_inline_stat(self.compact_saved, "0")
        self._set_inline_stat(self.compact_ignored, "0")
        self._set_inline_stat(self.compact_error, "0")
        self._set_inline_stat(self.compact_elapsed, "00:00:00")

        self.results.DeleteAllItems()
        self.btn_stop.Enable(True)
        self.btn_pause.Enable(True)
        self.btn_pause.SetLabel("Pause")
        self.heading.SetLabel("Downloading images...")
        self._update_summary()

    def set_source(self, url, title=""):
        self.heading.SetLabel("Downloading images...")
        self.source.SetLabel(url or title or "Waiting for a download...")
        self.Layout()

    def set_elapsed(self, elapsed):
        self.elapsed_label[1].SetLabel(elapsed)
        self._set_inline_stat(self.compact_elapsed, elapsed)

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

        if self.results.GetItemCount():
            self.results.EnsureVisible(self.results.GetItemCount() - 1)

    def _update_summary(self):
        maximum = max(1, self.progress.GetRange())
        value = self.progress.GetValue()
        percent = int((value / maximum) * 100)
        self.progress_summary.SetLabel(f"{value} / {maximum} tasks")
        self.percent.SetLabel(f"{percent}%")
