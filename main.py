import wx
from wx.adv import Sound
import time

from download_panel import DownloadPanel

from scraper import (
    create_commander,
    notify_commander,
    Message
)

from timer import (
    create_timer_thread,
    timer_quit
)

import clipboard
from global_props import Settings

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

        self.notify_sfx = Sound()
        self.notify_sfx.Create("notification.wav")
    
        self.clipboard = \
            clipboard.ClipboardListener(parent=self, 
                                        callback=self.on_clipboard, 
                                        url_only=True)
        self.clipboard.start()

    def on_clipboard(self, text):
        self.dldpanel.addressbar.txt_address.SetValue(text)
        self.Raise()
    
    def on_timer_callback(self, formatted_time):
        try:
            wx.CallAfter(self.dldpanel.progressbar.time.SetLabel, formatted_time)
        except AssertionError:
            pass
    
    def on_close_window(self, evt):
        """
        close the running thread and exit
        """
        timer_quit.set()
        notify_commander(Message(thread="main", type="quit"))
        self.commander.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """
        callback from background thread
        """
        if msg.thread == "commander":
            # message
            if msg.type == "message":
                self.update_status(msg.thread.upper(), msg.data["message"])
            # All tasks complete
            elif msg.type == "complete":
                if Settings.load()["notify-done"]:
                    self.notify_sfx.Play()
                # kill the timer thread
                timer_quit.set()
                self.update_status("COMMANDER", "All tasks have completed")
                self.dldpanel.progressbar.reset_progress(0)
                self.dldpanel.addressbar.txt_address.SetValue("")
            # fetch has completed
            elif msg.type == "fetch" and msg.status == "finished":
                # Set the progress bar maximum range
                self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))
            # fetch has started
            elif msg.type == "fetch" and msg.status == "started":
                self.status.SetValue("")
            # started download and loading threads
            elif msg.type == "searching" and msg.status == "start":
                timer_quit.clear()
                self.dldpanel.resetstats()
                create_timer_thread(self.on_timer_callback).start()
                self.update_status(msg.thread.upper(), "Starting threads...")
        
        elif msg.thread == "grunt":
            # saved and ok
            if msg.type == "image" and msg.status == "ok":
                #self.update_status("IMAGE_SAVED", f"{msg.data['pathname']}, {msg.data['url']}")
                self.dldpanel.imgsaved.value.SetLabel(str(msg.data["images_saved"]))
            # finished task
            elif msg.type == "finished" and msg.status == "complete":
                self.dldpanel.progressbar.increment()
            # finsihed task by cancelling
            elif msg.type == "finished" and msg.status == "cancelled":
                self.update_status(f"Thread#{msg.id}", "has cancelled")
                self.dldpanel.progressbar.increment()
            # error stat update
            elif msg.type == "stat" and msg.status == "error":
                self.dldpanel.errors.value.SetLabel(str(msg.data["value"]))
            # ignored link update
            elif msg.type == "stat" and msg.status == "ignored":
                self.dldpanel.errors.value.SetLabel(str(msg.data["value"]))
                

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
        #self.status.ShowPosition(self.status.GetLastPosition())


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