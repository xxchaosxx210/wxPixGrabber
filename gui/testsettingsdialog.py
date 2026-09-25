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

        self.delete_downloads = wx.CheckBox(
            panel,
            label="Delete downloaded test files when the test finishes or is cancelled"
        )
        self.delete_downloads.SetValue(
            settings["delete_downloads_after_test"]
        )

        count_row = wx.BoxSizer(wx.HORIZONTAL)
        count_row.Add(count_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        count_row.Add(self.image_count, 0, wx.ALIGN_CENTER_VERTICAL)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(count_row, 0, wx.EXPAND | wx.ALL, 14)
        layout.Add(self.delete_downloads, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        layout.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)
        layout.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 14)

        panel.SetSizer(layout)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizerAndFit(outer)
        self.SetMinSize((520, -1))
        self.CentreOnParent()

    def get_settings(self):
        return {
            "image_count": self.image_count.GetValue(),
            "delete_downloads_after_test": self.delete_downloads.GetValue()
        }
