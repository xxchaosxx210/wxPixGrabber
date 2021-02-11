import wx
import time

from download_panel import DownloadPanel

from scraper import (
    create_commander,
    notify_commander,
    Message
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

        self.Bind(wx.EVT_CLOSE, self.on_close_window)

        self.status = self.dldpanel.statusbox.txt_status

        self.commander = create_commander(self.handler_callback)
        self.commander.start()
    
    def on_close_window(self, evt):
        """
        close the running thread and exit
        """
        notify_commander(Message(thread="main", type="quit"))
        self.commander.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """
        callback from background thread
        """
        if msg.thread == "commander":
            if msg.type == "message":
                self.update_status(msg.thread.upper(), msg.data["message"])
            elif msg.type == "complete":
                self.status.SetValue("")
                self.update_status("COMMANDER", "All tasks have completed")
                self.dldpanel.progressbar.reset_progress(0)
            elif msg.type == "fetch" and msg.status == "finished":
                # Set the progress bar maximum range
                self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))

        elif msg.thread == "grunt":
            if msg.type == "image" and msg.status == "ok":
                self.update_status("IMAGE_SAVED", f"{msg.data['pathname']}, {msg.data['url']}")
            elif msg.type == "finished" and msg.status == "complete":
                self.dldpanel.progressbar.increment()
            elif msg.type == "finished" and msg.status == "cancelled":
                self.update_status(f"Thread#{msg.id}", "has cancelled")
                self.dldpanel.progressbar.increment()
                

    def handler_callback(self, msg):
        """
        sends the message from background thread to the main thread.
        I wanted to keep the GUI code seperate from the scraper module
        """
        wx.CallAfter(self.message_from_thread, msg)
    
    def update_status(self, name, text):
        """
        takes in a name of type of message
        display the text with a time code
        will replace this with a listctrl in
        the future
        """
        status = self.status.GetValue()
        if len(status) > 100000:
            status = ""
        status += f"[{time.ctime(time.time())}]{name}: {text}\n" 
        self.status.SetValue(status)
        self.status.ShowPosition(self.status.GetLastPosition())


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