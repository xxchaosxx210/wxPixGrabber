import copy
import os
import webbrowser

import wx
import wx.lib.scrolledpanel as scrolled

import crawler.options as options
from crawler.options import SQL_PATH


APP_BACKGROUND = wx.Colour(244, 246, 249)
SIDEBAR_BACKGROUND = wx.Colour(248, 249, 251)
CARD_BACKGROUND = wx.Colour(255, 255, 255)
BORDER_COLOUR = wx.Colour(216, 221, 228)
TEXT_COLOUR = wx.Colour(45, 49, 55)
MUTED_TEXT = wx.Colour(105, 112, 122)
PRIMARY = wx.Colour(30, 111, 232)
NAV_SELECTED = wx.Colour(225, 237, 252)
NAV_HOVER = wx.Colour(238, 243, 249)

PAGE_NAMES = [
    "General",
    "Downloads",
    "Images",
    "Network & Cookies",
    "Filters",
    "Advanced",
    "About",
]


def _font(window, size=None, bold=False):
    font = window.GetFont()
    if size is not None:
        font.SetPointSize(size)
    if bold:
        font.SetWeight(wx.FONTWEIGHT_BOLD)
    return font


def _label(parent, text, width=155):
    label = wx.StaticText(parent, label=text)
    label.SetForegroundColour(TEXT_COLOUR)
    label.SetMinSize((width, -1))
    return label


class NavItem(wx.Panel):

    def __init__(self, parent, label, index, on_select):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.index = index
        self.on_select = on_select
        self.selected = False
        self.SetMinSize((-1, 34))
        self.SetBackgroundColour(SIDEBAR_BACKGROUND)

        self.label = wx.StaticText(self, label=label)
        self.label.SetForegroundColour(TEXT_COLOUR)
        self.label.SetBackgroundColour(SIDEBAR_BACKGROUND)

        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(self.label, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 12)
        self.SetSizer(layout)

        for control in (self, self.label):
            control.Bind(wx.EVT_LEFT_DOWN, self._on_click)
            control.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
            control.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)

    def set_selected(self, selected):
        self.selected = selected
        background = NAV_SELECTED if selected else SIDEBAR_BACKGROUND
        self.SetBackgroundColour(background)
        self.label.SetBackgroundColour(background)
        self.label.SetForegroundColour(PRIMARY if selected else TEXT_COLOUR)
        self.label.SetFont(_font(self.label, bold=selected))
        self.Refresh()

    def _on_click(self, evt):
        self.on_select(self.index)

    def _on_enter(self, evt):
        if not self.selected:
            self.SetBackgroundColour(NAV_HOVER)
            self.label.SetBackgroundColour(NAV_HOVER)
            self.Refresh()

    def _on_leave(self, evt):
        # Moving between this panel and its child label can generate a leave
        # event even though the pointer is still visually inside the nav item.
        # Only remove the hover highlight once the pointer has actually left
        # the whole item.
        mouse_pos = self.ScreenToClient(wx.GetMousePosition())
        if self.GetClientRect().Contains(mouse_pos):
            return

        if not self.selected:
            self.SetBackgroundColour(SIDEBAR_BACKGROUND)
            self.label.SetBackgroundColour(SIDEBAR_BACKGROUND)
            self.Refresh()


class CardPanel(wx.Panel):

    def __init__(self, parent, title):
        super().__init__(parent, style=wx.BORDER_THEME)
        self.SetBackgroundColour(CARD_BACKGROUND)

        heading = wx.StaticText(self, label=title)
        heading.SetBackgroundColour(CARD_BACKGROUND)
        heading.SetForegroundColour(TEXT_COLOUR)
        heading.SetFont(_font(heading, 9, True))

        self.body = wx.BoxSizer(wx.VERTICAL)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        layout.AddSpacer(7)
        layout.Add(self.body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(layout)


class SettingsPage(scrolled.ScrolledPanel):

    def __init__(self, parent, title, subtitle):
        super().__init__(parent, style=wx.TAB_TRAVERSAL)
        self.SetBackgroundColour(APP_BACKGROUND)

        heading = wx.StaticText(self, label=title)
        heading.SetForegroundColour(TEXT_COLOUR)
        heading.SetFont(_font(heading, 16, True))

        description = wx.StaticText(self, label=subtitle)
        description.SetForegroundColour(MUTED_TEXT)

        self.layout = wx.BoxSizer(wx.VERTICAL)
        self.layout.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
        self.layout.Add(description, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
        self.layout.AddSpacer(12)

        self.SetSizer(self.layout)

    def add_card(self, title):
        card = CardPanel(self, title)
        self.layout.Add(card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        return card

    def finish(self):
        self.SetupScrolling(scroll_x=False, scroll_y=True, rate_y=10)


class GeneralPage(SettingsPage):

    def __init__(self, parent, dialog):
        super().__init__(parent, "General", "Basic application settings and behaviour.")
        self.dialog = dialog

        profile = self.add_card("Profile")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(profile, "Active profile:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.profile_choice = wx.Choice(profile)
        row.Add(self.profile_choice, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.btn_delete_profile = wx.Button(profile, label="Delete", size=(72, -1))
        self.btn_new_profile = wx.Button(profile, label="New", size=(72, -1))
        row.Add(self.btn_delete_profile, 0, wx.RIGHT, 6)
        row.Add(self.btn_new_profile, 0)
        profile.body.Add(row, 0, wx.EXPAND)

        behaviour = self.add_card("Application")
        self.auto_download = wx.CheckBox(behaviour, label="Automatically start downloading after links are fetched")
        self.notify_done = wx.CheckBox(behaviour, label="Notify me when a download has finished")
        self.results_collapsed_on_start = wx.CheckBox(
            behaviour,
            label="Start with Results section collapsed"
        )
        self.compact_bottom_right = wx.CheckBox(
            behaviour,
            label="Move compact view to bottom-right corner"
        )
        for control in (
            self.auto_download,
            self.notify_done,
            self.results_collapsed_on_start,
            self.compact_bottom_right,
        ):
            behaviour.body.Add(control, 0, wx.BOTTOM, 7)

        self.btn_new_profile.Bind(wx.EVT_BUTTON, dialog._on_new_profile)
        self.btn_delete_profile.Bind(wx.EVT_BUTTON, dialog._on_delete_profile)
        self.profile_choice.Bind(wx.EVT_CHOICE, dialog._on_profile_choice)

        self.finish()

    def refresh_profiles(self, selected=None):
        profiles = options.load_profiles()
        if "default" not in profiles:
            profiles.insert(0, "default")
        profiles = sorted(set(profiles), key=lambda name: (name != "default", name.lower()))
        self.profile_choice.SetItems(profiles)
        if selected and selected in profiles:
            self.profile_choice.SetStringSelection(selected)
        elif profiles:
            self.profile_choice.SetSelection(0)


class DownloadsPage(SettingsPage):

    def __init__(self, parent):
        super().__init__(parent, "Downloads", "Destination, filename and download performance options.")

        destination = self.add_card("Destination")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(destination, "Save directory:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.save_path = wx.TextCtrl(destination)
        self.btn_browse = wx.Button(destination, label="Browse...", size=(86, -1))
        row.Add(self.save_path, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(self.btn_browse, 0)
        destination.body.Add(row, 0, wx.EXPAND)

        handling = self.add_card("File handling")
        self.unique_path = wx.CheckBox(handling, label="Create a unique folder from the page title")
        self.generate_filenames = wx.CheckBox(handling, label="Generate prefixed filenames")
        handling.body.Add(self.unique_path, 0, wx.BOTTOM, 7)
        handling.body.Add(self.generate_filenames, 0, wx.BOTTOM, 7)

        prefix_row = wx.BoxSizer(wx.HORIZONTAL)
        prefix_row.Add(_label(handling, "Filename prefix:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.filename_prefix = wx.TextCtrl(handling, size=(160, -1))
        prefix_row.Add(self.filename_prefix, 0)
        handling.body.Add(prefix_row, 0, wx.EXPAND | wx.BOTTOM, 9)

        exists_row = wx.BoxSizer(wx.HORIZONTAL)
        exists_row.Add(_label(handling, "If file already exists:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.file_exists = wx.Choice(handling, choices=["Skip", "Overwrite", "Rename"])
        exists_row.Add(self.file_exists, 0)
        handling.body.Add(exists_row, 0, wx.EXPAND)

        performance = self.add_card("Performance")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(performance, "Maximum connections:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.max_connections = wx.SpinCtrl(performance, min=1, max=100, initial=10, size=(90, -1))
        row.Add(self.max_connections, 0)
        performance.body.Add(row, 0, wx.EXPAND | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(performance, "Connection timeout:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.timeout = wx.SpinCtrl(performance, min=1, max=60, initial=5, size=(90, -1))
        row.Add(self.timeout, 0, wx.RIGHT, 7)
        row.Add(wx.StaticText(performance, label="seconds"), 0, wx.ALIGN_CENTER_VERTICAL)
        performance.body.Add(row, 0, wx.EXPAND)

        self.btn_browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self.generate_filenames.Bind(wx.EVT_CHECKBOX, self._on_generate_filenames)

        self.finish()

    def _on_browse(self, evt):
        dlg = wx.DirDialog(
            self,
            "Save Folder",
            self.save_path.GetValue(),
            style=wx.DD_DIR_MUST_EXIST,
        )
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            self.save_path.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_generate_filenames(self, evt):
        self.filename_prefix.Enable(self.generate_filenames.GetValue())


class ImagesPage(SettingsPage):

    FORMATS = ("JPG", "PNG", "GIF", "BMP", "ICO", "TIFF", "TGA", "WEBP")

    def __init__(self, parent):
        super().__init__(parent, "Images", "Image discovery, dimensions and supported file formats.")

        discovery = self.add_card("Image discovery")
        self.thumbnails_only = wx.CheckBox(
            discovery,
            label="Prefer links surrounding thumbnails instead of the thumbnail image itself"
        )
        discovery.body.Add(self.thumbnails_only, 0, wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(discovery, "Minimum resolution:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.min_width = wx.SpinCtrl(discovery, min=0, max=99999, initial=200, size=(90, -1))
        self.min_height = wx.SpinCtrl(discovery, min=0, max=99999, initial=200, size=(90, -1))
        row.Add(self.min_width, 0, wx.RIGHT, 7)
        row.Add(wx.StaticText(discovery, label="×"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 7)
        row.Add(self.min_height, 0, wx.RIGHT, 7)
        row.Add(wx.StaticText(discovery, label="pixels"), 0, wx.ALIGN_CENTER_VERTICAL)
        discovery.body.Add(row, 0, wx.EXPAND)

        formats = self.add_card("Image formats")
        self.format_checks = {}
        grid = wx.FlexGridSizer(cols=4, hgap=18, vgap=9)
        for name in self.FORMATS:
            checkbox = wx.CheckBox(formats, label=name)
            self.format_checks[name.lower()] = checkbox
            grid.Add(checkbox, 0)
        formats.body.Add(grid, 0, wx.EXPAND)

        self.finish()


class NetworkPage(SettingsPage):

    BROWSERS = ("Firefox", "Chrome", "Opera", "Edge", "All")

    def __init__(self, parent):
        super().__init__(parent, "Network & Cookies", "Choose browser cookies and the User-Agent PixGrabber sends with requests.")

        cookies = self.add_card("Browser cookies")
        intro = wx.StaticText(
            cookies,
            label="Use cookies from one browser profile when a host requires an authenticated or age-confirmed session."
        )
        intro.SetForegroundColour(MUTED_TEXT)
        intro.Wrap(560)
        cookies.body.Add(intro, 0, wx.EXPAND | wx.BOTTOM, 12)

        self.cookie_radios = {}
        for index, browser in enumerate(self.BROWSERS):
            style = wx.RB_GROUP if index == 0 else 0
            radio = wx.RadioButton(cookies, label=browser, style=style)
            self.cookie_radios[browser.lower()] = radio
            cookies.body.Add(radio, 0, wx.BOTTOM, 6)

        user_agent = self.add_card("User-Agent")
        ua_intro = wx.StaticText(
            user_agent,
            label="Automatic is recommended. It matches the installed Firefox version."
        )
        ua_intro.SetForegroundColour(MUTED_TEXT)
        ua_intro.Wrap(560)
        user_agent.body.Add(ua_intro, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.user_agent_automatic = wx.RadioButton(
            user_agent,
            label="Automatic (recommended)",
            style=wx.RB_GROUP
        )
        self.user_agent_custom = wx.RadioButton(user_agent, label="Custom User-Agent")
        user_agent.body.Add(self.user_agent_automatic, 0, wx.BOTTOM, 6)
        user_agent.body.Add(self.user_agent_custom, 0, wx.BOTTOM, 8)

        ua_row = wx.BoxSizer(wx.HORIZONTAL)
        self.user_agent_text = wx.TextCtrl(user_agent)
        self.user_agent_text.SetHint("Paste a complete User-Agent string")
        self.btn_reset_user_agent = wx.Button(user_agent, label="Reset to automatic", size=(125, -1))
        ua_row.Add(self.user_agent_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        ua_row.Add(self.btn_reset_user_agent, 0)
        user_agent.body.Add(ua_row, 0, wx.EXPAND)

        note = wx.StaticText(
            user_agent,
            label="If Custom is selected but the box is empty, PixGrabber falls back to Automatic."
        )
        note.SetForegroundColour(MUTED_TEXT)
        note.Wrap(560)
        user_agent.body.Add(note, 0, wx.EXPAND | wx.TOP, 8)

        proxy_note = wx.StaticText(
            cookies,
            label="Proxy configuration remains in the settings file but is not currently used by the downloader."
        )
        proxy_note.SetForegroundColour(MUTED_TEXT)
        proxy_note.Wrap(560)
        cookies.body.AddSpacer(8)
        cookies.body.Add(proxy_note, 0, wx.EXPAND)

        self.user_agent_automatic.Bind(wx.EVT_RADIOBUTTON, self._on_user_agent_mode)
        self.user_agent_custom.Bind(wx.EVT_RADIOBUTTON, self._on_user_agent_mode)
        self.btn_reset_user_agent.Bind(wx.EVT_BUTTON, self._on_reset_user_agent)

        self.finish()

    def _sync_user_agent_controls(self):
        self.user_agent_text.Enable(self.user_agent_custom.GetValue())

    def _on_user_agent_mode(self, evt):
        self._sync_user_agent_controls()

    def _on_reset_user_agent(self, evt):
        self.user_agent_automatic.SetValue(True)
        self.user_agent_custom.SetValue(False)
        self.user_agent_text.SetValue("")
        self._sync_user_agent_controls()


class FiltersPage(SettingsPage):

    def __init__(self, parent):
        super().__init__(parent, "Filters", "Control which links and forms are considered during discovery.")

        filters = self.add_card("Search filters")
        self.filters_enabled = wx.CheckBox(filters, label="Enable URL filters")
        filters.body.Add(self.filters_enabled, 0, wx.BOTTOM, 8)

        self.filter_list = wx.ListBox(filters, choices=[], style=wx.LB_SINGLE | wx.LB_SORT)
        self.filter_list.SetMinSize((-1, 150))
        filters.body.Add(self.filter_list, 1, wx.EXPAND | wx.BOTTOM, 8)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self.filter_text = wx.TextCtrl(filters, style=wx.TE_PROCESS_ENTER)
        self.btn_add_filter = wx.Button(filters, label="Add", size=(65, -1))
        self.btn_delete_filter = wx.Button(filters, label="Delete", size=(70, -1))
        self.btn_clear_filters = wx.Button(filters, label="Delete All", size=(82, -1))
        add_row.Add(self.filter_text, 1, wx.RIGHT, 7)
        add_row.Add(self.btn_add_filter, 0, wx.RIGHT, 6)
        add_row.Add(self.btn_delete_filter, 0, wx.RIGHT, 6)
        add_row.Add(self.btn_clear_filters, 0)
        filters.body.Add(add_row, 0, wx.EXPAND)

        forms = self.add_card("Form search")
        self.form_search = wx.CheckBox(forms, label="Search forms (can be slower)")
        self.include_original_host = wx.CheckBox(forms, label="Include forms from the original host")
        forms.body.Add(self.form_search, 0, wx.BOTTOM, 7)
        forms.body.Add(self.include_original_host, 0)

        self.btn_add_filter.Bind(wx.EVT_BUTTON, self._on_add_filter)
        self.btn_delete_filter.Bind(wx.EVT_BUTTON, self._on_delete_filter)
        self.btn_clear_filters.Bind(wx.EVT_BUTTON, lambda evt: self.filter_list.Clear())
        self.filter_text.Bind(wx.EVT_TEXT_ENTER, self._on_add_filter)

        self.finish()

    def _on_add_filter(self, evt):
        text = self.filter_text.GetValue().strip()
        if not text:
            return
        if text in self.filter_list.GetItems():
            wx.MessageBox("That filter already exists.", "Search Filters", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.filter_list.Append(text)
        self.filter_text.SetValue("")

    def _on_delete_filter(self, evt):
        selection = self.filter_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.filter_list.Delete(selection)


class AdvancedPage(SettingsPage):

    def __init__(self, parent):
        super().__init__(parent, "Advanced", "Maintenance and local application data.")

        maintenance = self.add_card("Cache")
        cache_row = wx.BoxSizer(wx.HORIZONTAL)
        cache_row.Add(_label(maintenance, "Cache database:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        cache_path = wx.TextCtrl(maintenance, value=SQL_PATH, style=wx.TE_READONLY)
        self.btn_clear_cache = wx.Button(maintenance, label="Clear Cache", size=(88, -1))
        cache_row.Add(cache_path, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        cache_row.Add(self.btn_clear_cache, 0)
        maintenance.body.Add(cache_row, 0, wx.EXPAND)

        files = self.add_card("Application data")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(files, "Settings file:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row.Add(wx.TextCtrl(files, value=options.SETTINGS_PATH, style=wx.TE_READONLY), 1)
        files.body.Add(row, 0, wx.EXPAND | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(_label(files, "Profiles folder:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row.Add(wx.TextCtrl(files, value=options.PROFILES_PATH, style=wx.TE_READONLY), 1)
        files.body.Add(row, 0, wx.EXPAND)

        self.btn_clear_cache.Bind(wx.EVT_BUTTON, self._on_clear_cache)

        self.finish()

    def _on_clear_cache(self, evt):
        dlg = wx.MessageDialog(
            self,
            "Are you sure you want to delete the cache?",
            "Clear Cache",
            style=wx.CANCEL | wx.OK | wx.CENTER | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_OK:
            if os.path.exists(SQL_PATH):
                os.remove(SQL_PATH)
                wx.GetApp().window.sbar.SetStatusText("Cache has been cleared")
        dlg.Destroy()


class AboutPage(SettingsPage):

    def __init__(self, parent):
        super().__init__(parent, "About", "Application information and project links.")

        about = self.add_card("wxPixGrabber")
        name = wx.StaticText(about, label="PixGrabber")
        name.SetFont(_font(name, 14, True))
        about.body.Add(name, 0, wx.BOTTOM, 5)
        about.body.Add(wx.StaticText(about, label=f"Version {options.VERSION}"), 0, wx.BOTTOM, 10)

        description = wx.StaticText(
            about,
            label="A wxPython image-link crawler and downloader."
        )
        description.SetForegroundColour(MUTED_TEXT)
        about.body.Add(description, 0, wx.BOTTOM, 14)

        self.btn_project = wx.Button(about, label="Open GitHub project")
        about.body.Add(self.btn_project, 0)
        self.btn_project.Bind(wx.EVT_BUTTON, lambda evt: webbrowser.open(options.GIT_SOURCE))

        self.finish()


class SettingsDialog(wx.Dialog):

    def __init__(self, parent, id, title, size, pos, style, name, settings):
        super().__init__(
            parent,
            id=id,
            title=title,
            pos=pos,
            size=(820, 560),
            style=style | wx.RESIZE_BORDER,
            name=name
        )

        self.app = wx.GetApp()
        self.settings = copy.deepcopy(settings)
        self.SetBackgroundColour(APP_BACKGROUND)
        self.SetMinSize((720, 500))

        root = wx.Panel(self)
        root.SetBackgroundColour(APP_BACKGROUND)

        sidebar = wx.Panel(root, style=wx.BORDER_THEME)
        sidebar.SetBackgroundColour(SIDEBAR_BACKGROUND)
        sidebar.SetMinSize((165, -1))

        sidebar_title = wx.StaticText(sidebar, label="Options")
        sidebar_title.SetForegroundColour(TEXT_COLOUR)
        sidebar_title.SetBackgroundColour(SIDEBAR_BACKGROUND)
        sidebar_title.SetFont(_font(sidebar_title, 12, True))

        self.nav_items = []
        nav_items = wx.BoxSizer(wx.VERTICAL)
        for index, page_name in enumerate(PAGE_NAMES):
            item = NavItem(sidebar, page_name, index, self._select_page)
            self.nav_items.append(item)
            nav_items.Add(item, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        nav_layout = wx.BoxSizer(wx.VERTICAL)
        nav_layout.Add(sidebar_title, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 12)
        nav_layout.Add(nav_items, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        nav_layout.AddStretchSpacer(1)
        sidebar.SetSizer(nav_layout)

        self.book = wx.Simplebook(root)
        self.general_page = GeneralPage(self.book, self)
        self.downloads_page = DownloadsPage(self.book)
        self.images_page = ImagesPage(self.book)
        self.network_page = NetworkPage(self.book)
        self.filters_page = FiltersPage(self.book)
        self.advanced_page = AdvancedPage(self.book)
        self.about_page = AboutPage(self.book)

        self.pages = [
            self.general_page,
            self.downloads_page,
            self.images_page,
            self.network_page,
            self.filters_page,
            self.advanced_page,
            self.about_page,
        ]
        for page in self.pages:
            self.book.AddPage(page, "")

        body = wx.BoxSizer(wx.HORIZONTAL)
        body.Add(sidebar, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 8)
        body.Add(self.book, 1, wx.EXPAND | wx.ALL, 8)

        footer = wx.Panel(root)
        footer.SetBackgroundColour(APP_BACKGROUND)

        self.btn_defaults = wx.Button(footer, label="Reset to Defaults")
        self.btn_apply = wx.Button(footer, label="Apply")
        btn_cancel = wx.Button(footer, wx.ID_CANCEL, "Cancel")
        self.btn_ok = wx.Button(footer, wx.ID_OK, "OK")
        self.btn_ok.SetDefault()

        footer_layout = wx.BoxSizer(wx.HORIZONTAL)
        footer_layout.Add(self.btn_defaults, 0)
        footer_layout.AddStretchSpacer(1)
        footer_layout.Add(self.btn_apply, 0, wx.RIGHT, 7)
        footer_layout.Add(btn_cancel, 0, wx.RIGHT, 7)
        footer_layout.Add(self.btn_ok, 0)
        footer.SetSizer(footer_layout)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(body, 1, wx.EXPAND)
        outer.Add(wx.StaticLine(root), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        outer.Add(footer, 0, wx.EXPAND | wx.ALL, 8)
        root.SetSizer(outer)

        frame_layout = wx.BoxSizer(wx.VERTICAL)
        frame_layout.Add(root, 1, wx.EXPAND)
        self.SetSizer(frame_layout)

        self.btn_defaults.Bind(wx.EVT_BUTTON, self._on_defaults)
        self.btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
        self.btn_ok.Bind(wx.EVT_BUTTON, self._on_ok)

        self.load_settings(settings)
        self._select_page(0)
        self.CentreOnParent()

    def _select_page(self, index):
        self.book.ChangeSelection(index)
        for item_index, item in enumerate(self.nav_items):
            item.set_selected(item_index == index)

    def load_settings(self, settings):
        self.settings = copy.deepcopy(settings)

        general = self.general_page
        profile_name = settings.get("profile-name", "default")
        general.refresh_profiles(profile_name)
        general.auto_download.SetValue(settings.get("auto-download", False))
        general.notify_done.SetValue(settings.get("notify-done", True))
        general.results_collapsed_on_start.SetValue(
            settings.get("results-collapsed-on-start", True)
        )
        general.compact_bottom_right.SetValue(
            settings.get("compact-bottom-right", True)
        )

        downloads = self.downloads_page
        downloads.save_path.SetValue(settings.get("save_path", ""))
        downloads.unique_path.SetValue(settings.get("unique_pathname", {}).get("enabled", True))
        downloads.generate_filenames.SetValue(settings.get("generate_filenames", {}).get("enabled", True))
        downloads.filename_prefix.SetValue(settings.get("generate_filenames", {}).get("name", "image"))
        downloads.filename_prefix.Enable(downloads.generate_filenames.GetValue())

        file_exists = settings.get("file_exists", "overwrite").capitalize()
        if not downloads.file_exists.SetStringSelection(file_exists):
            downloads.file_exists.SetStringSelection("Overwrite")

        downloads.max_connections.SetValue(int(settings.get("max_connections", 10)))
        timeout = int(settings.get("connection_timeout", 5))
        downloads.timeout.SetValue(max(1, min(60, timeout)))

        images = self.images_page
        images.thumbnails_only.SetValue(settings.get("thumbnails_only", True))
        minimum = settings.get("minimum_image_resolution", {"width": 200, "height": 200})
        images.min_width.SetValue(int(minimum.get("width", 200)))
        images.min_height.SetValue(int(minimum.get("height", 200)))

        enabled_formats = settings.get("images_to_search", {})
        for key, checkbox in images.format_checks.items():
            checkbox.SetValue(bool(enabled_formats.get(key, key in ("jpg", "webp"))))

        cookies = settings.get("cookies", {})
        selected_cookie = "firefox"
        for key in self.network_page.cookie_radios:
            if cookies.get(key, False):
                selected_cookie = key
                break
        for key, radio in self.network_page.cookie_radios.items():
            radio.SetValue(key == selected_cookie)

        user_agent = settings.get("user_agent", {"mode": "automatic", "custom": ""})
        user_agent_mode = str(user_agent.get("mode", "automatic")).lower()
        self.network_page.user_agent_automatic.SetValue(user_agent_mode != "custom")
        self.network_page.user_agent_custom.SetValue(user_agent_mode == "custom")
        self.network_page.user_agent_text.SetValue(str(user_agent.get("custom", "")))
        self.network_page._sync_user_agent_controls()

        filter_settings = settings.get("filter-search", {"enabled": True, "filters": []})
        filters = self.filters_page
        filters.filters_enabled.SetValue(filter_settings.get("enabled", True))
        filters.filter_list.SetItems(list(filter_settings.get("filters", [])))

        forms = settings.get("form_search", {"enabled": True, "include_original_host": False})
        filters.form_search.SetValue(forms.get("enabled", True))
        filters.include_original_host.SetValue(forms.get("include_original_host", False))

    def get_settings(self):
        settings = copy.deepcopy(self.settings)

        settings["profile-name"] = (
            self.general_page.profile_choice.GetStringSelection() or "default"
        )
        settings["auto-download"] = self.general_page.auto_download.GetValue()
        settings["notify-done"] = self.general_page.notify_done.GetValue()
        settings["results-collapsed-on-start"] = (
            self.general_page.results_collapsed_on_start.GetValue()
        )
        settings["compact-bottom-right"] = (
            self.general_page.compact_bottom_right.GetValue()
        )

        settings["save_path"] = self.downloads_page.save_path.GetValue()

        settings.setdefault("unique_pathname", {})
        settings["unique_pathname"]["enabled"] = self.downloads_page.unique_path.GetValue()

        settings.setdefault("generate_filenames", {})
        settings["generate_filenames"]["enabled"] = self.downloads_page.generate_filenames.GetValue()
        settings["generate_filenames"]["name"] = self.downloads_page.filename_prefix.GetValue()

        settings["file_exists"] = (
            self.downloads_page.file_exists.GetStringSelection() or "Overwrite"
        ).lower()
        settings["max_connections"] = self.downloads_page.max_connections.GetValue()
        settings["connection_timeout"] = self.downloads_page.timeout.GetValue()

        settings["thumbnails_only"] = self.images_page.thumbnails_only.GetValue()
        settings["minimum_image_resolution"] = {
            "width": self.images_page.min_width.GetValue(),
            "height": self.images_page.min_height.GetValue(),
        }
        settings["images_to_search"] = {
            key: checkbox.GetValue()
            for key, checkbox in self.images_page.format_checks.items()
        }

        settings["cookies"] = {
            key: radio.GetValue()
            for key, radio in self.network_page.cookie_radios.items()
        }
        settings["user_agent"] = {
            "mode": "custom" if self.network_page.user_agent_custom.GetValue() else "automatic",
            "custom": self.network_page.user_agent_text.GetValue().strip(),
        }

        settings["filter-search"] = {
            "enabled": self.filters_page.filters_enabled.GetValue(),
            "filters": list(self.filters_page.filter_list.GetItems()),
        }

        settings["form_search"] = {
            "enabled": self.filters_page.form_search.GetValue(),
            "include_original_host": self.filters_page.include_original_host.GetValue(),
        }

        return settings

    def _on_apply(self, evt):
        settings = self.get_settings()
        options.save_settings(settings)
        self.settings = copy.deepcopy(settings)
        self.app.window.set_profile_status(settings["profile-name"])
        self.app.window.SetStatusText("Settings applied")

    def _on_ok(self, evt):
        self.EndModal(wx.ID_OK)

    def _on_defaults(self, evt):
        defaults = copy.deepcopy(options.DEFAULT_SETTINGS)
        current_profile = self.general_page.profile_choice.GetStringSelection()
        if current_profile:
            defaults["profile-name"] = current_profile
        self.load_settings(defaults)

    def _on_profile_choice(self, evt):
        name = evt.GetString()
        if options.use_profile(name):
            self.app.window.set_profile_status(name)
            self.load_settings(options.load_settings())

    def _on_new_profile(self, evt):
        dlg = wx.TextEntryDialog(self, "Name the profile", "New Profile")
        if dlg.ShowModal() == wx.ID_OK:
            name = options.format_filename(dlg.GetValue().strip())
            if name:
                settings = self.get_settings()
                settings["profile-name"] = name
                options.save_profile(settings)
                options.use_profile(name)
                self.app.window.set_profile_status(name)
                self.load_settings(options.load_settings())
        dlg.Destroy()

    def _on_delete_profile(self, evt):
        name = self.general_page.profile_choice.GetStringSelection()
        try:
            if options.delete_profile(name):
                settings = options.load_settings()
                self.app.window.set_profile_status(settings.get("profile-name", "default"))
                self.load_settings(settings)
        except NameError as err:
            wx.MessageBox(str(err), "Profile", wx.OK | wx.ICON_ERROR, self)
