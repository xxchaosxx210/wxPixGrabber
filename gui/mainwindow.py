import wx

from gui.downloadpanel import DownloadPanel
from gui.menubar import PixGrabberMenuBar
import gui.notificationbar as notify
from gui.detachprogress import DetachableFrame

from crawler.message import Message
import crawler.message as const

import crawler.options as options

from timer import (
    create_timer_thread,
    timer_quit
)


class MainWindow(wx.Frame):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.app = wx.GetApp()
        self._create_statusbar()
        self._load_icon()
        self.SetMenuBar(PixGrabberMenuBar(parent=self))

        self.dldpanel = DownloadPanel(parent=self)
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.dldpanel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vs)
        self.SetSize(kw["size"])

        self.Bind(wx.EVT_CLOSE, self.on_close_window)

        # detach status frame
        self.detached_frame = DetachableFrame(self, -1, "")

    def _create_statusbar(self):
        self.sbar = wx.StatusBar(parent=self, id=-1)
        font = self.sbar.GetFont()
        font.SetPointSize(10)
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
        self.detached_frame.Destroy()
        self.app.commander.queue.put(Message(
            thread=const.THREAD_MAIN, event=const.EVENT_QUIT, _id=0, data=None, status=const.STATUS_OK))
        self.app.commander.thread.join()
        evt.Skip()
    
    def message_from_thread(self, msg):
        """Message from the background thread

        Args:
            msg (Message): is a Message object
                    Message: thread  (int): thread which sent the message
                             event   (int): the type of message
                             id      (int): this is only used if a task process has sent the message
                             status  (int): the status of the message either STATUS_OK, STATUS_ERROR or STATUS_IGNORED
                             data   (dict): extra information depending on the message event
        """
        if msg.thread == const.THREAD_COMMANDER:
            # MESSAGE
            if msg.event == const.EVENT_MESSAGE:
                self.sbar.SetStatusText(msg.data["message"])

            # ALL TASKS COMPLETED
            elif msg.event == const.EVENT_COMPLETE:
                self._on_scraping_complete()

            # FETCH HAS COMPLETED
            elif msg.event == const.EVENT_FETCH and msg.status == const.STATUS_OK:
                self._on_fetch_finished(msg)
                self.dldpanel.treeview.populate(msg)
                self.dldpanel.addressbar.txt_address.SetValue("")
            # FETCH ERROR
            elif msg.event == const.EVENT_FETCH and msg.status == const.STATUS_ERROR:
                self._on_fetch_error(msg)
            # FETCH IGNORED
            elif msg.event == const.EVENT_FETCH and msg.status == const.STATUS_IGNORED:
                self._on_fetch_ignored(msg)
            # TASKS HAVE BEEN CREATED AND ARE NOW SEARCHING
            elif msg.event == const.EVENT_START and msg.status == const.STATUS_OK:
                self._on_start_scraping(msg)
        
        elif msg.thread == const.THREAD_TASK:
            # TASK HAS COMPLETED
            if msg.event == const.EVENT_FINISHED:
                self.dldpanel.progressbar.increment()
                self.dldpanel.treeview.child_complete(msg)
                self.detached_frame.add_progress()
            # IMAGE ERRROR
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_ERROR:
                self.dldpanel.treeview.add_url(msg)
                self.dldpanel.errors.add_stat()
                self.detached_frame.add_error()
            # IMAGE SAVED
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_OK:
                self.dldpanel.imgsaved.add_stat()
                self.detached_frame.add_saved()
                self.dldpanel.treeview.add_url(msg)
            # IMAGE IGNORED
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_IGNORED:
                self.dldpanel.ignored.add_stat()
                self.dldpanel.treeview.add_url(msg)
                self.detached_frame.add_ignored()
            # TASK HAS STARTED
            elif msg.event == const.EVENT_SEARCHING and msg.status == const.STATUS_OK:
                self.dldpanel.treeview.set_searching(msg.id)
                if self.is_detachable():
                    self.detached_frame.Show()
                else:
                    self.detached_frame.Hide()
    
    def _on_start_scraping(self, msg):
        # Start a new timer
        timer_quit.clear()
        create_timer_thread(self._on_timer_callback).start()
        # Reset the stats on teh download panel
        self.dldpanel.errors.reset_stat()
        self.dldpanel.ignored.reset_stat()
        self.dldpanel.imgsaved.reset_stat()
        self.sbar.SetStatusText("Starting Tasks...")
        # disable the fetch and start buttons while searching
        self.dldpanel.enable_controls(False)
    
    def _on_scraping_complete(self):
        self.detached_frame.Hide()
        # play the notification sound if required
        if options.load_settings()["notify-done"]:
            self.app.sounds["complete"].Play()
            notify.NotificationBar(self, -1, "", "PixGrabber has completed", timeout=notify.NOTIFY_LONG)
        # kill the timer thread
        timer_quit.set()
        self.sbar.SetStatusText("All Tasks have completed")
        self.dldpanel.progressbar.reset_progress(0)
        self.dldpanel.addressbar.txt_address.SetValue("")
        self.dldpanel.enable_controls(True)
    
    def _on_fetch_finished(self, msg):
        self.sbar.SetStatusText(f"{len(msg.data['urls'])} Links found")
        # Set the progress bar maximum range
        self.dldpanel.progressbar.reset_progress(len(msg.data.get("urls")))
        self.detached_frame.reset(len(msg.data.get("urls", [])))
        # set Frame title from fetched Url title. similar to how a Browser behaves
        # we will use this to generate a unique folder name
        self.SetTitle(msg.data["title"])
        if msg.data.get("urls", []):
            if options.load_settings()["auto-download"]:
                # start the download automatically no wait
                self.dldpanel.on_start_button(None)
    
    def _on_fetch_error(self, msg):
        self.app.sounds["error"].Play()
        self.dldpanel.treeview.clear()
        root = self.dldpanel.treeview.AddRoot(msg.data["url"])
        error = self.dldpanel.treeview._img_error
        self.dldpanel.treeview.SetItemData(root, msg)
        self.dldpanel.treeview.SetItemImage(root, error, wx.TreeItemIcon_Normal)
        self.dldpanel.treeview.SetItemImage(root, error, wx.TreeItemIcon_Expanded)
        self.dldpanel.treeview.AppendItem(root, msg.data["message"])
    
    def _on_fetch_ignored(self, msg):
        self.app.sounds["error"].Play()
        self.sbar.SetStatusText(msg.data["message"])
    
    def is_detachable(self):
        return options.load_settings().get("detach-progress", True)
        