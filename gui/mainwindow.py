import wx
import time
import logging

from gui.downloadpanel import DownloadPanel

from crawler.types import Message

import crawler.options as options

from timer import (
    create_timer_thread,
    timer_quit
)

_log = logging.getLogger(__name__)


class MainWindow(wx.Frame):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.app = wx.GetApp()

        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(self.app.bitmaps["icon"])
        self.SetIcon(icon)

        self.dldpanel = DownloadPanel(parent=self)
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.dldpanel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vs)
        self.SetSize(kw["size"])

        self.Bind(wx.EVT_CLOSE, self.on_close_window)

        self.status = self.dldpanel.statusbox.txt_status

    def on_clipboard(self, text):
        """Function handler which recieves text from the Cllpboard

        Args:
            text (str): the text recieved from the Clipboard listener
        """
        if options.load_settings()["notify-done"]:
            self.app.sounds["clipboard"].Play()
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
        timer_quit.set()
        self.app.commander.queue.put(Message(thread="main", type="quit"))
        self.app.commander.thread.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """Message from the background thread

        Args:
            msg (Message): is a Message object from web.scraper.py
        """
        if msg.thread == "commander":
            # message
            if msg.type == "message":
                self.update_status(msg.thread.upper(), msg.data["message"])
            # All tasks complete
            elif msg.type == "complete":
                self._on_scraping_complete()
            # fetch has completed
            elif msg.type == "fetch" and msg.status == "finished":
                self._on_fetch_finished(msg)
            # fetch error
            elif msg.type == "fetch" and msg.status == "error":
                self.app.sounds["error"].Play()
                self.update_status("COMMANDER", msg.data["message"])
            # fetch has started
            elif msg.type == "fetch" and msg.status == "started":
                self.status.SetValue("")
            # started download and loading threads
            elif msg.type == "searching" and msg.status == "start":
                self._on_start_scraping(msg)
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
    
    def _on_start_scraping(self, msg):
        timer_quit.clear()
        self.dldpanel.resetstats()
        create_timer_thread(self._on_timer_callback).start()
        self.update_status(msg.thread.upper(), "Starting threads...")
        self.dldpanel.addressbar.btn_fetch.Enable(False)
        self.dldpanel.addressbar.btn_start.Enable(False)
    
    def _on_scraping_complete(self):
        if options.load_settings()["notify-done"]:
            self.app.sounds["complete"].Play()
            self.Raise()
        # kill the timer thread
        timer_quit.set()
        self.update_status("COMMANDER", "All tasks have completed")
        self.dldpanel.progressbar.reset_progress(0)
        self.dldpanel.addressbar.txt_address.SetValue("")
        self.dldpanel.addressbar.btn_fetch.Enable(True)
        self.dldpanel.addressbar.btn_start.Enable(True)
    
    def _on_fetch_finished(self, msg):
        # Set the progress bar maximum range
        self.update_status("COMMANDER", f"{len(msg.data['urls'])} Links found")
        self.update_status("COMMANDER", "Press Start to start scanning for images...")
        self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))
        self.SetTitle(msg.data["title"])
        if msg.data.get("urls", []):
            if options.load_settings()["auto-download"]:
                # start the download automatically no wait
                self.dldpanel.on_start_button(None)

    def handler_callback(self, msg):
        """Sends the message from background thread to main thread

        Args:
            msg (Message): A Message class found in web.scraper.py
        """
        wx.CallAfter(self.message_from_thread, msg)
    
    def update_status(self, name, text):
        """displays output to the status textctrl
        doesn't allow more than 100MB of text in the buffer

        Args:
            name (str): The name of the Thread or Process that is sending the update
            text (text): The message of the update to display in the textctrl
        """
        status = self.status.GetValue()
        if len(status) > 100000:
            status = ""
        status += f"[{time.ctime(time.time())}]{name}: {text}\n" 
        self.status.SetValue(status)