import wx
import time

from download_panel import DownloadPanel

from scraper import (
    create_commander,
    notify_commander
)

class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MainWindow(wx.Frame):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.dldpanel = DownloadPanel(parent=self)
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.dldpanel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vs)
        self.SetSize(kw["size"])

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.status = self.dldpanel.statusbox.txt_status

        commander = create_commander(self.handler_callback)
        commander.start()
    
    def message_from_thread(self, msg):
        if msg.type == "message":
            self.update_status(msg.thread, msg.data["message"])

    def handler_callback(self, msg):
        # notify the main thread
        wx.CallAfter(self.message_from_thread, msg)
    
    def update_status(self, name, text):
        status = self.status.GetValue()
        if len(status) > 1000000:
            status = ""
        status += f"[{time.ctime(time.time())}]{name}: {text}\n" 
        self.status.SetValue(status)


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