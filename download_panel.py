import wx

from app_theme import (
    WX_BORDER,
    WX_BUTTON_SIZE,
    ThemedTextCtrl,
    ThemedButton,
    vboxsizer,
    hboxsizer,
    ThemedStaticText
)

from scraper import (
    notify_commander,
    Message
)

from settings_dialog import SettingsDialog

"""
download_panel:
    Vertical:
        Horizontal:
            addressbar:
                Horizontal:
                    txt_address:
                    btn_fetch:
                    btn_stop:
                    btn_start
"""


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.addressbar = AddressBar(self, -1)
        self.statusbox = StatusPanel(self, -1)
        self.progressbar = ProgressPanel(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)
        
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.addressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.statusbox, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 1, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.progressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        self.SetSizer(vs)

    def on_btn_settings(self, evt):
        dlg = SettingsDialog(parent=self.GetParent(),
                             id= -1,
                             title="Settings",
                             size=wx.DefaultSize,
                             pos=wx.DefaultPosition,
                             style=wx.DEFAULT_DIALOG_STYLE,
                             name="settings_dialog")
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            dlg.save_settings()
        dlg.Destroy()
    
    def on_fetch_button(self, evt):
        if self.addressbar.txt_address.GetValue():
            data = {"url": self.addressbar.txt_address.GetValue()}
            notify_commander(Message(thread="main", type="fetch", data=data))

    def on_start_button(self, evt):
        notify_commander(Message(thread="main", type="start"))

    def on_stop_button(self, evt):
        notify_commander(Message(thread="main", type="cancel"))


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

        self.txt_status = wx.TextCtrl(self, -
        1, 
        "",
        style=wx.TE_READONLY|wx.TE_MULTILINE)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.txt_status, 1, wx.EXPAND|wx.ALL, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Status")
        box.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(box)

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

        