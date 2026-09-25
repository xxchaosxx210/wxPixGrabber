import wx

from gui.style import (
    CARD_BACKGROUND,
    BORDER_COLOUR,
    SUCCESS,
    IGNORED_TEXT,
    ERROR_TEXT,
    NEUTRAL_TEXT,
    bold_font,
    dip,
)


class CompletionToast(wx.Frame):
    """Small non-blocking completion toast anchored to the PixGrabber window."""

    HOLD_MS = 3500
    FADE_INTERVAL_MS = 35
    FADE_STEP = 24

    def __init__(self, parent, saved=0, ignored=0, errors=0):
        style = wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_NONE
        super().__init__(parent=parent, id=-1, title="", style=style)

        self._parent_window = parent
        self._alpha = 255
        self._can_fade = False

        self.SetBackgroundColour(BORDER_COLOUR)

        outer = wx.Panel(self)
        outer.SetBackgroundColour(BORDER_COLOUR)

        card = wx.Panel(outer)
        card.SetBackgroundColour(CARD_BACKGROUND)

        has_errors = int(errors) > 0
        accent_colour = ERROR_TEXT if has_errors else SUCCESS

        accent = wx.Panel(card, size=(dip(card, 5), -1))
        accent.SetBackgroundColour(accent_colour)

        body = wx.Panel(card)
        body.SetBackgroundColour(CARD_BACKGROUND)

        icon = wx.StaticText(body, label="!" if has_errors else "✓")
        icon.SetForegroundColour(accent_colour)
        icon.SetBackgroundColour(CARD_BACKGROUND)
        icon_font = bold_font(icon, 18)
        icon.SetFont(icon_font)

        title = wx.StaticText(
            body,
            label="Download finished" if has_errors else "Download complete"
        )
        title.SetForegroundColour(NEUTRAL_TEXT)
        title.SetBackgroundColour(CARD_BACKGROUND)
        title.SetFont(bold_font(title, 11))

        saved_text = wx.StaticText(
            body,
            label=f"{int(saved)} {'image' if int(saved) == 1 else 'images'} saved"
        )
        saved_text.SetForegroundColour(NEUTRAL_TEXT)
        saved_text.SetBackgroundColour(CARD_BACKGROUND)

        ignored_value = int(ignored)
        errors_value = int(errors)
        detail_text = wx.StaticText(
            body,
            label=(
                f"{ignored_value} ignored  ·  "
                f"{errors_value} {'error' if errors_value == 1 else 'errors'}"
            )
        )
        detail_text.SetForegroundColour(
            ERROR_TEXT if has_errors else IGNORED_TEXT if ignored_value else NEUTRAL_TEXT
        )
        detail_text.SetBackgroundColour(CARD_BACKGROUND)

        text_column = wx.BoxSizer(wx.VERTICAL)
        text_column.Add(title, 0)
        text_column.Add(saved_text, 0, wx.TOP, dip(body, 3))
        text_column.Add(detail_text, 0, wx.TOP, dip(body, 2))

        body_layout = wx.BoxSizer(wx.HORIZONTAL)
        body_layout.Add(
            icon, 0,
            wx.ALIGN_TOP | wx.RIGHT,
            dip(body, 10)
        )
        body_layout.Add(text_column, 1, wx.EXPAND)
        body.SetSizer(body_layout)

        card_layout = wx.BoxSizer(wx.HORIZONTAL)
        card_layout.Add(accent, 0, wx.EXPAND)
        card_layout.Add(
            body, 1,
            wx.EXPAND | wx.ALL,
            dip(card, 13)
        )
        card.SetSizer(card_layout)

        border = dip(outer, 1)
        outer_layout = wx.BoxSizer(wx.VERTICAL)
        outer_layout.Add(card, 1, wx.EXPAND | wx.ALL, border)
        outer.SetSizer(outer_layout)

        frame_layout = wx.BoxSizer(wx.VERTICAL)
        frame_layout.Add(outer, 1, wx.EXPAND)
        self.SetSizer(frame_layout)

        self.SetMinClientSize((dip(self, 310), -1))
        self.Fit()
        self._position_to_parent()

        self._hold_timer = wx.Timer(self)
        self._fade_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_hold_finished, self._hold_timer)
        self.Bind(wx.EVT_TIMER, self._on_fade, self._fade_timer)
        self.Bind(wx.EVT_LEFT_UP, self._on_click)
        outer.Bind(wx.EVT_LEFT_UP, self._on_click)
        card.Bind(wx.EVT_LEFT_UP, self._on_click)
        body.Bind(wx.EVT_LEFT_UP, self._on_click)

        try:
            self._can_fade = bool(self.CanSetTransparent())
        except Exception:
            self._can_fade = False

        show_without_activating = getattr(self, "ShowWithoutActivating", None)
        if callable(show_without_activating):
            show_without_activating()
        else:
            self.Show()

        self._hold_timer.StartOnce(self.HOLD_MS)

    def _position_to_parent(self):
        width, height = self.GetSize()
        margin = dip(self, 14)

        try:
            parent_rect = self._parent_window.GetScreenRect()
            x = parent_rect.GetRight() - width - margin
            y = parent_rect.GetBottom() - height - margin

            display_index = wx.Display.GetFromWindow(self._parent_window)
            if display_index == wx.NOT_FOUND:
                display_index = 0
            area = wx.Display(display_index).GetClientArea()

            x = min(max(x, area.x + margin), area.GetRight() - width - margin)
            y = min(max(y, area.y + margin), area.GetBottom() - height - margin)
            self.SetPosition((x, y))
        except Exception:
            screen_width, screen_height = wx.GetDisplaySize()
            self.SetPosition((
                max(margin, screen_width - width - margin),
                max(margin, screen_height - height - margin),
            ))

    def _on_hold_finished(self, _event):
        if self._can_fade:
            self._fade_timer.Start(self.FADE_INTERVAL_MS)
        else:
            self.Close()

    def _on_fade(self, _event):
        self._alpha = max(0, self._alpha - self.FADE_STEP)
        if self._alpha <= 0:
            self._fade_timer.Stop()
            self.Close()
            return

        try:
            self.SetTransparent(self._alpha)
        except Exception:
            self._fade_timer.Stop()
            self.Close()

    def _on_click(self, _event):
        if self._hold_timer.IsRunning():
            self._hold_timer.Stop()
        if self._fade_timer.IsRunning():
            self._fade_timer.Stop()
        self.Close()
