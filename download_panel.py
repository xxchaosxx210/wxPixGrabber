import wx

class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.txt_address = wx.TextCtrl(self, -1, "")

        btn_fetch = wx.Button(self, -1, "Fetch", size=(120, -1))
        btn_stop = wx.Button(self, -1, "Cancel", size=(120, -1))
        btn_start = wx.Button(self, -1, "Start", size=(120, -1))