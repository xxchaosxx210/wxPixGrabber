import wx
import threading

import crawler.message as const
import gui.notificationbar as notify
import crawler.options as options

from gui.downloadpanel import DownloadPanel
from gui.menubar import PixGrabberMenuBar
from gui.detachprogress import DetachableFrame
from gui.fetchdialog import FetchDialog
from crawler.message import Message
from timer import (
    create_timer_thread,
    timer_quit
)


class MainWindow(wx.Frame):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.app = wx.GetApp()
        self._create_status_bar()
        self._load_icon()
        self.SetMenuBar(PixGrabberMenuBar(parent=self))
        self._fetch_dlg = None

        self.dld_panel = DownloadPanel(parent=self)
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(self.dld_panel, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vs)
        self.SetSize(kw["size"])

        self.Bind(wx.EVT_CLOSE, self.on_close_window)

        # detach status frame
        self.detached_frame = DetachableFrame(self, -1, "")

    def set_profile_status(self, profile_name: str):
        self.SetStatusText(f"Profile: {profile_name}", 1)

    def _create_status_bar(self):
        self.sbar = wx.StatusBar(parent=self, id=-1)
        font = self.sbar.GetFont()
        font.SetPointSize(10)
        self.sbar.SetFont(font)
        self.sbar.SetFieldsCount(2, [-2, -1])
        self.SetStatusBar(self.sbar)
        self.set_profile_status(options.load_settings()["profile-name"])
    
    def _load_icon(self):
        icon = wx.Icon()
        icon.CopyFromBitmap(self.app.bitmaps["icon"])
        self.SetIcon(icon)
    
    def _on_timer_callback(self, formatted_time):
        try:
            wx.CallAfter(self.dld_panel.progressbar.time.SetLabel, formatted_time)
        except AssertionError:
            pass
    
    def on_close_window(self, evt):
        timer_quit.set()
        self.detached_frame.Destroy()
        self.app.commander.queue.put(Message(
            thread=const.THREAD_MAIN, event=const.EVENT_QUIT, id=0, data={}, status=const.STATUS_OK))
        self.app.commander.join()
        evt.Skip()
    
    def message_from_thread(self, msg: Message):
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
                self.SetStatusText(msg.data["message"])

            # ALL TASKS COMPLETED
            elif msg.event == const.EVENT_COMPLETE:
                self._on_scraping_complete()

            elif msg.event == const.EVENT_FETCH:
                self.dld_panel.treeview.add_to_root(msg)

            elif msg.event == const.EVENT_FETCH_START:
                self.SetTitle(f'{msg.data["title"]}')
                self.dld_panel.treeview.create_root(msg)
                self._fetch_dlg = FetchDialog(self, -1, msg.data["url"])
                threading.Thread(target=self._fetch_dlg.ShowModal).start()

            elif msg.event == const.EVENT_FETCH_COMPLETE and msg.status == const.STATUS_OK:
                self._fetch_dlg.Destroy()
                self._on_fetch_finished(msg)
                self.dld_panel.addressbar.txt_address.SetValue("")
            # FETCH ERROR
            elif msg.event == const.EVENT_FETCH_COMPLETE and msg.status == const.STATUS_ERROR:
                self._fetch_dlg.Destroy()
                self._on_fetch_error(msg)
            # FETCH IGNORED
            elif msg.event == const.EVENT_FETCH_COMPLETE and msg.status == const.STATUS_IGNORED:
                self._fetch_dlg.Destroy()
                self._on_fetch_ignored(msg)

            # TASKS HAVE BEEN CREATED AND ARE NOW SEARCHING
            elif msg.event == const.EVENT_START and msg.status == const.STATUS_OK:
                self._on_start_scraping()
        
        elif msg.thread == const.THREAD_TASK:
            # TASK HAS COMPLETED
            if msg.event == const.EVENT_FINISHED:
                self.dld_panel.progressbar.increment()
                self.dld_panel.treeview.child_complete(msg)
                self.detached_frame.add_progress()
            # IMAGE ERROR
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_ERROR:
                self.dld_panel.treeview.add_url(msg)
                self.dld_panel.errors.add_stat()
                self.detached_frame.add_error()
            # IMAGE SAVED
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_OK:
                self.dld_panel.imgsaved.add_stat()
                self.detached_frame.add_saved()
                self.dld_panel.treeview.add_url(msg)
            # IMAGE IGNORED
            elif msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_IGNORED:
                self.dld_panel.ignored.add_stat()
                self.dld_panel.treeview.add_url(msg)
                self.detached_frame.add_ignored()
            # TASK HAS STARTED
            elif msg.event == const.EVENT_SEARCHING and msg.status == const.STATUS_OK:
                self.dld_panel.treeview.set_searching(msg.id)
                # Detach Progress frame if option set
                if options.load_settings().get("detach-progress", True):
                    self.detached_frame.Show()
                else:
                    self.detached_frame.Hide()
    
    def _on_start_scraping(self):
        # Start a new timer
        timer_quit.clear()
        create_timer_thread(self._on_timer_callback).start()
        # Reset the stats on teh download panel
        self.dld_panel.errors.reset_stat()
        self.dld_panel.ignored.reset_stat()
        self.dld_panel.imgsaved.reset_stat()
        self.SetStatusText("Starting Tasks...")
        # disable the fetch and start buttons while searching
        self.dld_panel.enable_controls(False)
    
    def _on_scraping_complete(self):
        self.detached_frame.Hide()
        # play the notification sound if required
        if options.load_settings()["notify-done"]:
            self.app.sounds["complete"].Play()
            notify.NotificationBar(None, -1, "", "PixGrabber has completed", timeout=notify.NOTIFY_LONG)
        # kill the timer thread
        timer_quit.set()
        self.SetStatusText("All Tasks have completed")
        self.dld_panel.progressbar.reset_progress(0)
        self.dld_panel.addressbar.txt_address.SetValue("")
        self.dld_panel.enable_controls(True)
    
    def _on_fetch_finished(self, msg: Message):
        urls_length = msg.data["length"]
        self.SetStatusText(f"{urls_length} Links found")
        # Set the progress bar maximum range
        self.dld_panel.progressbar.reset_progress(urls_length)
        self.detached_frame.reset(urls_length)
        # set Frame title from fetched Url title. similar to how a Browser behaves
        # we will use this to generate a unique folder name
        self.SetTitle(f'{msg.data["title"]} - Links found: {urls_length}')
        if urls_length > 0:
            self.dld_panel.treeview.Expand(self.dld_panel.treeview.GetRootItem())
            if options.load_settings()["auto-download"]:
                # start the download automatically no wait
                self.dld_panel.start_tasks()
    
    def _on_fetch_error(self, msg: Message):
        self.app.sounds["error"].Play()
        self.dld_panel.treeview.clear()
        root = self.dld_panel.treeview.AddRoot(msg.data["url"])
        error = self.dld_panel.treeview._img_error
        self.dld_panel.treeview.SetItemData(root, msg)
        self.dld_panel.treeview.SetItemImage(root, error, wx.TreeItemIcon_Normal)
        self.dld_panel.treeview.SetItemImage(root, error, wx.TreeItemIcon_Expanded)
        self.dld_panel.treeview.AppendItem(root, msg.data["message"])
    
    def _on_fetch_ignored(self, msg: Message):
        self.app.sounds["error"].Play()
        self.SetStatusText(msg.data["message"])
