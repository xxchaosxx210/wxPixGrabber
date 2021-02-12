import wx
from wx.lib import masked

from global_props import Settings

import wx.lib.scrolledpanel as scrolled

from app_theme import (
    ThemedButton,
    hboxsizer,
    vboxsizer,
    DIALOG_BORDER
)

STATICBOX_BORDER = 5


class SettingsDialog(wx.Dialog):

    def __init__(self, parent, id, title, size, pos, style, name):
        super().__init__()
        self.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        self.Create(parent, id, title, pos, size, style, name)

        self.panel = SettingsPanel(self, -1)
        self.ok_cancel_panel = OkCancelPanel(self, -1)

        vs = vboxsizer()

        hs = hboxsizer()
        hs.Add(self.panel, 1, wx.ALL|wx.EXPAND, 10)
        vs.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        hs = hboxsizer()
        hs.Add(self.ok_cancel_panel, 1, wx.ALL|wx.EXPAND, 10)
        vs.Add(hs, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(vs)

        self.SetSize(600, 400)

        self.panel.SetFocus()
    
    def save_settings(self):
        settings = Settings.load()

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
            self.panel.folder_panel.chk_prefixed_name.GetValue()
        settings["generate_filenames"]["enabled"] = \
            self.panel.folder_panel.chk_unique_path.GetValue()
        settings["generate_filenames"]["name"] = \
            self.panel.folder_panel.txt_unique_path.GetValue()

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
        
        Settings.save(settings)


class SettingsPanel(scrolled.ScrolledPanel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.max_connections = MaxConnectionsPanel(self, -1)
        self.timeout = TimeoutPanel(self, -1)
        self.minsize_panel = MinWidthHeightPanel(self, -1)
        self.thumb_panel = ThumbnailOnlyPanel(self, -1)
        self.savepath = SaveFolderPanel(self, -1)
        self.folder_panel = SaveOptionsPanel(self, -1)
        self.cookie_panel = CookieOptionsPanel(self, -1)
        self.imgformat_panel = ImageFormatOptionsPanel(self, -1)
        self.fileexist_panel = FileAlreadyExistPanel(self, -1)
        self.formsearch_panel = FormSearchPanel(self, -1)

        vs = vboxsizer()

        hs = hboxsizer()
        hs.Add(self.max_connections, 1, wx.EXPAND|wx.ALL, 0)
        hs.AddSpacer(DIALOG_BORDER)
        hs.Add(self.timeout, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.minsize_panel, 0, wx.EXPAND|wx.ALL, 0)
        hs.AddSpacer(DIALOG_BORDER)
        hs.Add(self.thumb_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.savepath, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.folder_panel, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.cookie_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.imgformat_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.formsearch_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.fileexist_panel, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        self.SetSizer(vs)
        self.Fit()

        self.SetAutoLayout(1)
        self.SetupScrolling()


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
            hs = hboxsizer()
            hs.Add(chk, 1, wx.ALL|wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

        exts = Settings.load()["images_to_search"]
        # iterate through the file extension dict
        for index, key in enumerate(exts.keys()):
            self.ext[index].SetValue(exts[key])
    
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
            hs = vboxsizer()
            hs.Add(rb, 1, wx.ALL|wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

        file_exists = Settings.load()["file_exists"]
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
            hs = hboxsizer()
            hs.Add(rb, 1, wx.ALL|wx.EXPAND, 0)
            box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
            box.AddSpacer(10)
        self.SetSizer(box)

        cookies = Settings.load()["cookies"]
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

        hs = hboxsizer()
        hs.Add(self.text, 1, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(btn_dir, 0, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Save Path")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)

        self.text.SetValue(Settings.load()["save_path"])
    
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
        self.txt_unique_path = wx.TextCtrl(self, -1, "image", size=(120, -1))

        box = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Folder Options")

        hs = vboxsizer()
        hs.Add(self.chk_prefixed_name, 1, wx.ALL|wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND|wx.ALL, 0)
        box.AddSpacer(30)
        hs = hboxsizer()
        hs.Add(self.chk_unique_path, 1, wx.ALL|wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND|wx.ALL, 0)
        hs = hboxsizer()
        hs.Add(self.txt_unique_path, 1, wx.ALL|wx.EXPAND, 0)
        box.Add(hs, 0, wx.EXPAND|wx.ALL, 0)

        self.SetSizer(box)

        settings = Settings.load()
        self.chk_prefixed_name.SetValue(settings["unique_pathname"]["enabled"])
        self.chk_unique_path.SetValue(settings["generate_filenames"]["enabled"])
        self.txt_unique_path.SetValue(settings["generate_filenames"]["name"])
        

class MaxConnectionsPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.slider = wx.Slider(self, 
                                -1, 10, 0, 30, 
                                style=wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS|wx.SL_LABELS)

        hs = hboxsizer()
        hs.Add(self.slider, 1, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Maximum Connections")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)

        self.slider.SetValue(Settings.load()["max_connections"])


class FormSearchPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.chk_enable = wx.CheckBox(self, -1, "Enable")
        self.chk_include_host = wx.CheckBox(self, -1, "Include Forms from original Host")

        hs = hboxsizer()
        hs.Add(self.chk_enable, 0, wx.EXPAND|wx.ALL, STATICBOX_BORDER)
        hs.AddSpacer(DIALOG_BORDER)
        hs.Add(self.chk_include_host, 0, wx.EXPAND|wx.ALL, STATICBOX_BORDER)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Search Forms (can be slow)")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)

        self.SetSizer(box)

        formsearch = Settings.load()["form_search"]
        self.chk_enable.SetValue(formsearch["enabled"])
        self.chk_include_host.SetValue(formsearch["include_original_host"])


class ThumbnailOnlyPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.checkbox = wx.CheckBox(self, -1, "")
        self.checkbox.SetValue(True)

        hs = hboxsizer()
        hs.Add(self.checkbox, 1, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Thumbnail Links only")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)

        self.checkbox.SetValue(Settings.load()["thumbnails_only"])


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

        hs = hboxsizer()
        hs.Add(self.text_width, 1, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(label, 0, wx.ALIGN_BOTTOM, 0)
        hs.AddSpacer(10)
        hs.Add(self.text_height, 1, wx.ALL|wx.EXPAND, 0)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Minimum Resolution Size (width, height)")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)

        minsize = Settings.load()["minimum_image_resolution"]
        self.text_width.SetValue(minsize["width"])
        self.text_height.SetValue(minsize["height"])

class TimeoutPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        MAX_TIMEOUT = 60

        choices = list(map(lambda x: str(x+1), range(MAX_TIMEOUT)))

        self.choice = wx.Choice(self, -1,
                                choices=choices)
        
        self.choice.SetSelection(6)

        hs = hboxsizer()
        hs.Add(self.choice, 1, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Timeout")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)

        timeout = Settings.load()["connection_timeout"]
        if timeout > 0 and timeout <= 60:
            self.choice.SetSelection(timeout)


class OkCancelPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        btn_cancel = ThemedButton(self, wx.ID_CANCEL, "Cancel")
        btn_ok = ThemedButton(self, wx.ID_OK, "Save")

        hs = hboxsizer()

        hs.Add(btn_cancel, 0, wx.ALIGN_CENTER, 0)
        hs.Add(btn_ok, 0, wx.ALIGN_CENTER, 0)

        vs = vboxsizer()
        vs.Add(hs, 1, wx.ALIGN_CENTER, 0)

        self.SetSizer(vs)