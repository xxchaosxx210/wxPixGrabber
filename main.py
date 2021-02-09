import wx

from download_panel import DownloadPanel


class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MainWindow(wx.Frame):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.dldpanel = DownloadPanel(parent=self)
        sizer = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        sizer.Add(self.dldpanel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(sizer)
        self.SetSize(kw["size"])


def _main():
    app = PixGrabberApp()
    window = MainWindow(
        parent=None,
        id=-1,
        title="PixGrabber", 
        size=(800, 600))
    window.Show()
    app.MainLoop()

if __name__ == '__main__':
    _main()