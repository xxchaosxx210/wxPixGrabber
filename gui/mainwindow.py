import wx
import logging

from gui.downloadpanel import DownloadPanel

from crawler.constants import CMessage as Message
import crawler.constants as const

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
        self._create_statusbar()
        self._load_icon()

        self.dldpanel = DownloadPanel(parent=self)
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.dldpanel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vs)
        self.SetSize(kw["size"])

        self.Bind(wx.EVT_CLOSE, self.on_close_window)
    
    def _create_statusbar(self):
        self.sbar = wx.StatusBar(parent=self, id=-1)
        font = self.sbar.GetFont()
        font.SetPointSize(12)
        self.sbar.SetFont(font)
        self.sbar.SetFieldsCount(1)
        self.SetStatusBar(self.sbar)
    
    def _load_icon(self):
        icon = wx.Icon()
        icon.CopyFromBitmap(self.app.bitmaps["icon"])
        self.SetIcon(icon)
    
    def _on_timer_callback(self, formatted_time):
        try:
            wx.CallAfter(self.dldpanel.progressbar.time.SetLabel, formatted_time)
        except AssertionError:
            pass
    
    def on_close_window(self, evt):
        timer_quit.set()
        self.app.commander.queue.put(Message(
            thread=const.THREAD_MAIN, event=const.EVENT_QUIT, id=0, data=None, status=const.STATUS_OK))
        self.app.commander.thread.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """Message from the background thread

        Args:
            msg (Message): is a Message object from web.scraper.py
        """
        if msg.thread == const.THREAD_COMMANDER:
            # message
            if msg.event == const.EVENT_MESSAGE:
                self.sbar.SetStatusText(msg.data["message"])
            # All tasks complete
            elif msg.event == const.EVENT_COMPLETE:
                self._on_scraping_complete()
            # fetch has completed
            elif msg.event == const.EVENT_FETCH and msg.status == const.STATUS_OK:
                self._on_fetch_finished(msg)
                self.dldpanel.addressbar.txt_address.SetValue("")
            # fetch error
            elif msg.event == const.EVENT_FETCH and msg.status == const.STATUS_ERROR:
                self.app.sounds["error"].Play()
                self.sbar.SetStatusText(msg.data["message"])
            # started download and loading threads
            elif msg.event == const.EVENT_START and msg.status == const.STATUS_OK:
                self._on_start_scraping(msg)
        
        elif msg.thread == const.THREAD_TASK:
            if msg.event == const.EVENT_FINISHED and msg.status == const.STATUS_OK:
                self.dldpanel.progressbar.increment()
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_ERROR:
                _log.info(f"{msg.data['url']} had an error. Message: {msg.data['message']}")
                self.dldpanel.treeview.add_url(msg)
                self.dldpanel.errors.add_stat()
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_OK:
                self.dldpanel.imgsaved.add_stat()
                self.dldpanel.treeview.add_url(msg)
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_IGNORED:
                self.dldpanel.ignored.add_stat()
                self.dldpanel.treeview.add_url(msg)
            elif msg.event == const.EVENT_SEARCHING and msg.status == const.STATUS_OK:
                self.dldpanel.treeview.set_searching(msg.id)
    
    def _on_start_scraping(self, msg):
        timer_quit.clear()
        self.dldpanel.errors.reset_stat()
        self.dldpanel.ignored.reset_stat()
        self.dldpanel.imgsaved.reset_stat()
        create_timer_thread(self._on_timer_callback).start()
        self.sbar.SetStatusText("Starting Tasks...")
        self.dldpanel.addressbar.btn_fetch.Enable(False)
        self.dldpanel.addressbar.btn_start.Enable(False)
    
    def _on_scraping_complete(self):
        if options.load_settings()["notify-done"]:
            self.app.sounds["complete"].Play()
        # kill the timer thread
        timer_quit.set()
        self.sbar.SetStatusText("All Tasks have completed")
        self.dldpanel.progressbar.reset_progress(0)
        self.dldpanel.addressbar.txt_address.SetValue("")
        self.dldpanel.addressbar.btn_fetch.Enable(True)
        self.dldpanel.addressbar.btn_start.Enable(True)
    
    def _on_fetch_finished(self, msg):
        # Set the progress bar maximum range
        self.sbar.SetStatusText(f"{len(msg.data['urls'])} Links found")
        self.dldpanel.treeview.populate(msg.data["url"], msg.data["urls"])
        self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))
        self.SetTitle(msg.data["title"])
        if msg.data.get("urls", []):
            if options.load_settings()["auto-download"]:
                # start the download automatically no wait
                self.dldpanel.on_start_button(None)
        