import wx
import os
from wx.lib import masked

import wx.lib.scrolledpanel as scrolled
from crawler.options import SQL_PATH
import crawler.options as options

STATIC_BOX_BORDER = 5

DIALOG_BORDER = 30


class SettingsDialog(wx.Dialog):

    def __init__(self, parent, id, title, size, pos, style, name, settings):
        super().__init__()
        self.app = wx.GetApp()
        self.bitmaps = self.app.bitmaps
        self.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        self.Create(parent, id, title, pos, size, style, name)

        self.panel = SettingsPanel(self, -1)
        self.ok_cancel_panel = OkCancelPanel(self, -1)

        vs = wx.BoxSizer(wx.VERTICAL)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.panel, 1, wx.ALL | wx.EXPAND, 0)
        vs.Add(hs, 1, wx.ALL | wx.EXPAND, 0)
        vs.AddSpacer(10)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.ok_cancel_panel, 1, wx.ALL | wx.EXPAND, 0)
        vs.Add(hs, 0, wx.ALL | wx.EXPAND, 0)
        vs.AddSpacer(10)
        self.SetSizer(vs)

        w, h = self.app.window.GetSize()
        self.SetSize(w - 40, h - 40)

        self.panel.SetFocus()
        self.settings = settings
        self.load_settings(settings)

    def load_settings(self, settings):
        """Initializes the Settings wxControls from the settings dict

        Args:
            settings (dict): The settings json loaded from the settings.json file
        """

        filtered_search = settings.get("filter-search",
                                       {"enabled": True, "filters": ["imagevenue.com/"]})
        self.panel.filter_panel.checkbox.SetValue(filtered_search["enabled"])
        self.panel.filter_panel.listbox.Clear()
        [self.panel.filter_panel.listbox.Append(item) for item in filtered_search["filters"]]

        self.panel.auto_panel.checkbox.SetValue(
            settings.get("auto-download", False))

        self.panel.notify_panel.checkbox.SetValue(
            settings.get("notify-done", True))

        self.panel.detach_panel.checkbox.SetValue(
            settings.get("detach-progress", True))

        self.panel.imgformat_panel.set_values(
            settings.get("images_to_search",
                         (True, False, False, False, False, False, False)))

        self.panel.fileexist_panel.set_selection(
            settings.get("file_exists", "overwrite"))

        self.panel.cookie_panel.set_group(settings.get("cookies", {}))

        self.panel.savepath.text.SetValue(
            settings.get("save_path", ""))

        self.panel.folder_panel.set_options(
            settings["unique_pathname"]["enabled"],
            settings["generate_filenames"]["enabled"],
            settings["generate_filenames"]["name"])

        self.panel.max_connections.slider.SetValue(
            settings.get("max_connections", 10))

        formsearch = settings.get("form_search", {
            "enabled": True, "include_original_host": False})
        self.panel.formsearch_panel.chk_enable.SetValue(
            formsearch["enabled"])
        self.panel.formsearch_panel.chk_include_host.SetValue(
            formsearch["include_original_host"])

        self.panel.thumb_panel.checkbox.SetValue(
            settings.get("thumbnails_only", True))

        minsize = settings.get(
            "minimum_image_resolution", {"width": 100, "height": 100})
        self.panel.minsize_panel.set_min_values(
            minsize["width"], minsize["height"])

        self.panel.timeout.set_timeout(
            settings.get("connection_timeout", 5))

    def get_settings(self) -> dict:
        """Like load_settings but in reverse. Should be called
        if the Dialog returns wx.ID_OK and save the returned settings json

        Returns:
            str: settings json object
        """
        settings = self.settings

        settings["profile-name"] = \
            self.panel.profile_panel.cmbox.GetStringSelection()

        # filtered search
        settings["filter-search"]["filters"] \
            = self.panel.filter_panel.listbox.GetItems()
        settings["filter-search"]["enabled"] = \
            self.panel.filter_panel.checkbox.GetValue()

        # notify
        settings["notify-done"] = \
            self.panel.notify_panel.checkbox.GetValue()

        # detach progress
        settings["detach-progress"] = \
            self.panel.detach_panel.checkbox.GetValue()

        # auto-download
        settings["auto-download"] = \
            self.panel.auto_panel.checkbox.GetValue()

        # form search
        settings["form_search"]["enabled"] = \
            self.panel.formsearch_panel.chk_enable.GetValue()
        settings["form_search"]["include_original_host"] = \
            self.panel.formsearch_panel.chk_include_host.GetValue()

        # If file already exists
        settings["file_exists"] = \
            self.panel.fileexist_panel.get_selected()

        # Save options
        settings["unique_pathname"]["enabled"] = \
            self.panel.folder_panel.chk_unique_path.GetValue()
        settings["generate_filenames"]["enabled"] = \
            self.panel.folder_panel.chk_prefixed_name.GetValue()
        settings["generate_filenames"]["name"] = \
            self.panel.folder_panel.txt_prefixed_name.GetValue()

        settings["save_path"] = \
            self.panel.savepath.text.GetValue()

        # Thumbnails only
        settings["thumbnails_only"] = \
            self.panel.thumb_panel.checkbox.GetValue()

        # min size
        settings["minimum_image_resolution"]["width"] = \
            self.panel.minsize_panel.text_width.GetValue()
        settings["minimum_image_resolution"]["height"] = \
            self.panel.minsize_panel.text_height.GetValue()

        # Max timeout
        settings["connection_timeout"] = \
            self.panel.timeout.choice.GetSelection()

        # Max Connections
        settings["max_connections"] = self.panel.max_connections.slider.GetValue()

        # Cookies
        settings["cookies"] = self.panel.cookie_panel.get_group()

        # Get the Image format
        settings["images_to_search"] = \
            self.panel.imgformat_panel.get_values()

        return settings


class SettingsPanel(scrolled.ScrolledPanel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pnl = wx.Panel(self, -1)

        self.profile_panel = ProfilePanel(pnl, -1, dialog=self.GetParent())
        self.max_connections = MaxConnectionsPanel(pnl, -1)
        self.timeout = TimeoutPanel(pnl, -1)
        self.auto_panel = AutoDownload(pnl, -1)
        self.minsize_panel = MinWidthHeightPanel(pnl, -1)
        self.thumb_panel = ThumbnailOnlyPanel(pnl, -1)
        self.savepath = SaveFolderPanel(pnl, -1)
        self.folder_panel = SaveOptionsPanel(pnl, -1)
        self.cookie_panel = CookieOptionsPanel(pnl, -1)
        self.imgformat_panel = ImageFormatOptionsPanel(pnl, -1)
        self.fileexist_panel = FileAlreadyExistPanel(pnl, -1)
        self.formsearch_panel = FormSearchPanel(pnl, -1)
        self.notify_panel = NotifyPanel(pnl, -1)
        self.detach_panel = DetachPanel(pnl, -1)
        self.filter_panel = FilterPanel(pnl, -1, size=(-1, 200))
        self.cache_panel = CachePanel(pnl, -1)

        vs = wx.BoxSizer(wx.VERTICAL)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.profile_panel, 1, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.max_connections, 1, wx.EXPAND | wx.ALL, 0)
        hs.Add(self.timeout, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.auto_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.minsize_panel, 0, wx.EXPAND | wx.ALL, 0)
        hs.Add(self.thumb_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.savepath, 1, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.folder_panel, 1, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.cookie_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.imgformat_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.formsearch_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.fileexist_panel, 1, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.filter_panel, 1, wx.EXPAND | wx.ALL, 0)
        hs.AddStretchSpacer(1)
        vs.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.notify_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.detach_panel, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.cache_panel, 1, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND | wx.ALL, 0)

        pnl.SetSizer(vs)

        gs = wx.GridSizer(cols=1, rows=1, vgap=0, hgap=0)
        gs.Add(pnl, 1, wx.EXPAND | wx.ALL, 20)
        self.SetSizer(gs)
        self.Fit()
        self.SetAutoLayout(1)
        self.SetupScrolling()


class ProfilePanel(wx.Panel):

    def __init__(self, parent, id, dialog):
        super().__init__(parent=parent, id=id)

        self.dlg = dialog
        self.app = wx.GetApp()

        settings = options.load_settings()

        self.cmbox = wx.Choice(self, -1, choices=options.load_profiles())
        self.cmbox.SetStringSelection(settings["profile-name"])
        btn_new = wx.Button(self, -1, "New")
        btn_delete = wx.Button(self, -1, "Delete")

        vs = wx.StaticBoxSizer(wx.VERTICAL, self, "Profile")
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.cmbox, 1, wx.EXPAND | wx.ALL, 0)
        hs.AddSpacer(5)
        hs.Add(btn_delete, 0, wx.EXPAND | wx.ALL, 0)
        hs.AddSpacer(5)
        hs.Add(btn_new, 0, wx.EXPAND | wx.ALL, 0)
        vs.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(vs)

        btn_new.Bind(wx.EVT_BUTTON, self._on_new_profile, btn_new)
        btn_delete.Bind(wx.EVT_BUTTON, self._on_btn_delete, btn_delete)
        self.cmbox.Bind(wx.EVT_CHOICE, self._on_choice, self.cmbox)

    def _on_btn_delete(self, evt):
        name = self.cmbox.GetStringSelection()
        try:
            if options.delete_profile(name):
                settings = options.load_settings()
                self.dlg.load_settings(settings)
                self.cmbox.Delete(self.cmbox.GetSelection())
                self.cmbox.SetStringSelection(settings["profile-name"])
        except NameError as err:
            dlg = wx.MessageDialog(self, err.__str__(), "Error", style=wx.OK | wx.CENTER | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

    def _on_new_profile(self, evt):
        dlg = wx.TextEntryDialog(self, "Name the Profile", "New Profile Name")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue()
            settings = self.dlg.get_settings()
            name = options.format_filename(name)
            settings["profile-name"] = name
            options.save_profile(settings)
            options.use_profile(name)
            self.app.window.set_profile_status(name)
            self.cmbox.Append(name)
            self.cmbox.SetStringSelection(name)
        dlg.Destroy()

    def _on_choice(self, evt):
        name = evt.GetString()
        options.use_profile(name)
        self.app.window.set_profile_status(name)
        self.dlg.load_settings(options.load_settings())


class DetachPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.checkbox = wx.CheckBox(self, -1, "Enable")

        vbox = wx.StaticBoxSizer(wx.VERTICAL, self, "Detachable Progress Window")
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.checkbox, 0, wx.ALL | wx.EXPAND, 0)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(vbox)


class AutoDownload(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.checkbox = wx.CheckBox(self, -1, "Enable")

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Automatically Download when Url found")

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.checkbox, 1, wx.ALL | wx.EXPAND, 0)
        box.Add(hs, 1, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(box)


class NotifyPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.checkbox = wx.CheckBox(self, -1, "Enable")

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Notify when finished")

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.checkbox, 1, wx.ALL | wx.EXPAND, 0)
        box.Add(hs, 1, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(box)


class ImageFormatOptionsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.ext = []

        self.ext.append(wx.CheckBox(self, -1, "JPG"))
        self.ext.append(wx.CheckBox(self, -1, "PNG"))
        self.ext.append(wx.CheckBox(self, -1, "GIF"))
        self.ext.append(wx.CheckBox(self, -1, "BMP"))
        self.ext.append(wx.CheckBox(self, -1, "ICO"))
        self.ext.append(wx.CheckBox(self, -1, "TIFF"))
        self.ext.append(wx.CheckBox(self, -1, "TGA"))

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Search for selected image formats")
        for chk in self.ext:
            hs = wx.BoxSizer(wx.HORIZONTAL)
            hs.Add(chk, 1, wx.ALL | wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

    def set_values(self, file_exts):
        # iterate through the file extension dict
        for index, key in enumerate(file_exts.keys()):
            self.ext[index].SetValue(file_exts[key])

    def get_values(self):
        d = {}
        for checkbox in self.ext:
            key = checkbox.GetLabelText().lower()
            value = bool(checkbox.GetValue())
            d[key] = value
        return d


class FileAlreadyExistPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.group = []

        self.group.append(wx.RadioButton(self, -1, "Skip", style=wx.RB_GROUP))
        self.group.append(wx.RadioButton(self, -1, "Overwrite"))
        self.group.append(wx.RadioButton(self, -1, "Rename"))

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "If File already exists")
        for rb in self.group:
            hs = wx.BoxSizer(wx.VERTICAL)
            hs.Add(rb, 1, wx.ALL | wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

    def set_selection(self, file_exists):
        for rb in self.group:
            rb.SetValue(False)
            if file_exists == rb.GetLabelText().lower():
                rb.SetValue(True)

    def get_selected(self):
        for rb in self.group:
            if rb.GetValue():
                return rb.GetLabelText().lower()
        return "overwrite"


class CookieOptionsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.group = []

        self.group.append(wx.RadioButton(self, -1, "Firefox", style=wx.RB_GROUP))
        self.group.append(wx.RadioButton(self, -1, "Chrome"))
        self.group.append(wx.RadioButton(self, -1, "Opera"))
        self.group.append(wx.RadioButton(self, -1, "Edge"))
        self.group.append(wx.RadioButton(self, -1, "All"))

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Use Browser Cookies")
        for rb in self.group:
            hs = wx.BoxSizer(wx.HORIZONTAL)
            hs.Add(rb, 1, wx.ALL | wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

    def set_group(self, cookies):
        # iterate through the browser cookie dict
        for index, key in enumerate(cookies.keys()):
            self.group[index].SetValue(cookies[key])

    def get_group(self):
        d = {}
        for radiobutton in self.group:
            key = radiobutton.GetLabelText().lower()
            value = bool(radiobutton.GetValue())
            d[key] = value
        return d


class SaveFolderPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.text = wx.TextCtrl(self, -1, "")
        btn_dir = wx.Button(self, -1, "Browse", size=(68, -1))

        btn_dir.Bind(wx.EVT_BUTTON, self.on_dir_button, btn_dir)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.text, 1, wx.ALL | wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(btn_dir, 0, wx.ALL | wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Save Path")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(box)

    def on_dir_button(self, evt):
        dlg = wx.DirDialog(
            self,
            "Save Folder",
            self.text.GetValue(),
            style=wx.DD_DIR_MUST_EXIST,
        )
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            self.text.SetValue(dlg.GetPath())
        dlg.Destroy()


class SaveOptionsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.chk_prefixed_name = wx.CheckBox(self, -1, "Generate prefixed Filenames")
        self.chk_prefixed_name.SetValue(True)
        self.chk_unique_path = wx.CheckBox(self, -1, "Unique path name")
        self.chk_unique_path.SetValue(True)
        self.txt_prefixed_name = wx.TextCtrl(self, -1, "image", size=(120, -1))

        self.chk_prefixed_name.Bind(wx.EVT_CHECKBOX, self.on_prefix_checkbox, self.chk_prefixed_name)

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Folder Options")

        hs = wx.BoxSizer(wx.VERTICAL)
        hs.Add(self.chk_unique_path, 1, wx.ALL | wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        box.AddSpacer(30)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.chk_prefixed_name, 1, wx.ALL | wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND | wx.ALL, 0)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.txt_prefixed_name, 1, wx.ALL | wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(box)

    def on_prefix_checkbox(self, evt):
        if evt.Selection:
            self.txt_prefixed_name.Enable(True)
        else:
            self.txt_prefixed_name.Enable(False)

    def set_options(self, unique_path_enabled,
                    gen_filename_enabled, gen_filename):
        self.chk_unique_path.SetValue(unique_path_enabled)
        self.chk_prefixed_name.SetValue(gen_filename_enabled)
        self.txt_prefixed_name.SetValue(gen_filename)
        if self.chk_prefixed_name.GetValue():
            self.txt_prefixed_name.Enable(True)
        else:
            self.txt_prefixed_name.Enable(False)


class MaxConnectionsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.slider = wx.Slider(self,
                                -1, 10, 1, 100,
                                style=wx.SL_HORIZONTAL | wx.SL_MIN_MAX_LABELS | wx.SL_LABELS)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.slider, 1, wx.ALL | wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Maximum Connections")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(box)


class FormSearchPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.chk_enable = wx.CheckBox(self, -1, "Enable")
        self.chk_include_host = wx.CheckBox(self, -1, "Include Forms from original Host")

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.chk_enable, 0, wx.EXPAND | wx.ALL, STATIC_BOX_BORDER)
        hs.AddSpacer(DIALOG_BORDER)
        hs.Add(self.chk_include_host, 0, wx.EXPAND | wx.ALL, STATIC_BOX_BORDER)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Search Forms (can be slow)")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(box)


class ThumbnailOnlyPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.checkbox = wx.CheckBox(self, -1, "")
        self.checkbox.SetValue(True)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.checkbox, 1, wx.ALL | wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Thumbnail Links only")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(box)


class MinWidthHeightPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.text_width = masked.NumCtrl(self,
                                         -1,
                                         200,
                                         integerWidth=5,
                                         allowNegative=False)

        self.text_height = masked.NumCtrl(self,
                                          -1,
                                          200,
                                          integerWidth=5,
                                          allowNegative=False)

        label = wx.StaticText(self, -1, "x")

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.text_width, 1, wx.ALL | wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(label, 0, wx.ALIGN_BOTTOM, 0)
        hs.AddSpacer(10)
        hs.Add(self.text_height, 1, wx.ALL | wx.EXPAND, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Minimum Resolution Size (width, height)")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(box)

    def set_min_values(self, width, height):
        self.text_width.SetValue(width)
        self.text_height.SetValue(height)


class TimeoutPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        choices = list(map(lambda x: str(x + 1), range(60)))

        self.choice = wx.Choice(self, -1,
                                choices=choices)

        self.choice.SetSelection(6)

        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.choice, 1, wx.ALL | wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Timeout")
        box.Add(hs, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(box)

    def set_timeout(self, timeout):
        if timeout > 0 and timeout <= 60:
            self.choice.SetSelection(timeout)


class FilterPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.listbox = wx.ListBox(self, -1, choices=[], style=wx.LB_SINGLE | wx.LB_SORT)
        self.textctrl = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.checkbox = wx.CheckBox(self, -1, "Enable")
        btn_all = wx.Button(self, -1, "Delete All")
        btn_remove = wx.Button(self, -1, "Delete")
        btn_add = wx.Button(self, -1, "Add")
        btn_add.Bind(wx.EVT_BUTTON, self.on_add, btn_add)
        btn_remove.Bind(wx.EVT_BUTTON, self.on_remove, btn_remove)
        btn_all.Bind(wx.EVT_BUTTON, lambda evt: self.listbox.Clear(), btn_all)
        self.textctrl.Bind(wx.EVT_TEXT_ENTER, lambda evt: self.on_add(None), self.textctrl)

        sbox = wx.StaticBoxSizer(wx.VERTICAL, self, "Search Filters")
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.listbox, 1, wx.ALL | wx.EXPAND, 0)
        sbox.Add(hs, 1, wx.ALL | wx.EXPAND, 0)
        sbox.AddSpacer(10)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        hs.Add(self.textctrl, 1, wx.ALL | wx.EXPAND, 0)
        sbox.Add(hs, 0, wx.ALL | wx.EXPAND, 0)
        sbox.AddSpacer(10)
        hs = wx.BoxSizer(wx.HORIZONTAL)
        for w in (btn_all, btn_remove, btn_add, self.checkbox):
            hs.Add(w, 0, wx.ALIGN_CENTER, 0)
            hs.AddSpacer(10)
        sbox.Add(hs, 0, wx.ALIGN_CENTER, 0)
        sbox.AddSpacer(10)
        self.SetSizer(sbox)

    def on_add(self, evt):
        text = self.textctrl.GetValue()
        if text:
            if text not in self.listbox.GetItems():
                self.listbox.Append(text)
                self.textctrl.SetValue("")
            else:
                dlg = wx.MessageDialog(self, "Duplicate entry found", "Nope", wx.OK | wx.CENTER | wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()

    def on_remove(self, evt):
        index = self.listbox.GetSelection()
        if index is not wx.NOT_FOUND:
            self.listbox.Delete(index)


class CachePanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        app = wx.GetApp()

        btn_delete = wx.Button(self, -1, "Clear Cache")
        self.Bind(wx.EVT_BUTTON, self.on_clear_cache, btn_delete)
        btn_delete.SetBitmap(app.bitmaps["delete"], wx.LEFT)
        btn_delete.SetBitmapMargins((2, 2))
        btn_delete.SetInitialSize()

    def on_clear_cache(self, evt):
        dlg = wx.MessageDialog(self, "Are you sure you want to delete the Cache?", "Delete Cache?",
                               style=wx.CANCEL | wx.OK | wx.CENTER)
        if dlg.ShowModal() == wx.ID_OK:
            if os.path.exists(SQL_PATH):
                os.remove(SQL_PATH)
                wx.GetApp().window.sbar.SetStatusText("Cache has been cleared")
        dlg.Destroy()


class OkCancelPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        btn_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        btn_ok = wx.Button(self, wx.ID_OK, "Save")

        hs = wx.BoxSizer(wx.HORIZONTAL)

        hs.Add(btn_cancel, 0, wx.ALIGN_CENTER, 0)
        hs.AddSpacer(10)
        hs.Add(btn_ok, 0, wx.ALIGN_CENTER, 0)

        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(hs, 1, wx.ALIGN_CENTER, 0)

        self.SetSizer(vs)
