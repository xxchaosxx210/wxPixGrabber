import wx
import os
import webbrowser
import logging

from gui.about import AnimatedDialog
from gui.settingsdialog import SettingsDialog

from crawler.options import (
    VERSION,
    DEBUG,
    load_settings,
    save_settings
)

import crawler.constants as const
from crawler.constants import CMessage as Message

_Log = logging.getLogger()

ID_OPEN_URL = 101
ID_OPEN_HTML = 102
ID_SAVE = 103
ID_LOAD_SAVE = 104
ID_OPEN_SAVE_PATH = 1041
ID_EXIT = 105

# HELP IDs
ID_ABOUT = 106
ID_HELP_DOC = 107

# GRAB
ID_SCAN_FETCH = 108
ID_SCAN_CANCEL = 109
ID_SCAN_START = 110
ID_SCAN_SETTINGS = 111
ID_SCAN_DEBUG = 112

class PixGrabberMenuBar(wx.MenuBar):

    def __init__(self, parent=None, style=0):
        super().__init__(style=style)
        self.parent = parent
        self.app = wx.GetApp()
        menu = wx.Menu()
        menu.Append(ID_OPEN_URL, "Open Url\tCtrl+U", "Enter a Url address to scan (Ctrl+U)")
        menu.Append(ID_OPEN_HTML, "Open HTML\tCtrl+H", "Open an HTML document from local disk (Ctrl+H)")
        menu.AppendSeparator()
        menu.Append(ID_OPEN_SAVE_PATH, "Open Save Path\tCtrl+Shift+O", "Opens Save Path in Explorer Window (Ctrl+Shift+O)")
        menu.AppendSeparator()
        menu.Append(ID_SAVE, "Save\tCtrl+S", "Saves the last scan (Ctrl+S)")
        menu.Append(ID_LOAD_SAVE, "Load\tCtrl+L", "Load a save (Ctrl+L)")
        menu.AppendSeparator()
        menu.Append(ID_EXIT, "Exit\tCtrl+E", "Close the Program (Ctrl+E)")
        self.Append(menu, "&File")

        menu = wx.Menu()
        if DEBUG:
            menu.Append(ID_SCAN_DEBUG, "Debug\tF8", "Run a test scan (F8)")
        menu.AppendSeparator()
        menu.Append(ID_SCAN_FETCH, "Fetch\tF1", "Fetch Images from Url or file (F1)")
        menu.AppendSeparator()
        menu.Append(ID_SCAN_CANCEL, "Cancel\tF3", "Cancel running Image scan (F3)")
        menu.Append(ID_SCAN_START, "Start\tF5", "Start scanning downloading the images (F5)")
        menu.AppendSeparator()
        menu.Append(ID_SCAN_SETTINGS, "Settings\tCtrl+Shift+S", "Open Settings (Ctrl+Shift+S)")
        self.Append(menu, "S&can")

        menu = wx.Menu()
        menu.Append(ID_HELP_DOC, "Documentation\tCtrl+Shift+H", "A more in depth usage of PixGrabber what it is and what it does (Ctrl+Shift+H)")
        menu.AppendSeparator()
        menu.Append(ID_ABOUT, "About", "About the Program and Developer")
        self.Append(menu, "&Help")   

        parent.Bind(wx.EVT_MENU, self._on_open_url, id=ID_OPEN_URL)
        parent.Bind(wx.EVT_MENU, self._on_open_html, id=ID_OPEN_HTML)
        parent.Bind(wx.EVT_MENU, self._open_save_path, id=ID_OPEN_SAVE_PATH)
        parent.Bind(wx.EVT_MENU, self._on_save_scan, id=ID_SAVE)
        parent.Bind(wx.EVT_MENU, self._on_load_save, id=ID_LOAD_SAVE)
        parent.Bind(wx.EVT_MENU, lambda evt : self.parent.Close(), id=ID_EXIT)

        if DEBUG:
            parent.Bind(wx.EVT_MENU, self._on_debug, id=ID_SCAN_DEBUG)
        parent.Bind(wx.EVT_MENU, self._on_fetch, id=ID_SCAN_FETCH)
        parent.Bind(wx.EVT_MENU, self._on_scan_cancel, id=ID_SCAN_CANCEL)
        parent.Bind(wx.EVT_MENU, self._on_scan_start, id=ID_SCAN_START)
        parent.Bind(wx.EVT_MENU, self._on_settings, id=ID_SCAN_SETTINGS)
        
        parent.Bind(wx.EVT_MENU, self._on_help_document, id=ID_HELP_DOC)
        parent.Bind(wx.EVT_MENU, self._on_about, id=ID_ABOUT)

    def _on_debug(self, evt):
        self.app.commander.queue.put_nowait(
                Message(thread=const.THREAD_MAIN, 
                        event=const.EVENT_FETCH, id=0, 
                        status=const.STATUS_OK, 
                        data={"url": "http://localhost:5000/setup_test"}))

    def _on_fetch(self, evt):
        _Log.info("Fetch Pressed")

    def _on_scan_cancel(self, evt):
        _Log.info("Cancel Pressed")

    def _on_scan_start(self, evt):
        _Log.info("Start Pressed")

    def _on_open_url(self, evt):
        _Log.info("Open URL Pressed")
    
    def _on_open_html(self, evt):
        _Log.info("Open HTML File pressed")
    
    def _on_save_scan(self, evt):
        _Log.info("Save scan pressed")
    
    def _on_load_save(self, evt):
        _Log.info("Load save pressed")
    
    def _on_help_document(self, evt):
        _Log.info("Help documentation pressed")
    
    def _on_about(self, evt):
        dlg = AnimatedDialog(self.parent, -1, "About", 
                            ["PixGrabber", "Paul Millar", "", VERSION])
        dlg.ShowModal()
        dlg.Destroy()
    
    def _on_settings(self, evt):
        dlg = SettingsDialog(parent=self.parent,
                             id= -1,
                             title="Settings",
                             size=wx.DefaultSize,
                             pos=wx.DefaultPosition,
                             style=wx.DEFAULT_DIALOG_STYLE,
                             name="settings_dialog",
                             settings=load_settings())
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.get_settings()
            save_settings(settings)
        dlg.Destroy()
    
    def _open_save_path(self, evt):
        path = load_settings().get("save_path", "")
        if os.path.exists(path):
            webbrowser.open(path)