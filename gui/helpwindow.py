import os
import webbrowser
from pathlib import Path

import wx

try:
    import wx.html2 as webview
except ImportError:
    webview = None

import wx.html


APP_BACKGROUND = wx.Colour(244, 246, 249)
SIDEBAR_BACKGROUND = wx.Colour(248, 249, 251)
BORDER_COLOUR = wx.Colour(216, 221, 228)
TEXT_COLOUR = wx.Colour(45, 49, 55)


SECTIONS = [
    ("Getting Started", "getting-started"),
    ("Downloading", "downloading"),
    ("Results", "results"),
    ("Settings", "settings"),
    ("Test Server", "test-server"),
    ("Troubleshooting", "troubleshooting"),
    ("Browser Helper", "browser-helper"),
]


class HelpWindow(wx.Frame):

    def __init__(self, parent):
        super().__init__(
            parent,
            title="wxPixGrabber Help",
            size=(960, 680),
            style=wx.DEFAULT_FRAME_STYLE
        )

        self.help_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "docs", "help.html")
        )
        self.help_url = Path(self.help_path).as_uri()

        self.SetBackgroundColour(APP_BACKGROUND)

        panel = wx.Panel(self)
        panel.SetBackgroundColour(APP_BACKGROUND)

        sidebar = wx.Panel(panel, style=wx.BORDER_SIMPLE)
        sidebar.SetBackgroundColour(SIDEBAR_BACKGROUND)
        sidebar.SetMinSize((205, -1))

        title = wx.StaticText(sidebar, label="Help")
        title_font = title.GetFont()
        title_font.SetPointSize(15)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        title.SetForegroundColour(TEXT_COLOUR)
        title.SetBackgroundColour(SIDEBAR_BACKGROUND)

        subtitle = wx.StaticText(sidebar, label="wxPixGrabber")
        subtitle.SetForegroundColour(wx.Colour(105, 112, 122))
        subtitle.SetBackgroundColour(SIDEBAR_BACKGROUND)

        self.navigation = wx.ListBox(
            sidebar,
            choices=[label for label, anchor in SECTIONS],
            style=wx.LB_SINGLE
        )
        self.navigation.SetSelection(0)
        self.navigation.Bind(wx.EVT_LISTBOX, self._on_section)

        btn_browser = wx.Button(sidebar, label="Open in Browser")
        btn_browser.Bind(wx.EVT_BUTTON, self._on_open_browser)

        sidebar_sizer = wx.BoxSizer(wx.VERTICAL)
        sidebar_sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        sidebar_sizer.Add(subtitle, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        sidebar_sizer.Add(self.navigation, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        sidebar_sizer.Add(btn_browser, 0, wx.EXPAND | wx.ALL, 10)
        sidebar.SetSizer(sidebar_sizer)

        content = wx.Panel(panel, style=wx.BORDER_SIMPLE)
        content.SetBackgroundColour(wx.WHITE)

        if webview is not None:
            self.viewer = webview.WebView.New(content)
            self.viewer.LoadURL(self.help_url)
        else:
            self.viewer = wx.html.HtmlWindow(content)
            self.viewer.LoadPage(self.help_path)

        content_sizer = wx.BoxSizer(wx.VERTICAL)
        content_sizer.Add(self.viewer, 1, wx.EXPAND)
        content.SetSizer(content_sizer)

        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(sidebar, 0, wx.EXPAND | wx.ALL, 12)
        layout.Add(content, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 12)
        panel.SetSizer(layout)

        self.CentreOnParent()

    def _on_section(self, evt):
        selection = self.navigation.GetSelection()
        if selection == wx.NOT_FOUND:
            return

        anchor = SECTIONS[selection][1]
        if webview is not None:
            self.viewer.LoadURL(f"{self.help_url}#{anchor}")
        else:
            self.viewer.LoadPage(f"{self.help_path}#{anchor}")

    def _on_open_browser(self, evt):
        webbrowser.open(self.help_url)
