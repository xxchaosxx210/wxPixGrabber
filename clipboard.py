import wx
import os
import re

if os.name == "nt":
    from win32 import (
        win32api,
        win32gui,
        win32clipboard
    )
    import win32.lib.win32con as win32con

# Http and Https pattern
URL_PATTERN = re.compile(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)')


class ClipboardListener:

    def __init__(self, parent, callback, url_only=False):
        """
        __init__(object, function, bool)
        takes in a wx window normally a frame. callback is a function
        to which to recieve text changes from the clipboard
        url_only set to True then callback will only recieve url links
        found in the text from the clipboard.
        """
        self.hwnd = parent.GetHandle()
        self._first = True
        self.callback = callback
        self._next_hwnd = None
        self._url_only = url_only
        if os.name == "nt":
            self.oldwndproc = \
                win32gui.SetWindowLong(self.hwnd, 
                                       win32con.GWL_WNDPROC, 
                                       self.wndproc)
        self._next_hwnd = win32clipboard.SetClipboardViewer(self.hwnd)
    
    def wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            if self._next_hwnd:
                win32clipboard.ChangeClipboardChain(
                    self.hwnd, self._next_hwnd)
            else:
                win32clipboard.ChangeClipboardChain(
                    self.hwnd, 0)
            win32api.SetWindowLong(self.hwnd, 
                                   win32con.GWL_WNDPROC, 
                                   self.oldwndproc)

        elif msg == win32con.WM_CHANGECBCHAIN:
            # is it our window?
            if self._next_hwnd == wparam:
                # repair the chain
                self._next_hwnd = lparam
            if self._next_hwnd:
                # if another viewer in chain pass it on
                win32api.SendMessage(
                    self._next_hwnd, msg, wparam, lparam)

        elif msg == win32con.WM_DRAWCLIPBOARD:
            self._process_clipboard()
            if self._next_hwnd:
                win32api.SendMessage(hwnd, msg, wparam, lparam)

        win32gui.CallWindowProc(self.oldwndproc, hwnd, msg, wparam, lparam)
    
    def _getclipboardtext(self):
        text = ""
        c = wx.Clipboard()
        if c.Open():
            if c.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                data = wx.TextDataObject()
                c.GetData(data)
                text = data.GetText()
                c.Close()
        return text
    
    def _process_clipboard(self):
        # first link in the clipboard chain?
        if self._first:
            self._first = False
        else:
            text = self._getclipboardtext()
            if text:
                if self._url_only:
                    result = URL_PATTERN.search(text)
                    if result:
                        self.callback(result.group())
                else:
                    return text