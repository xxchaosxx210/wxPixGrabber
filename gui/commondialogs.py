import wx


class UrlDialog(wx.Dialog):

    def __init__(self, parent: wx.Window, _id: int, size: tuple):
        self.Create(parent=parent, id=_id, title="Enter Url", size=size)

        panel = wx.Panel(self, -1)

        self.text = wx.TextCtrl(panel, -1, "")
        self.text.SetHelpText("Enter a Url to search for images")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        btn_ok = wx.Button(panel, wx.ID_OK, "OK")

        vbox = wx.BoxSizer(wx.VERTICAL)
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        h_box.Add(self.url_text, 1, wx.EXPAND | wx.ALL, 0)
        vbox.Add(h_box, 0, wx.EXPAND | wx.ALL, 0)
        h_box = wx.BoxSizer(wx.HORIZONTAL)
        h_box.Add(btn_cancel, 0, wx.ALIGN_CENTER, 0)
        h_box.Add(btn_ok, 0, wx.ALIGN_CENTER, 0)
        vbox.Add(h_box, 0, wx.ALIGN_CENTER, 0)
        panel.SetSizer(vbox)

        grid_sizer = wx.GridSizer(cols=1, rows=1, hgap=0, vgap=0)
        grid_sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(grid_sizer)