import wx

from gui.statustreeview import StatusTreeView
from crawler.message import Message
import crawler.message as const

BORDER = 5


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.app = wx.GetApp()

        self.addressbar = AddressBar(self, -1)
        self.treeview = StatusTreeView(self, -1)
        btn_detach = wx.Button(self, -1)
        btn_detach.SetBitmap(self.app.bitmaps["detach"], wx.LEFT)
        btn_detach.SetBitmapMargins((2, 2))
        btn_detach.SetInitialSize()
        self.errors = StatsPanel(parent=self, stat_name="Errors:", stat_value="0")
        self.ignored = StatsPanel(parent=self, stat_name="Ignored:", stat_value="0")
        self.imgsaved = StatsPanel(parent=self, stat_name="Saved:", stat_value="0")
        self.progressbar = ProgressPanel(self, -1)

        btn_detach.Bind(wx.EVT_BUTTON, self._on_detach_button, btn_detach)
        btn_detach.Bind(wx.EVT_ENTER_WINDOW,
                        lambda evt: self.app.window.SetStatusText("Show/Hide Detachable Progress Window"))

        vs = wx.BoxSizer(wx.VERTICAL)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.addressbar, 1, wx.EXPAND | wx.ALL, BORDER)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.treeview, 1, wx.EXPAND | wx.ALL, BORDER)
        vs.Add(hs, 1, wx.EXPAND | wx.ALL, BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.AddSpacer(BORDER)
        hs.Add(btn_detach, 0, wx.EXPAND | wx.ALL, 0)
        hs.AddStretchSpacer(1)
        hs.Add(self.errors, 0, wx.EXPAND | wx.ALL, 2)
        hs.AddSpacer(BORDER)
        hs.Add(self.ignored, 0, wx.EXPAND | wx.ALL, 2)
        hs.AddSpacer(BORDER)
        hs.Add(self.imgsaved, 0, wx.EXPAND | wx.ALL, 2)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 2)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.progressbar, 1, wx.EXPAND | wx.ALL, BORDER)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, BORDER)

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
                Message(thread=const.THREAD_MAIN, event=const.EVENT_FETCH, id=0, status=const.STATUS_OK, data=data))

    def start_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_START, status=const.STATUS_OK, data={}, id=0))

    def stop_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_CANCEL))
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_FETCH_CANCEL))

    def pause_tasks(self):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_PAUSE, data={}, status=const.STATUS_OK))

    def on_btn_open_dir(self, evt):
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


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.app = wx.GetApp()

        self.txt_address = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)

        bitmaps = wx.GetApp().bitmaps
        btn_open = wx.BitmapButton(self, -1, bitmaps["html-file"])

        self.btn_fetch = wx.BitmapButton(self, -1, bitmaps["fetch"])
        self.btn_stop = wx.BitmapButton(self, -1, bitmaps["cancel"])
        self.btn_pause = wx.BitmapButton(self, -1, bitmaps["pause"])
        self.btn_pause.Enable(False)
        self.btn_start = wx.BitmapButton(self, -1, bitmaps["start"])

        self.txt_address.Bind(wx.EVT_TEXT_ENTER, lambda evt: self.GetParent().fetch_link(), self.txt_address)
        self.btn_fetch.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().fetch_link(), self.btn_fetch)
        self.btn_pause.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().pause_tasks(), self.btn_pause)
        self.btn_stop.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().stop_tasks(), self.btn_stop)
        self.btn_start.Bind(wx.EVT_BUTTON, lambda evt: self.GetParent().start_tasks(), self.btn_start)
        btn_open.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_open_dir, btn_open)

        self.set_help_text(self.btn_fetch, "Fetch Links found from the Url")
        self.set_help_text(self.btn_start, "Start scanning the fetched Urls")
        self.set_help_text(self.btn_pause, "Pause the running Tasks")
        self.set_help_text(self.btn_stop, "Stop the current Scan")
        self.set_help_text(self.txt_address, "Enter a Url or File path to go fetch")
        self.set_help_text(btn_open, "Open an HTML file from local drive to go fetch")

        vs = wx.BoxSizer(wx.VERTICAL)

        hs = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Url or HTML File")
        hs.Add(self.txt_address, 1, wx.ALL | wx.EXPAND, 0)
        hs.Add(btn_open, 0, wx.ALL | wx.EXPAND, 0)
        hs.AddSpacer(20)
        hs.Add(self.btn_fetch, 0, wx.ALL | wx.EXPAND, 0)
        hs.Add(self.btn_stop, 0, wx.ALL | wx.EXPAND, 0)
        hs.Add(self.btn_pause, 0, wx.ALL | wx.EXPAND, 0)
        hs.Add(self.btn_start, 0, wx.ALL | wx.EXPAND, 0)

        vs.Add(hs, 1, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(vs)

    def set_help_text(self, button, text):
        button.Bind(wx.EVT_ENTER_WINDOW,
                    lambda evt: self.on_mouse_over_button(text),
                    button)

    def on_mouse_over_button(self, text):
        self.app.window.sbar.SetStatusText(text)


class StatsPanel(wx.Panel):

    def __init__(self, stat_name, stat_value, *args, **kw):
        super().__init__(*args, **kw)

        lbl = wx.StaticText(self, -1, stat_name)
        self.value = wx.StaticText(self, -1, stat_value)

        vs = wx.BoxSizer(wx.VERTICAL)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(lbl, 1, wx.ALL | wx.EXPAND, 0)
        hs.AddSpacer(BORDER)
        hs.Add(self.value, 1, wx.ALL | wx.EXPAND, 0)
        vs.Add(hs, 1, wx.ALL | wx.EXPAND)
        self.SetSizer(vs)

        self.stat = 0

    def reset_stat(self):
        self.stat = 0
        self.value.SetLabel("0")

    def add_stat(self):
        self.stat += 1
        self.value.SetLabel(self.stat.__str__())


class ProgressPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.gauge = wx.Gauge(self, -1, 100, style=wx.GA_HORIZONTAL | wx.GA_PROGRESS | wx.GA_SMOOTH)
        self.time = wx.StaticText(self, -1, "00:00:00")

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Progress")

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 0)
        box.Add(vs, 1, wx.ALL | wx.EXPAND, 0)

        box.AddSpacer(BORDER)

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.time, 1, wx.EXPAND | wx.ALL, 0)
        box.Add(vs, 0, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(box)

    def reset_progress(self, max_range):
        self.gauge.SetRange(max_range)
        self.gauge.SetValue(0)

    def increment(self):
        value = self.gauge.GetValue()
        r = self.gauge.GetRange()
        try:
            self.gauge.SetValue(value + 1)
        except Exception:
            print("")
