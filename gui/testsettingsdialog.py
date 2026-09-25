import wx

import crawler.testoptions as testoptions


class TestServerOptionsDialog(wx.Dialog):

    def __init__(self, parent):
        super().__init__(
            parent,
            title="Test Server Options",
            style=wx.DEFAULT_DIALOG_STYLE
        )

        settings = testoptions.load_test_settings()

        panel = wx.Panel(self)

        count_label = wx.StaticText(panel, label="Number of test images:")
        self.image_count = wx.SpinCtrl(
            panel,
            min=1,
            max=100,
            initial=settings["image_count"],
            size=(90, -1)
        )

        port_label = wx.StaticText(panel, label="Server port:")
        self.port = wx.SpinCtrl(
            panel,
            min=1,
            max=65535,
            initial=settings["port"],
            size=(100, -1)
        )

        self.clean_downloads = wx.CheckBox(
            panel,
            label="Clean the dummy download folder before the test starts"
        )
        self.clean_downloads.SetValue(
            settings["clean_downloads_before_test"]
        )

        count_row = wx.BoxSizer(wx.HORIZONTAL)
        count_row.Add(count_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        count_row.Add(self.image_count, 0, wx.ALIGN_CENTER_VERTICAL)

        port_row = wx.BoxSizer(wx.HORIZONTAL)
        port_row.Add(port_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        port_row.Add(self.port, 0, wx.ALIGN_CENTER_VERTICAL)
        port_row.Add(wx.StaticText(panel, label="Default: 5000"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        hint = wx.StaticText(
            panel,
            label="Leave cleanup unticked when you want existing files kept for duplicate, skip, overwrite or rename testing."
        )
        hint.Wrap(480)

        btn_cancel = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        btn_save = wx.Button(panel, wx.ID_OK, "Save")
        btn_save.SetDefault()

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(btn_cancel, 0, wx.RIGHT, 8)
        buttons.Add(btn_save, 0)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(count_row, 0, wx.EXPAND | wx.ALL, 14)
        layout.Add(port_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        layout.Add(self.clean_downloads, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        layout.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        layout.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)
        layout.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 14)

        panel.SetSizer(layout)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(outer)
        self.SetMinSize((540, -1))
        self.CentreOnParent()

    def get_settings(self):
        return {
            "image_count": self.image_count.GetValue(),
            "clean_downloads_before_test": self.clean_downloads.GetValue(),
            "port": self.port.GetValue()
        }
