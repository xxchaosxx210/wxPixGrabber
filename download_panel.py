import wx

from app_theme import (
    WX_BORDER,
    WX_BUTTON_SIZE,
    ThemedStaticText,
    ThemedButton
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


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.txt_address = ThemedStaticText(self, -1, "")

        btn_fetch = ThemedButton(self, -1, "Fetch", size=WX_BUTTON_SIZE)
        btn_stop = ThemedButton(self, -1, "Cancel", size=WX_BUTTON_SIZE)
        btn_start = ThemedButton(self, -1, "Start", size=WX_BUTTON_SIZE)
        btn_settings = ThemedButton(self, -1, "Settings", size=WX_BUTTON_SIZE)

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
        "Ready to Fetch...",
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
        self.gauge.SetValue(50)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.gauge, 1, wx.EXPAND|wx.ALL, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Progress")
        box.Add(hs, 1, wx.ALL|wx.EXPAND, 0)
        self.SetSizer(box)

        