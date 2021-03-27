import wx

from timer import (
    create_timer_thread,
    timer_quit
)


class FetchDialog(wx.Dialog):

    def __init__(self, parent: wx.Frame, _id: int, title: str):
        super().__init__()
        self.Create(parent=parent, id=_id, title=title, size=(640, 200))

        panel = wx.Panel(self, -1)
        label = wx.StaticText(panel, -1, "Scanning Web Document for images. Please wait...")
        self.time_lbl = wx.StaticText(panel, -1, "Time Elapsed: 00:00:00")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")

        self.Bind(wx.EVT_WINDOW_DESTROY, lambda evt: timer_quit.set(), self)

        border = 10

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(border)
        hbox.Add(label, 1, wx.EXPAND|wx.ALL, 0)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, border)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(border)
        hbox.Add(self.time_lbl, 1, wx.EXPAND | wx.ALL, 0)
        vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, border)
        vbox.AddStretchSpacer(1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(cancel_btn, 0, wx.ALL|wx.EXPAND, 0)
        hbox.AddSpacer(border)
        vbox.Add(hbox, 0, wx.ALIGN_RIGHT, border)
        vbox.AddSpacer(border)
        panel.SetSizer(vbox)

        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(panel, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(gs)

        self.CentreOnParent()

    def ShowModal(self):
        timer_quit.clear()
        create_timer_thread(self._on_update_time).start()
        super().ShowModal()

    def _on_update_time(self, t: str):
        self.time_lbl.SetLabel(f"Time Elapsed: {t}")


def test():
    class TestFrame(wx.Frame):
        def __init__(self):
            super().__init__(None, -1, "Test Dialog")
            btn = wx.Button(self, -1, "Launch", size=(100, 30))
            btn.Bind(wx.EVT_BUTTON, self._on_dialog, btn)
            g = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
            g.Add(btn, 1, wx.EXPAND | wx.ALL, 0)
            self.SetSizerAndFit(g)

        def _on_dialog(self, evt):
            dlg = FetchDialog(self, -1, "Scanning http://www.facebook.com/user/joe-bloggs")
            dlg.ShowModal()
            dlg.Destroy()

    app = wx.App()
    TestFrame().Show()
    app.MainLoop()


if __name__ == '__main__':
    test()
