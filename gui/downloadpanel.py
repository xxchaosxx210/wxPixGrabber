import wx
import webbrowser

from gui.theme import (
    WX_BORDER,
    ThemedTextCtrl,
    vboxsizer,
    hboxsizer,
    ThemedStaticText
)

from crawler.constants import CMessage as Message
import crawler.constants as const
import crawler.options as options

from gui.settingsdialog import SettingsDialog


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.app = wx.GetApp()

        self.addressbar = AddressBar(self, -1)
        self.treeview = StatusTreeView(self, -1)
        self.errors = StatsPanel(parent=self, stat_name="Errors:", stat_value="0")
        self.ignored = StatsPanel(parent=self, stat_name="Ignored:", stat_value="0")
        self.imgsaved = StatsPanel(parent=self, stat_name="Saved:", stat_value="0")
        self.progressbar = ProgressPanel(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)
        
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.addressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.treeview, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 1, wx.EXPAND|wx.ALL, WX_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.AddStretchSpacer(1)
        hs.Add(self.errors, 0, wx.EXPAND|wx.ALL, 2)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.ignored, 0, wx.EXPAND|wx.ALL, 2)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.imgsaved, 0, wx.EXPAND|wx.ALL, 2)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 2)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.progressbar, 1, wx.EXPAND|wx.ALL, WX_BORDER)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, WX_BORDER)

        self.SetSizer(vs)
    
    def on_fetch_button(self, evt):
        if self.addressbar.txt_address.GetValue():
            data = {"url": self.addressbar.txt_address.GetValue()}
            self.app.commander.queue.put_nowait(
                Message(thread=const.THREAD_MAIN, event=const.EVENT_FETCH, id=0, status=const.STATUS_OK, data=data))

    def on_start_button(self, evt):
        self.app.commander.queue.put_nowait(
                Message(thread=const.THREAD_MAIN, event=const.EVENT_START, status=const.STATUS_OK, data=None, id=0))

    def on_stop_button(self, evt):
        self.app.commander.queue.put_nowait(
            Message(thread=const.THREAD_MAIN, event=const.EVENT_CANCEL, data=None, id=0, status=const.STATUS_OK))
    
    def on_btn_open_dir(self, evt):
        dlg = wx.FileDialog(
            parent=self, message="Choose an HTML Document to Search",
            wildcard="(*.html,*.xhtml)|*.html;*.xhtml",
            style=-wx.FD_FILE_MUST_EXIST|wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.addressbar.txt_address.SetValue(dlg.GetPaths()[0])
        dlg.Destroy()

    def on_mouse_enter(self, text):
        self.app.window.sbar.SetStatusText(text)


class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.app = wx.GetApp()
        
        self.txt_address = ThemedTextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)

        bitmaps = wx.GetApp().bitmaps
        btn_open = wx.BitmapButton(self, -1, bitmaps["html-file"])

        self.btn_fetch = wx.BitmapButton(self, -1, bitmaps["fetch"])
        self.btn_stop = wx.BitmapButton(self, -1, bitmaps["cancel"])
        self.btn_start = wx.BitmapButton(self, -1, bitmaps["start"])

        self.txt_address.Bind(wx.EVT_TEXT_ENTER, self.GetParent().on_fetch_button, self.txt_address)
        self.btn_fetch.Bind(wx.EVT_BUTTON, self.GetParent().on_fetch_button, self.btn_fetch)
        self.btn_stop.Bind(wx.EVT_BUTTON, self.GetParent().on_stop_button, self.btn_stop)
        self.btn_start.Bind(wx.EVT_BUTTON, self.GetParent().on_start_button, self.btn_start)
        btn_open.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_open_dir, btn_open)

        self.set_help_text(self.btn_fetch, "Fetch Links found from the Url")
        self.set_help_text(self.btn_start, "Start scanning the fetched Urls")
        self.set_help_text(self.btn_stop, "Stop the current Scan")
        self.set_help_text(self.txt_address, "Enter a Url or File path to go fetch")
        self.set_help_text(btn_open, "Open an HTML file from local drive to go fetch")

        vs = vboxsizer()

        hs = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Url or HTML File")
        hs.Add(self.txt_address, 1, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_open, 0, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(20)
        hs.Add(self.btn_fetch, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(self.btn_stop, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(self.btn_start, 0, wx.ALL|wx.EXPAND, 0)
    
        vs.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(vs)
    
    def set_help_text(self, button, text):
        button.Bind(wx.EVT_ENTER_WINDOW,
                    lambda evt: self.on_mouse_over_button(text), 
                    button)

    def on_mouse_over_button(self, text):
        self.app.window.sbar.SetStatusText(text)


class StatusTreeView(wx.TreeCtrl):

    class ItemPopup(wx.Menu):

        """PopupMenu for the TreeCtrl
        """

        def __init__(self, parent, item):
            super().__init__()
            self._text = parent.GetItemText(item)
            self._parent = parent
            self.Append(100, "Copy", "Copy item to Clipboard")
            self.Append(101, "Open", "Try to open the Item")
            self._parent.Bind(wx.EVT_MENU, self._on_copy, id=100)
            self._parent.Bind(wx.EVT_MENU, self._on_open, id=101)
        
        def _on_open(self, evt):
            webbrowser.open(self._text)
        
        def _on_copy(self, evt):
            data = wx.TextDataObject()
            data.SetText(self._text)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data)
                wx.TheClipboard.Close()

    def __init__(self, parent, id):
        super().__init__(parent=parent, id=id, style=wx.TR_SINGLE|wx.TR_NO_BUTTONS)
        self.app = wx.GetApp()
        self.imagelist = wx.ImageList(16, 16)
        self._link_bmp = self.imagelist.Add(self.app.bitmaps["web"])
        self._img_bmp = self.imagelist.Add(self.app.bitmaps["image"])
        self._error_bmp = self.imagelist.Add(self.app.bitmaps["error"])
        self._ignored_bmp = self.imagelist.Add(self.app.bitmaps["ignored"])
        self._saved_bmp = self.imagelist.Add(self.app.bitmaps["saved"])
        self._search_bmp = self.imagelist.Add(self.app.bitmaps["searching"])
        self.SetImageList(self.imagelist)

        self.clear()

        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self._on_right_click, self)
    
    def _on_right_click(self, evt):
        menu = StatusTreeView.ItemPopup(self, evt.Item)
        self.PopupMenu(menu)
        menu.Destroy()

    def populate(self, url, links):
        """Gets called after Fetch job

        Args:
            url (str): The source Url gets added as root
            links (list): UrlData objects
        """
        self.clear()
        self.root = self.AddRoot(url)
        self.SetItemData(self.root, None)
        self.SetItemImage(self.root, self._link_bmp, wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, self._link_bmp, wx.TreeItemIcon_Expanded)

        for link in links:
            child = self.AppendItem(self.root, link.url)
            self.children.append(child)
            self.SetItemData(child, None)
            if link.tag == "a":
                self.SetItemImage(child, self._link_bmp, wx.TreeItemIcon_Normal)
                self.SetItemImage(child, self._link_bmp, wx.TreeItemIcon_Expanded)
            else:
                self.SetItemImage(child, self._img_bmp, wx.TreeItemIcon_Normal)
                self.SetItemImage(child, self._img_bmp, wx.TreeItemIcon_Expanded)
        self.Expand(self.root)
    
    def add_url(self, msg):
        child = self.children[msg.id]
        self.AppendItem(child, msg.data["message"])
        if msg.status == const.STATUS_OK:
            bmp = self._saved_bmp
        elif msg.status == const.STATUS_ERROR:
            bmp = self._error_bmp
        else:
            bmp = self._ignored_bmp
        self.SetItemData(child, None)
        self.SetItemImage(child, bmp, wx.TreeItemIcon_Normal)
        self.SetItemImage(child, bmp, wx.TreeItemIcon_Expanded)
    
    def set_searching(self, index):
        child = self.children[index]
        self.SetItemImage(child, self._search_bmp, wx.TreeItemIcon_Normal)
        self.SetItemImage(child, self._search_bmp, wx.TreeItemIcon_Expanded)
    
    def set_message(self, msg):
        child = self.children[msg.id]
        self.AppendItem(child, msg.data["message"])
    
    def clear(self):
        self.DeleteAllItems()
        self.children = []
        

class StatsPanel(wx.Panel):

    def __init__(self, stat_name, stat_value, *args, **kw):
        super().__init__(*args, **kw)

        lbl = wx.StaticText(self, -1, stat_name)
        self.value = wx.StaticText(self, -1, stat_value)

        vs = vboxsizer()
        hs = hboxsizer()
        hs.Add(lbl, 1, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(WX_BORDER)
        hs.Add(self.value, 1, wx.ALL|wx.EXPAND, 0)
        vs.Add(hs, 1, wx.ALL|wx.EXPAND)
        self.SetSizer(vs)

        self.stat = 0
    
    def reset_stat(self):
        self.stat = 0
        self.value.SetLabel("0")
    
    def add_stat(self):
        self.stat += 1
        self.value.SetLabel(self.stat.__str__())
    

class ProgressPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.gauge = wx.Gauge(self, -1, 100)
        self.time = ThemedStaticText(self, -1, "00:00:00")

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Progress")

        vs = vboxsizer()
        vs.Add(self.gauge, 1, wx.EXPAND|wx.ALL, 0)
        box.Add(vs, 1, wx.ALL|wx.EXPAND, 0)

        box.AddSpacer(WX_BORDER)

        vs = vboxsizer()
        vs.Add(self.time, 1, wx.EXPAND|wx.ALL, 0)
        box.Add(vs, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(box)
    
    def reset_progress(self, max_range):
        self.gauge.SetRange(max_range)
        self.gauge.SetValue(0)
    
    def increment(self):
        value = self.gauge.GetValue()
        self.gauge.SetValue(value + 1)

        