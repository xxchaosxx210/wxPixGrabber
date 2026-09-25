import wx
import logging
from gui.statustreeview import StatusTreeView
from gui.style import (
    APP_BACKGROUND,
    CARD_BACKGROUND,
    PRIMARY,
    SUCCESS,
    NEUTRAL_BUTTON,
    NEUTRAL_TEXT,
    IGNORED_TEXT,
    ERROR_TEXT,
    H_GAP,
    V_GAP,
    OUTER_X,
    OUTER_Y,
    bold_font as _bold_font,
    dip as _dip,
    native_button as _native_button,
    primary_button as _action_button,
)
from crawler.message import Message
import crawler.message as const
import crawler.options as options

_Log = logging.getLogger(__name__)


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.app = wx.GetApp()
        self.SetBackgroundColour(APP_BACKGROUND)
        self.results_expanded = False
        self._expanded_frame_height = None
        self.compact_mode = False
        self._normal_frame_size = None
        self._normal_frame_position = None
        self._normal_was_maximized = False
        self._normal_title = "PixGrabber"
        self._normal_menu_bar = None

        self.addressbar = AddressBar(self, -1)
        self.results_panel = ResultsPanel(self, -1)
        self.treeview = self.results_panel.treeview
        self.treeview.SetIndent(16)

        tree_font = self.treeview.GetFont()
        tree_font.SetPointSize(9)
        self.treeview.SetFont(tree_font)

        self.errors = StatsPanel(
            parent=self, stat_name="Errors", stat_value="0",
            value_colour=ERROR_TEXT, on_change=self._sync_compact_stats
        )
        self.ignored = StatsPanel(
            parent=self, stat_name="Ignored", stat_value="0",
            value_colour=IGNORED_TEXT, on_change=self._sync_compact_stats
        )
        self.imgsaved = StatsPanel(
            parent=self, stat_name="Saved", stat_value="0",
            value_colour=SUCCESS, on_change=self._sync_compact_stats
        )
        self.progressbar = ProgressPanel(
            self, -1, on_change=self._sync_compact_progress
        )

        self.btn_compact = _native_button(self, "Compact", 72)
        self.btn_compact.Bind(
            wx.EVT_BUTTON, lambda evt: self.set_compact_mode(True)
        )
        self.btn_compact.Bind(
            wx.EVT_ENTER_WINDOW,
            lambda evt: self.app.window.SetStatusText(
                "Switch PixGrabber to compact progress view"
            )
        )

        self.compact_panel = CompactPanel(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)

        self._address_item = vs.Add(
            self.addressbar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, OUTER_X
        )
        self._source_bottom_spacer = vs.AddSpacer(OUTER_Y)
        self._summary_top_spacer = vs.AddSpacer(V_GAP)

        summary = wx.BoxSizer(wx.HORIZONTAL)
        summary.Add(self.imgsaved, 0, wx.EXPAND | wx.RIGHT, H_GAP)
        summary.Add(self.ignored, 0, wx.EXPAND | wx.RIGHT, H_GAP)
        summary.Add(self.errors, 0, wx.EXPAND | wx.RIGHT, H_GAP)
        summary.Add(self.progressbar, 1, wx.EXPAND | wx.RIGHT, H_GAP)
        summary.Add(self.btn_compact, 0, wx.ALIGN_CENTER_VERTICAL)
        self._summary_item = vs.Add(
            summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, OUTER_X
        )

        self._results_top_spacer = vs.AddSpacer(V_GAP)

        self._results_item = vs.Add(
            self.results_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, OUTER_X
        )
        self._bottom_spacer = vs.AddSpacer(OUTER_Y)

        self._compact_item = vs.Add(
            self.compact_panel, 0, wx.EXPAND | wx.ALL, _dip(self, 5)
        )
        self._compact_item.Show(False)

        self.SetSizer(vs)

        # Respect the startup preference. MainWindow applies the matching
        # frame height after its initial size has been set.
        collapse_on_start = options.load_settings().get(
            "results-collapsed-on-start", True
        )
        self.set_results_expanded(
            not collapse_on_start,
            update_status=False,
            resize_frame=False
        )

    def set_compact_mode(self, compact):
        compact = bool(compact)
        if compact == self.compact_mode:
            return

        frame = self.GetTopLevelParent()
        if not frame:
            return

        if compact:
            self._normal_was_maximized = frame.IsMaximized()
            if self._normal_was_maximized:
                frame.Restore()

            self._normal_frame_size = frame.GetSize()
            self._normal_frame_position = frame.GetPosition()
            self._normal_title = frame.GetTitle()
            self._normal_menu_bar = frame.GetMenuBar()

            for item in (
                self._address_item,
                self._source_bottom_spacer,
                self._summary_top_spacer,
                self._summary_item,
                self._results_top_spacer,
                self._results_item,
                self._bottom_spacer,
            ):
                item.Show(False)
            self._compact_item.Show(True)

            if self._normal_menu_bar is not None:
                frame.SetMenuBar(None)
            if frame.GetStatusBar() is not None:
                frame.GetStatusBar().Hide()

            self.compact_mode = True
            self._sync_compact_stats()
            self._sync_compact_progress()
            self.compact_panel.set_elapsed(self.progressbar.time.GetLabel())

            frame.SetTitle("PixGrabber")
            style = frame.GetWindowStyleFlag() | wx.STAY_ON_TOP
            frame.SetWindowStyleFlag(style)

            self.Layout()
            frame.Layout()
            self.Layout()
            frame.Layout()
            compact_best = self.GetBestSize()
            target_width = max(compact_best.width, _dip(self, 300))
            target_height = max(1, compact_best.height)
            frame.SetClientSize((target_width, target_height))

            if options.load_settings().get("compact-bottom-right", True):
                self._position_compact_bottom_right(frame)

            frame.Raise()
        else:
            self._compact_item.Show(False)
            for item in (
                self._address_item,
                self._source_bottom_spacer,
                self._summary_top_spacer,
                self._summary_item,
                self._results_top_spacer,
                self._results_item,
                self._bottom_spacer,
            ):
                item.Show(True)

            if self._normal_menu_bar is not None and frame.GetMenuBar() is None:
                frame.SetMenuBar(self._normal_menu_bar)
            if frame.GetStatusBar() is not None:
                frame.GetStatusBar().Show()

            style = frame.GetWindowStyleFlag() & ~wx.STAY_ON_TOP
            frame.SetWindowStyleFlag(style)
            frame.SetTitle(self._normal_title)

            self.compact_mode = False
            self.Layout()
            frame.Layout()

            if self._normal_frame_size is not None:
                frame.SetSize(self._normal_frame_size)
            if self._normal_frame_position is not None:
                frame.SetPosition(self._normal_frame_position)
            if self._normal_was_maximized:
                frame.Maximize(True)

    def _position_compact_bottom_right(self, frame):
        """Place compact mode just above the taskbar on the current display."""
        try:
            display_index = wx.Display.GetFromWindow(frame)
            if display_index == wx.NOT_FOUND:
                display_index = 0
            area = wx.Display(display_index).GetClientArea()
            width, height = frame.GetSize()
            margin = _dip(frame, 10)
            x = area.x + area.width - width - margin
            y = area.y + area.height - height - margin
            frame.SetPosition((max(area.x, x), max(area.y, y)))
        except Exception:
            pass

    def _sync_compact_stats(self, *_args):
        if not hasattr(self, "compact_panel"):
            return
        self.compact_panel.set_stats(
            self.imgsaved.stat,
            self.ignored.stat,
            self.errors.stat,
        )

    def _sync_compact_progress(self, *_args):
        if not hasattr(self, "compact_panel"):
            return
        self.compact_panel.set_progress(
            self.progressbar.gauge.GetValue(),
            self.progressbar.gauge.GetRange(),
        )

    def set_elapsed(self, elapsed):
        self.progressbar.time.SetLabel(elapsed)
        self.compact_panel.set_elapsed(elapsed)

    def set_paused(self, paused):
        self.compact_panel.set_paused(paused)

    def set_fetching_progress(self):
        self.progressbar.gauge.SetValue(10)
        self.progressbar.gauge.Pulse()
        self.compact_panel.progress.Pulse()

    def toggle_results_expanded(self):
        self.set_results_expanded(not self.results_expanded)

    def apply_initial_results_state(self):
        """Resize the main window to match the configured Results startup state."""
        frame = self.GetTopLevelParent()
        if frame:
            self._expanded_frame_height = frame.GetSize().height
        self._resize_frame_for_results(self.results_expanded)

    def set_results_expanded(self, expanded, update_status=True, resize_frame=True):
        expanded = bool(expanded)

        # Remember the user's current expanded height before collapsing so
        # opening Results again returns to the same useful working height.
        if self.results_expanded and not expanded:
            frame = self.GetTopLevelParent()
            if frame and not frame.IsMaximized() and not frame.IsIconized():
                self._expanded_frame_height = frame.GetSize().height

        self.results_expanded = expanded
        self.results_panel.set_expanded(self.results_expanded)

        # Collapsed Results only occupies the header height. Expanded Results
        # takes the remaining space below the controls.
        self._results_item.SetProportion(1 if self.results_expanded else 0)

        self.Layout()
        self.GetParent().Layout()

        if resize_frame:
            self._resize_frame_for_results(self.results_expanded)

        if update_status:
            frame = self.GetTopLevelParent()
            if frame:
                frame.SetStatusText(
                    "Results expanded" if self.results_expanded else "Results collapsed"
                )

    def _resize_frame_for_results(self, expanded):
        frame = self.GetTopLevelParent()
        if not frame or frame.IsMaximized() or frame.IsIconized():
            return

        current_width = frame.GetSize().width

        if expanded:
            target_height = self._expanded_frame_height
            if not target_height:
                target_height = max(frame.GetSize().height, 520)
        else:
            # The panel's best size now contains only Source, summary/progress
            # and the collapsed Results header. Add the existing frame chrome
            # and status-bar allowance so the outer frame hugs that content.
            frame.Layout()
            self.Layout()
            best_panel_height = self.GetBestSize().height
            chrome_height = max(0, frame.GetSize().height - self.GetSize().height)
            target_height = best_panel_height + chrome_height

        frame.SetSize((current_width, int(target_height)))
        frame.Layout()

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
        self.compact_panel.btn_pause.Enable(not state)

    def set_address_bar(self, text: str):
        self.addressbar.txt_address.SetValue(text)

    def set_progress_indeterminate(self):
        self.progressbar.save_state()
        self.progressbar.gauge.Pulse()

    def set_progress_determinate(self):
        self.progressbar.restore_state()


class CompactPanel(wx.Panel):

    def __init__(self, parent, id):
        super().__init__(parent, id, style=wx.BORDER_SIMPLE)
        self.SetBackgroundColour(CARD_BACKGROUND)

        gap_small = _dip(self, 4)
        gap_medium = _dip(self, 5)
        gap_large = _dip(self, 7)

        stats = wx.BoxSizer(wx.HORIZONTAL)
        self.saved = self._stat("Saved", SUCCESS)
        self.ignored = self._stat("Ignored", IGNORED_TEXT)
        self.errors = self._stat("Errors", ERROR_TEXT)

        stats.Add(self.saved[0], 1)
        stats.Add(
            wx.StaticLine(self, style=wx.LI_VERTICAL),
            0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap_medium
        )
        stats.Add(self.ignored[0], 1)
        stats.Add(
            wx.StaticLine(self, style=wx.LI_VERTICAL),
            0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap_medium
        )
        stats.Add(self.errors[0], 1)

        progress_row = wx.BoxSizer(wx.HORIZONTAL)
        self.progress = wx.Gauge(
            self, -1, 100,
            style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH
        )
        self.progress.SetForegroundColour(SUCCESS)
        self.progress.SetMinSize((-1, _dip(self, 10)))

        self.percent = wx.StaticText(self, label="0%")
        self.percent.SetForegroundColour(NEUTRAL_TEXT)
        self.percent.SetFont(_bold_font(self.percent))

        progress_row.Add(
            self.progress, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, gap_large
        )
        progress_row.Add(self.percent, 0, wx.ALIGN_CENTER_VERTICAL)

        elapsed_row = wx.BoxSizer(wx.HORIZONTAL)
        elapsed_row.AddStretchSpacer(1)

        elapsed_label = wx.StaticText(self, label="Elapsed")
        elapsed_label.SetForegroundColour(NEUTRAL_TEXT)

        self.elapsed = wx.StaticText(self, label="00:00:00")
        self.elapsed.SetForegroundColour(NEUTRAL_TEXT)
        self.elapsed.SetFont(_bold_font(self.elapsed))

        elapsed_row.Add(
            elapsed_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, gap_small
        )
        elapsed_row.Add(self.elapsed, 0, wx.ALIGN_CENTER_VERTICAL)

        # Let Windows choose the native button font and natural button height.
        self.btn_pause = _native_button(self, "Pause")
        self.btn_stop = _native_button(self, "Stop")
        self.btn_full = _native_button(self, "Full View")

        self.btn_pause.Bind(
            wx.EVT_BUTTON, lambda evt: self.GetParent().pause_tasks()
        )
        self.btn_stop.Bind(
            wx.EVT_BUTTON, lambda evt: self.GetParent().stop_tasks()
        )
        self.btn_full.Bind(
            wx.EVT_BUTTON, lambda evt: self.GetParent().set_compact_mode(False)
        )

        actions = wx.BoxSizer(wx.HORIZONTAL)
        actions.AddStretchSpacer(1)
        actions.Add(self.btn_pause, 0)
        actions.AddSpacer(gap_medium)
        actions.Add(self.btn_stop, 0)
        actions.AddSpacer(gap_medium)
        actions.Add(self.btn_full, 0)
        actions.AddStretchSpacer(1)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(stats, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, gap_large)
        layout.Add(
            progress_row, 0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, gap_medium
        )
        layout.Add(
            elapsed_row, 0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, gap_small
        )
        layout.Add(
            wx.StaticLine(self), 0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, gap_medium
        )
        layout.Add(
            actions, 0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, gap_large
        )
        self.SetSizer(layout)

    def _stat(self, title, colour):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(CARD_BACKGROUND)

        label = wx.StaticText(panel, label=title)
        label.SetBackgroundColour(CARD_BACKGROUND)
        label.SetForegroundColour(NEUTRAL_TEXT)

        value = wx.StaticText(panel, label="0")
        value.SetBackgroundColour(CARD_BACKGROUND)
        value.SetForegroundColour(colour)
        value.SetFont(_bold_font(value))

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(label, 0, wx.ALIGN_CENTER_HORIZONTAL)
        layout.Add(
            value, 0,
            wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, _dip(panel, 1)
        )
        panel.SetSizer(layout)
        return panel, value

    def set_stats(self, saved, ignored, errors):
        self.saved[1].SetLabel(str(saved))
        self.ignored[1].SetLabel(str(ignored))
        self.errors[1].SetLabel(str(errors))

    def set_progress(self, value, maximum):
        maximum = max(1, int(maximum))
        value = max(0, min(int(value), maximum))
        self.progress.SetRange(maximum)
        self.progress.SetValue(value)
        self.percent.SetLabel(f"{int((value / maximum) * 100)}%")

    def set_elapsed(self, elapsed):
        self.elapsed.SetLabel(elapsed)

    def set_paused(self, paused):
        self.btn_pause.SetLabel("Resume" if paused else "Pause")


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)

        self.app = wx.GetApp()
        self.SetBackgroundColour(CARD_BACKGROUND)

        heading = wx.StaticText(self, -1, "Source")
        heading.SetBackgroundColour(CARD_BACKGROUND)
        heading.SetForegroundColour(NEUTRAL_TEXT)
        heading.SetFont(_bold_font(heading, 9))

        self.txt_address = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.txt_address.SetMinSize((-1, 26))

        btn_open = _native_button(self, "Open HTML", 90)

        self.btn_fetch = _action_button(
            self, "Fetch Links", (96, 28),
            PRIMARY, wx.WHITE, bold=True
        )

        self.btn_start = _action_button(
            self, "Start", (72, 28),
            SUCCESS, wx.WHITE, bold=True
        )

        self.btn_pause = _native_button(self, "Pause", 72)
        self.btn_pause.Enable(False)

        self.btn_stop = _native_button(self, "Stop", 72)

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
        vs.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 3)

        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(self.txt_address, 1, wx.EXPAND | wx.RIGHT, H_GAP)
        source_row.Add(btn_open, 0, wx.EXPAND)
        vs.Add(source_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        vs.AddSpacer(5)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        actions.AddStretchSpacer(1)
        actions.Add(self.btn_fetch, 0, wx.RIGHT, H_GAP)
        actions.Add(self.btn_start, 0, wx.RIGHT, H_GAP)
        actions.Add(self.btn_pause, 0, wx.RIGHT, H_GAP)
        actions.Add(self.btn_stop, 0)
        vs.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(vs)

    def set_help_text(self, button, text):
        button.Bind(wx.EVT_ENTER_WINDOW,
                    lambda evt: self.on_mouse_over_button(text),
                    button)

    def on_mouse_over_button(self, text):
        self.app.window.sbar.SetStatusText(text)


class ResultsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)
        self.SetBackgroundColour(CARD_BACKGROUND)

        self.treeview = StatusTreeView(self, -1)

        header = wx.Panel(self, -1)
        header.SetBackgroundColour(wx.Colour(248, 249, 251))

        title = wx.StaticText(header, -1, "Results")
        title.SetBackgroundColour(header.GetBackgroundColour())
        title.SetForegroundColour(NEUTRAL_TEXT)
        title.SetFont(_bold_font(title, 9))

        self.btn_expand = _native_button(header, "Expand", 68)
        self.btn_expand.Bind(
            wx.EVT_BUTTON,
            lambda evt: self.GetParent().toggle_results_expanded()
        )
        self.btn_expand.Bind(
            wx.EVT_ENTER_WINDOW,
            lambda evt: wx.GetApp().window.SetStatusText(
                "Expand or collapse the Results tree"
            )
        )

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(title, 0, wx.ALIGN_CENTER_VERTICAL)
        hs.AddStretchSpacer(1)
        hs.Add(self.btn_expand, 0, wx.ALIGN_CENTER_VERTICAL)

        header.SetSizer(hs)

        self.divider = wx.StaticLine(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 6)
        vs.Add(self.divider, 0, wx.EXPAND)
        vs.Add(self.treeview, 1, wx.EXPAND)
        self.SetSizer(vs)

        self.divider.Hide()
        self.treeview.Hide()


    def set_expanded(self, expanded):
        self.btn_expand.SetLabel("Collapse" if expanded else "Expand")
        self.divider.Show(expanded)
        self.treeview.Show(expanded)
        self.Layout()



class StatsPanel(wx.Panel):

    def __init__(
        self, stat_name, stat_value, value_colour=NEUTRAL_TEXT,
        on_change=None, *args, **kw
    ):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)
        self.on_change = on_change
        self.SetBackgroundColour(CARD_BACKGROUND)

        lbl = wx.StaticText(self, -1, stat_name)
        lbl.SetBackgroundColour(CARD_BACKGROUND)
        lbl.SetForegroundColour(NEUTRAL_TEXT)
        self.value = wx.StaticText(self, -1, stat_value)
        self.value.SetBackgroundColour(CARD_BACKGROUND)
        self.value.SetForegroundColour(value_colour)

        lbl_font = lbl.GetFont()
        lbl_font.SetPointSize(9)
        lbl.SetFont(lbl_font)

        self.value.SetFont(_bold_font(self.value, 12))

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        vs.Add(self.value, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        self.SetSizer(vs)
        self.SetMinSize((72, 44))

        self.stat = 0

    def reset_stat(self):
        self.stat = 0
        self.value.SetLabel("0")
        if self.on_change:
            self.on_change(self.stat)

    def add_stat(self):
        self.stat += 1
        self.value.SetLabel(self.stat.__str__())
        if self.on_change:
            self.on_change(self.stat)


class ProgressPanel(wx.Panel):

    def __init__(self, *args, on_change=None, **kw):
        kw.setdefault("style", wx.BORDER_SIMPLE)
        super().__init__(*args, **kw)
        self.on_change = on_change
        self.SetBackgroundColour(CARD_BACKGROUND)

        self.gauge = wx.Gauge(self, -1, 100, style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH)
        self.gauge.SetForegroundColour(SUCCESS)
        self.gauge.SetMinSize((-1, 14))
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
        vs.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        vs.AddSpacer(3)
        vs.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.SetSizer(vs)
        self.SetMinSize((280, 46))

    def reset_progress(self, max_range):
        self.gauge.SetRange(max_range)
        self.gauge.SetValue(0)
        if self.on_change:
            self.on_change(0, max_range)

    def increment(self):
        value = self.gauge.GetValue()
        if value < self.gauge.GetRange():
            self.gauge.SetValue(value + 1)
        if self.on_change:
            self.on_change(self.gauge.GetValue(), self.gauge.GetRange())

    def save_state(self):
        self.stored_value = self.gauge.GetValue()
        self.stored_range = self.gauge.GetRange()

    def restore_state(self):
        self.gauge.SetRange(self.stored_range)
        self.gauge.SetValue(self.stored_value)
        if self.on_change:
            self.on_change(self.stored_value, self.stored_range)
