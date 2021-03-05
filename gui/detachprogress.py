import wx

class DetachableFrame(wx.Frame):

    def __init__(self, parent, id, title="", range=100):
        super().__init__(parent, id, title, style=wx.STAY_ON_TOP)
        width, height = (300, 100)
        d_width, d_height = wx.DisplaySize()
        self.SetPosition(wx.Point(d_width-width, d_height-height-100))
        self.panel = ProgressPanel(self, -1, range)
        g = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        g.Add(self.panel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(g)

        self.SetSize((width, height))
    
    def add_error(self):
        self.panel.error.SetLabel(
            str(int(self.panel.error.GetLabel())+1))
    
    def add_saved(self):
        self.panel.saved.SetLabel(
            str(int(self.panel.saved.GetLabel())+1))
    
    def add_ignored(self):
        self.panel.ignored.SetLabel(
            str(int(self.panel.ignored.GetLabel())+1))
    
    def add_progress(self):
        self.panel.progress.SetValue(self.panel.progress.GetValue()+1)


class ProgressPanel(wx.Panel):

    def __init__(self, parent, id, range):
        super().__init__(parent, id)

        self.progress = wx.Gauge(self, -1, range)
        lbl_saved = wx.StaticText(self, -1, "Saved: ")
        self.saved = wx.StaticText(self, -1, "0")
        lbl_error = wx.StaticText(self, -1, "Errors: ")
        self.error = wx.StaticText(self, -1, "0")
        lbl_ignore = wx.StaticText(self, -1, "Ignored: ")
        self.ignored = wx.StaticText(self, -1, "0")

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.progress, 1, wx.EXPAND|wx.ALL, 0)
        vbox.Add(hbox, 1, wx.EXPAND|wx.ALL, 0)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        for label in (lbl_error, self.error, lbl_ignore, self.ignored, lbl_saved, self.saved):
            hbox.Add(label, 0, wx.ALIGN_CENTER, 0)
            hbox.AddSpacer(20)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER, 0)
        self.SetSizer(vbox)