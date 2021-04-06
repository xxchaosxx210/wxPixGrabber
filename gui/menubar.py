import wx
import os
import webbrowser
import logging

from gui.bubbledialog import BubbleDialog
from gui.settingsdialog import SettingsDialog

from collections import namedtuple

from crawler.options import (
    VERSION,
    GIT_SOURCE,
    DEBUG,
    load_settings,
    save_settings,
    load_profiles,
    use_profile
)

import crawler.message as const
from crawler.message import Message

_Log = logging.getLogger()

ProfileSubMenuItem = namedtuple("ProfileSubMenuItem", ["id", "name"])

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
ID_PROFILES = 113


def _open_save_path():
    path = load_settings().get("save_path", "")
    if os.path.exists(path):
        webbrowser.open(path)


class PixGrabberMenuBar(wx.MenuBar):

    def __init__(self, parent=None, style=0):
        super().__init__(style=style)
        self.parent = parent
        self.app = wx.GetApp()

        self._profile_ids = []

        menu = wx.Menu()
        menu.Append(ID_OPEN_HTML, "Open HTML\tCtrl+H", "Open an HTML document from local disk (Ctrl+H)")
        menu.AppendSeparator()
        menu.Append(ID_OPEN_SAVE_PATH, "Open Save Path\tCtrl+Shift+O",
                    "Opens Save Path in Explorer Window (Ctrl+Shift+O)")
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
        menu.AppendSeparator()
        self.profiles_submenu = wx.Menu()
        self.create_profiles_submenu()
        menu.Append(ID_PROFILES, "Profiles", subMenu=self.profiles_submenu, helpString="Load Profile Settings")
        self.Append(menu, "S&can")

        menu = wx.Menu()
        menu.Append(ID_HELP_DOC, "Documentation\tCtrl+Shift+H",
                    "A more in depth usage of PixGrabber what it is and what it does (Ctrl+Shift+H)")
        menu.AppendSeparator()
        menu.Append(ID_ABOUT, "About", "About the Program and Developer")
        self.Append(menu, "&Help")   

        parent.Bind(wx.EVT_MENU, self._on_open_html, id=ID_OPEN_HTML)
        parent.Bind(wx.EVT_MENU, lambda evt: _open_save_path(), id=ID_OPEN_SAVE_PATH)
        parent.Bind(wx.EVT_MENU, lambda evt: self._on_save_scan(), id=ID_SAVE)
        parent.Bind(wx.EVT_MENU, self._on_load_save, id=ID_LOAD_SAVE)
        parent.Bind(wx.EVT_MENU, lambda evt: self.parent.Close(), id=ID_EXIT)

        if DEBUG:
            parent.Bind(wx.EVT_MENU, self._on_debug, id=ID_SCAN_DEBUG)
        parent.Bind(wx.EVT_MENU, self._on_fetch, id=ID_SCAN_FETCH)
        parent.Bind(wx.EVT_MENU, self._on_scan_cancel, id=ID_SCAN_CANCEL)
        parent.Bind(wx.EVT_MENU, self._on_scan_start, id=ID_SCAN_START)
        parent.Bind(wx.EVT_MENU, self._on_settings, id=ID_SCAN_SETTINGS)
        
        parent.Bind(wx.EVT_MENU, lambda evt: webbrowser.open("README.md"), id=ID_HELP_DOC)
        parent.Bind(wx.EVT_MENU, self._on_about, id=ID_ABOUT)
    
    def create_profiles_submenu(self):
        # loop through any menus still attached and delete
        for profile in self._profile_ids:
            self.profiles_submenu.Delete(profile.id)
        # set the list to default and add 9999 as default ID
        self._profile_ids = [ProfileSubMenuItem(9999, "default")]
        # put the default at the top
        self.profiles_submenu.Append(self._profile_ids[-1].id, self._profile_ids[-1].name, kind=wx.ITEM_RADIO)
        self.profiles_submenu.Check(self._profile_ids[-1].id, True)
        self.parent.Bind(wx.EVT_MENU, self._on_load_profile, id=self._profile_ids[-1].id)
        profiles = load_profiles()
        for profile_index, profile_name in enumerate(profiles):
            if profile_name not in "default":
                self._profile_ids.append(ProfileSubMenuItem(profile_index+10000, profile_name))
                p = self._profile_ids[-1]
                self.profiles_submenu.Append(p.id, p.name, kind=wx.ITEM_RADIO)
                self.parent.Bind(wx.EVT_MENU, self._on_load_profile, id=p.id)
        settings = load_settings()
        selected_profile = list(filter(lambda p: p.name == settings["profile-name"], self._profile_ids))[0]
        self.profiles_submenu.Check(selected_profile.id, True)

    def _on_load_profile(self, evt):
        name = evt.GetEventObject().GetLabelText(evt.Id)
        use_profile(name)
        self.app.window.set_profile_status(name)

    def _on_debug(self, evt):
        self.app.commander.queue.put_nowait(
                Message(thread=const.THREAD_MAIN, 
                        event=const.EVENT_FETCH, id=0,
                        status=const.STATUS_OK, 
                        data={"url": "http://localhost:5000/setup_test"}))

    def _on_fetch(self, evt):
        self.app.window.dld_panel.fetch_link()

    def _on_scan_cancel(self, evt):
        self.app.window.dld_panel.stop_tasks()

    def _on_scan_start(self, evt):
        self.app.window.dld_panel.start_tasks()
    
    def _on_open_html(self, evt):
        dlg = wx.FileDialog(
            parent=self, message="Choose an HTML Document to Search",
            wildcard="(*.html,*.xhtml)|*.html;*.xhtml",
            style=-wx.FD_FILE_MUST_EXIST | wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.app.window.dld_panel.set_address_bar(dlg.GetPaths()[0])
        dlg.Destroy()
    
    def _on_save_scan(self):
        tree_view = self.app.window.dld_panel.treeview
        root = tree_view.GetRootItem()
        for child in tree_view.get_children(root):
            for child2 in tree_view.get_children(child):
                msg = tree_view.GetItemData(child2)
                _Log.info(f"data={msg.data}")
            _Log.info(f"{child}")
    
    def _on_load_save(self, evt):
        _Log.info("Load save pressed")
    
    def _on_about(self, evt):
        dlg = BubbleDialog(self.parent, -1, "About",
                            ["PixGrabber(c)", "Developed by Paul Millar", GIT_SOURCE, VERSION],
                           size=(640, 480))
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
            self.create_profiles_submenu()
        dlg.Destroy()
