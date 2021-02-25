import wx

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
from gui.about import AnimatedDialog


class DownloadPanel(wx.Panel):

    def __init__(self, **kwargs):
        super(DownloadPanel, self).__init__(**kwargs)

        self.app = wx.GetApp()

        self.addressbar = AddressBar(self, -1)
        self.statusbox = StatusPanel(self, -1)
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
        hs.Add(self.statusbox, 1, wx.EXPAND|wx.ALL, WX_BORDER)
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
    
    def resetstats(self):
        """Resets the Stats labels
        """
        self.errors.value.SetLabel("0")
        self.imgsaved.value.SetLabel("0")
        self.ignored.value.SetLabel("0")

    def on_btn_settings(self, evt):
        dlg = SettingsDialog(parent=self.GetParent(),
                             id= -1,
                             title="Settings",
                             size=wx.DefaultSize,
                             pos=wx.DefaultPosition,
                             style=wx.DEFAULT_DIALOG_STYLE,
                             name="settings_dialog",
                             settings=options.load_settings())
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.get_settings()
            options.save_settings(settings)
        dlg.Destroy()
    
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
    
    def update_stats(self, saved, ignored, errors):
        self.ignored.value.SetLabel(str(ignored))
        self.imgsaved.value.SetLabel(str(saved))
        self.errors.value.SetLabel(str(errors))
    
    def on_btn_open_dir(self, evt):
        dlg = wx.FileDialog(
            parent=self, message="Choose an HTML Document to Search",
            wildcard="(*.html,*.xhtml)|*.html;*.xhtml",
            style=-wx.FD_FILE_MUST_EXIST|wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.addressbar.txt_address.SetValue(dlg.GetPaths()[0])
        dlg.Destroy()
    
    def on_btn_about(self, evt):
        dlg = AnimatedDialog(self, -1, "About", 
                            ["PixGrabber", "Paul Millar", "", options.VERSION])
        dlg.ShowModal()
        dlg.Destroy()

    def on_mouse_enter(self, text):
        self.app.window.sbar.SetStatusText(text)

class AddressBar(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.app = wx.GetApp()
        
        self.txt_address = ThemedTextCtrl(self, -1, "")

        bitmaps = wx.GetApp().bitmaps
        btn_open = wx.BitmapButton(self, -1, bitmaps["html-file"])

        self.btn_fetch = wx.BitmapButton(self, -1, bitmaps["fetch"])
        self.btn_stop = wx.BitmapButton(self, -1, bitmaps["cancel"])
        self.btn_start = wx.BitmapButton(self, -1, bitmaps["start"])
        btn_settings = wx.BitmapButton(self, -1, bitmaps["settings"])
        btn_about = wx.BitmapButton(self, -1, bitmaps["about"])

        self.btn_fetch.Bind(wx.EVT_BUTTON, self.GetParent().on_fetch_button, self.btn_fetch)
        self.btn_stop.Bind(wx.EVT_BUTTON, self.GetParent().on_stop_button, self.btn_stop)
        self.btn_start.Bind(wx.EVT_BUTTON, self.GetParent().on_start_button, self.btn_start)
        btn_settings.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_settings, btn_settings)
        btn_about.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_about, btn_about)
        btn_open.Bind(wx.EVT_BUTTON, self.GetParent().on_btn_open_dir, btn_open)

        self.set_help_text(self.btn_fetch, "Fetch Links found from the Url")
        self.set_help_text(self.btn_start, "Start scanning the fetched Urls")
        self.set_help_text(self.btn_stop, "Stop the current Scan")
        self.set_help_text(btn_settings, "Open the Settings Dialog")
        self.set_help_text(btn_about, "About the Program and Developer")
        self.set_help_text(self.txt_address, "Enter a Url or File path to go fetch")
        self.set_help_text(btn_open, "Open an HTML file from local drive to go fetch")

        vs = vboxsizer()

        hs = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Download Url")
        hs.Add(self.txt_address, 1, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_open, 0, wx.ALL|wx.EXPAND, 0)

        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 0)

        hs = hboxsizer()
        hs.Add(btn_settings, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(btn_about, 0, wx.ALL|wx.EXPAND, 0)
        hs.AddStretchSpacer(1)
        hs.Add(self.btn_fetch, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(self.btn_stop, 0, wx.ALL|wx.EXPAND, 0)
        hs.Add(self.btn_start, 0, wx.ALL|wx.EXPAND, 0)
    
        vs.Add(hs, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(vs)
    
    def set_help_text(self, button, text):
        button.Bind(wx.EVT_ENTER_WINDOW,
                    lambda evt: self.on_mouse_over_button(text), 
                    button)

    def on_mouse_over_button(self, text):
        self.app.window.sbar.SetStatusText(text)

class StatusPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.txt_status = ThemedTextCtrl(self, -
        1, 
        "",
        style=wx.TE_READONLY|wx.TE_MULTILINE)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.txt_status, 1, wx.EXPAND|wx.ALL, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Status")
        box.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(box)


class StatusTreeView(wx.TreeCtrl):

    def __init__(self, parent, id):
        super().__init__(parent=parent, id=id, style=wx.TR_SINGLE|wx.TR_NO_BUTTONS)
        self.app = wx.GetApp()
        self.imagelist = wx.ImageList(16, 16)
        self._link_bmp = self.imagelist.Add(self.app.bitmaps["web"])
        self._img_bmp = self.imagelist.Add(self.app.bitmaps["image"])
        self.SetImageList(self.imagelist)

    def populate(self, url, links):
        """Gets called after Fetch job

        Args:
            url (str): The source Url gets added as root
            links (list): UrlData objects
        """
        self.DeleteAllItems()
        self.root = self.AddRoot(url)
        self.SetItemData(self.root, None)
        self.SetItemImage(self.root, self._link_bmp, wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, self._link_bmp, wx.TreeItemIcon_Expanded)

        for link in links:
            child = self.AppendItem(self.root, link.url)
            self.SetItemData(child, None)
            if link.tag == "a":
                self.SetItemImage(child, self._link_bmp, wx.TreeItemIcon_Normal)
                self.SetItemImage(child, self._link_bmp, wx.TreeItemIcon_Expanded)
            else:
                self.SetItemImage(child, self._img_bmp, wx.TreeItemIcon_Normal)
                self.SetItemImage(child, self._img_bmp, wx.TreeItemIcon_Expanded)

        self.Expand(self.root)



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

        