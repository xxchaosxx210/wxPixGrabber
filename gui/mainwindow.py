import wx
import time
import multiprocessing as mp
import logging

from gui.downloadpanel import DownloadPanel

from web.scraper import (
    create_commander,
    Message
)
import web.options as options

from timer import (
    create_timer_thread,
    timer_quit
)

import clipboard

from resources.sfx import load_sounds


_log = logging.getLogger(__name__)


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

        self.commander_msgbox = mp.Queue()
        self.commander = create_commander(self.handler_callback, 
                                          self.commander_msgbox)
        self.commander.start()

        self.sfx = load_sounds()

        # keep a reference to the clipboard, there is a bug in that when the clipboard
        # listener is running, it captures win32 messages before they get to the wx event loop
        # for some reason messages are not being passed onto Dialog windows
        # so Dialogs are unresponsive so I patched it by closing the clipboard listener
        # when a Dialog is open. This leads to a bug when I start the listener again it
        # recaptures the last text on the clipboard. so a simple if condition makes sure the
        # text isnt sent to the textctrl address again
        self.clipboard = \
            clipboard.ClipboardListener(parent=self, 
                                        callback=self.on_clipboard, 
                                        url_only=True)
        self.clipboard.start()

    def on_clipboard(self, text):
        self.sfx.clipboard.Play()
        self.dldpanel.addressbar.txt_address.SetValue(text)
        if options.load_settings()["auto-download"]:
            self.dldpanel.on_fetch_button(None)
        else:
            # bring the window to the foreground
            self.Raise()
        _log.info(f"{text} added from Clipboard")

    
    def _on_timer_callback(self, formatted_time):
        try:
            wx.CallAfter(self.dldpanel.progressbar.time.SetLabel, formatted_time)
        except AssertionError:
            pass
    
    def on_close_window(self, evt):
        """
        close the running thread and exit
        """
        timer_quit.set()
        self.commander_msgbox.put(Message(thread="main", type="quit"))
        self.commander.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """
        msg - Message
            thread - the name of the calling thread. Either: grunt or commander
            type   - the type of message
        """
        if msg.thread == "commander":
            # message
            if msg.type == "message":
                self.update_status(msg.thread.upper(), msg.data["message"])
            # All tasks complete
            elif msg.type == "complete":
                if options.load_settings()["notify-done"]:
                    self.sfx.complete.Play()
                    self.Raise()
                # kill the timer thread
                timer_quit.set()
                self.update_status("COMMANDER", "All tasks have completed")
                self.dldpanel.progressbar.reset_progress(0)
                self.dldpanel.addressbar.txt_address.SetValue("")
            # fetch has completed
            elif msg.type == "fetch" and msg.status == "finished":
                # Set the progress bar maximum range
                self.update_status("COMMANDER", f"{len(msg.data['urls'])} Links found")
                self.update_status("COMMANDER", "Press Start to start scanning for images...")
                self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))
                if msg.data.get("urls", []):
                    if options.load_settings()["auto-download"]:
                        # start the download automatically no wait
                        self.dldpanel.on_start_button(None)

            # fetch has started
            elif msg.type == "fetch" and msg.status == "started":
                self.status.SetValue("")
            # started download and loading threads
            elif msg.type == "searching" and msg.status == "start":
                timer_quit.clear()
                self.dldpanel.resetstats()
                create_timer_thread(self._on_timer_callback).start()
                self.update_status(msg.thread.upper(), "Starting threads...")
            
            # error stat update
            elif msg.type == "stat-update":
                stats = msg.data["stats"]
                self.dldpanel.update_stats(stats.saved, stats.ignored, stats.errors)
        
        elif msg.thread == "grunt":
            # saved and ok
            if msg.type == "image" and msg.status == "ok":
                #self.update_status("IMAGE_SAVED", f"{msg.data['pathname']}, {msg.data['url']}")
                self.dldpanel.imgsaved.value.SetLabel(str(msg.data["images_saved"]))
            # finished task
            elif msg.type == "finished" and msg.status == "complete":
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