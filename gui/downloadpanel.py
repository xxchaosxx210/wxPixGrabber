import wx

from gui.theme import (
    WX_BORDER,
    WX_BUTTON_SIZE,
    ThemedTextCtrl,
    ThemedButton,
    vboxsizer,
    hboxsizer,
    ThemedStaticText
)

from scraper import Message

from gui.settingsdialog import SettingsDialog

from options import Settings


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.addressbar = AddressBar(self, -1)
        self.statusbox = StatusPanel(self, -1)
        self.errors = StatsPanel(parent=self, stat_name="Errors:", stat_value="0")
        self.ignored = StatsPanel(parent=self, stat_name="Ignored:", stat_value="0")
        self.imgsaved = StatsPanel(parent=self, stat_name="Saved:", stat_value="0")
        self.progressbar = ProgressPanel(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)
        
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.addressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.statusbox, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 1, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.AddStretchSpacer(1)
        hs.Add(self.errors, 0, wx.EXPAND|wx.ALL, 2)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.ignored, 0, wx.EXPAND|wx.ALL, 2)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.imgsaved, 0, wx.EXPAND|wx.ALL, 2)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 2)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.progressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        self.SetSizer(vs)
    
    def resetstats(self):
        self.errors.value.SetLabel("0")
        self.imgsaved.value.SetLabel("0")
        self.ignored.value.SetLabel("0")

    def on_btn_settings(self, evt):
        # if listening for clipboard events then
        # dialog won't recive window messages
        self.GetParent().clipboard.stop()
        dlg = SettingsDialog(parent=self.GetParent(),
                             id= -1,
                             title="Settings",
                             size=wx.DefaultSize,
                             pos=wx.DefaultPosition,
                             style=wx.DEFAULT_DIALOG_STYLE,
                             name="settings_dialog",
                             settings=Settings.load())
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.get_settings()
            Settings.save(settings)
        dlg.Destroy()
        # start up the clipboard listener again
        self.GetParent().clipboard.start()
    
    def on_fetch_button(self, evt):
        if self.addressbar.txt_address.GetValue():
            data = {"url": self.addressbar.txt_address.GetValue()}
            self.GetParent().commander_msgbox.put_nowait(
                Message(thread="main", type="fetch", data=data))

    def on_start_button(self, evt):
        self.GetParent().commander_msgbox.put_nowait(
                Message(thread="main", type="start"))

    def on_stop_button(self, evt):
        self.GetParent().commander_msgbox.put_nowait(
            Message(thread="main", type="cancel"))
    
    def reset(self):
        self.imgsaved.value.SetLabel("0")
        self.errors.value.SetLabel("0")
        self.ignored.value.SetLabel("0")
    
    def update_stats(self, saved, ignored, errors):
        self.ignored.value.SetLabel(str(ignored))
        self.imgsaved.value.SetLabel(str(saved))
        self.errors.value.SetLabel(str(errors))


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.txt_address = ThemedTextCtrl(self, -1, "")

        btn_fetch = ThemedButton(self, -1, "Fetch", size=WX_BUTTON_SIZE)
        btn_stop = ThemedButton(self, -1, "Cancel", size=WX_BUTTON_SIZE)
        btn_start = ThemedButton(self, -1, "Start", size=WX_BUTTON_SIZE)
        btn_settings = ThemedButton(self, -1, "Settings", size=WX_BUTTON_SIZE)

        btn_fetch.Bind(wx.EVT_BUTTON, self.GetParent().on_fetch_button, btn_fetch)
        btn_stop.Bind(wx.EVT_BUTTON, self.GetParent().on_stop_button, btn_stop)
        btn_start.Bind(wx.EVT_BUTTON, self.GetParent().on_start_button, btn_start)
        btn_settings.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_settings, btn_settings)

        hs = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Download Url")
        hs.Add(self.txt_address, 1, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_fetch, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_stop, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_start, 0, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(btn_settings, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(hs)

class StatusPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.txt_status = ThemedTextCtrl(self, -
        1, 
        "",
        style=wx.TE_READONLY|wx.TE_MULTILINE)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.txt_status, 1, wx.EXPAND|wx.ALL, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Status")
        box.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(box)


class StatsPanel(wx.Panel):

    def __init__(self, stat_name, stat_value, *args, **kw):
        super().__init__(*args, **kw)

        lbl = wx.StaticText(self, -1, stat_name)
        self.value = wx.StaticText(self, -1, stat_value)

        vs = vboxsizer()
        hs = hboxsizer()
        hs.Add(lbl, 1, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.value, 1, wx.ALL|wx.EXPAND, 0)
        vs.Add(hs, 1, wx.ALL|wx.EXPAND)
        self.SetSizer(vs)
    

class ProgressPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.gauge = wx.Gauge(self, -1, 100)
        self.time = ThemedStaticText(self, -1, "00:00:00")

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Progress")

        vs = vboxsizer()
        vs.Add(self.gauge, 1, wx.EXPAND|wx.ALL, 0)
        box.Add(vs, 1, wx.ALL|wx.EXPAND, 0)

        box.AddSpacer(WX_BORDER)

        vs = vboxsizer()
        vs.Add(self.time, 1, wx.EXPAND|wx.ALL, 0)
        box.Add(vs, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(box)
    
    def reset_progress(self, max_range):
        self.gauge.SetRange(max_range)
        self.gauge.SetValue(0)
    
    def increment(self):
        value = self.gauge.GetValue()
        self.gauge.SetValue(value + 1)

        