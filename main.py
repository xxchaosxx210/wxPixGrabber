import wx

from gui.mainwindow import MainWindow

import logging
import os

import clipboard

import multiprocessing as mp
import threading
import queue

from resources.globals import (
    load_wavs,
    load_bitmaps
)

from crawler.commander import create_commander
import crawler.constants as const

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def OnInit(self):
        self._initialize_resources()
        self.window = MainWindow(parent=None, id=-1,
                                 title="PixGrabber", size=(900, 600))
        self.SetTopWindow(self.window)
        self._initialize_threads()
        return super().OnInit()
    
    def _initialize_resources(self):
        self.bitmaps = load_bitmaps()
        self.sounds = load_wavs()

    def _initialize_threads(self):
        self.queue = mp.Queue()
        threading.Thread(target=self.commander_message_handler).start()
        self.commander = create_commander(self.queue)
        self.commander.thread.start()

        # keep a reference to the clipboard, there is a bug in that when the clipboard
        # listener is running, it captures win32 messages before they get to the wx event loop
        # for some reason messages are not being passed onto Dialog windows
        # so Dialogs are unresponsive so I patched it by closing the clipboard listener
        # when a Dialog is open. This leads to a bug when I start the listener again it
        # recaptures the last text on the clipboard. I found the best way around this is
        # to send an empty string to the clipboard
        self.clipboard = \
            clipboard.ClipboardListener(parent=self.window, 
                                        callback=self.window.on_clipboard, 
                                        url_only=True)
        self.clipboard.start()

        # this will be our server process
        self.server = None
     
    def commander_message_handler(self):
        quit = mp.Event()
        while not quit.is_set():
            try:
                msg = self.queue.get()
                if msg.thread == const.THREAD_COMMANDER and msg.event == const.EVENT_QUIT: 
                        quit.set()
                else:
                    # pass the message to the callback
                    wx.CallAfter(self.window.message_from_thread, msg)
            except queue.Empty:
                pass

def _main():
    # pyinstaller requires this. Otherwise multiple windows are spawned
    mp.freeze_support()
    app = PixGrabberApp()
    app.window.Show()
    app.MainLoop()

if __name__ == '__main__':
    _main()