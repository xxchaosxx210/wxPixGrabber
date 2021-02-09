import wx

import wx.lib.scrolledpanel as scrolled

from app_theme import (
    ThemedButton,
    hboxsizer,
    vboxsizer,
    DIALOG_BORDER
)


class SettingsDialog(wx.Dialog):

    def __init__(self, parent, id, title, size, pos, style, name):
        super().__init__()
        self.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        self.Create(parent, id, title, pos, size, style, name)

        self.panel = SetttingsPanel(self, -1)
        self.ok_cancel_panel = OkCancelPanel(self, -1)

        vs = vboxsizer()

        hs = hboxsizer()
        hs.Add(self.panel, 1, wx.ALL|wx.EXPAND, 10)
        vs.Add(hs, 1, wx.ALL|wx.EXPAND, 0)

        hs = hboxsizer()
        hs.Add(self.ok_cancel_panel, 1, wx.ALL|wx.EXPAND, 10)
        vs.Add(hs, 0, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(vs)

        self.SetSize(400, 400)


class SetttingsPanel(scrolled.ScrolledPanel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.max_connections = MaxConnectionsPanel(self, -1)
        self.timeout = TimeoutPanel(self, -1)
        self.minsize_panel = MinWidthHeightPanel(self, -1)
        self.thumb_panel = ThumbnailOnlyPanel(self, -1)
        self.savepath = SaveFolderPanel(self, -1)

        vs = vboxsizer()

        hs = hboxsizer()
        hs.Add(self.max_connections, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.timeout, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.ALIGN_CENTER, 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.minsize_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.ALIGN_CENTER , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.thumb_panel, 0, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.ALIGN_CENTER , 0)
        vs.AddSpacer(DIALOG_BORDER)

        hs = hboxsizer()
        hs.Add(self.savepath, 1, wx.EXPAND|wx.ALL, 0)
        vs.Add(hs, 0, wx.EXPAND|wx.ALL , 0)
        vs.AddSpacer(DIALOG_BORDER)

        self.SetSizer(vs)
        self.Fit()

        self.SetAutoLayout(1)
        self.SetupScrolling()


class SaveFolderPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.text = wx.TextCtrl(self, -1, "")
        btn_dir = wx.Button(self, -1, "Browse", size=(68, -1))

        btn_dir.Bind(wx.EVT_BUTTON, self.on_dir_button, self)

        hs = hboxsizer()
        hs.Add(self.text, 1, wx.ALL|wx.EXPAND, 0)
        hs.AddSpacer(10)
        hs.Add(btn_dir, 0, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Save Path")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)
    
    def on_dir_button(self, evt):
        dir = wx.DirDialog(
            self,
            "Save Folder",
            "",
            style=wx.DD_DIR_MUST_EXIST,
        )
        dir.CenterOnParent()
        if dir.ShowModal() == wx.ID_OK:
            print(dir.GetPath())
        dir.Destroy()
        

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


class MinWidthHeightPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.text_width = wx.TextCtrl(self,
                                      -1, 
                                      "200",
                                      style=wx.TE_CENTER)
        
        self.text_height = wx.TextCtrl(self,
                                        -1,
                                        "200",
                                        style=wx.TE_CENTER)

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


class TimeoutPanel(wx.Panel):

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        choices = list(map(lambda x: str(x+1), range(60)))

        self.choice = wx.Choice(self, -1,
                                choices=choices)
        
        self.choice.SetSelection(6)

        hs = hboxsizer()
        hs.AddSpacer(100)
        hs.Add(self.choice, 1, wx.ALL|wx.EXPAND, 0)
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Timeout")
        box.Add(hs, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(box)


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