import wx

from gui.mainwindow import MainWindow

import logging
import os

import multiprocessing as mp
import threading
import queue

from resources.globals import (
    load_wavs,
    load_bitmaps
)

from crawler.commander import create_commander
import crawler.constants as const
from crawler.server import server_process
from crawler.options import setup as setup_options

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def OnInit(self):
        self._initialize_resources()
        setup_options()
        self.window = MainWindow(parent=None, id=-1,
                                 title="PixGrabber", size=(900, 600))
        self.SetTopWindow(self.window)
        self._initialize_threads()
        return super().OnInit()
    
    def _initialize_resources(self):
        self.bitmaps = load_bitmaps()
        self.sounds = load_wavs()

    def _initialize_threads(self):
        # Setup the message Queues amd start the background thread
        self.queue = mp.Queue()
        threading.Thread(target=self.commander_message_handler).start()
        self.commander = create_commander(self.queue)
        self.commander.thread.start()

        # start the server for handling our Web Browser extension requests
        self.server = mp.Process(target=server_process, kwargs={"host": "localhost", "port": 5000, "a_queue": self.queue})
        self.server.start()

    def commander_message_handler(self):
        """handles messages sent from the commander thread and task processes
        """
        quit = mp.Event()
        while not quit.is_set():
            try:
                msg = self.queue.get()
                if msg.thread == const.THREAD_COMMANDER and msg.event == const.EVENT_QUIT:
                        self.server.terminate()
                        quit.set()
                elif msg.thread == const.THREAD_SERVER and msg.event == const.EVENT_SERVER_READY:
                    self.commander.queue.put_nowait(msg)
                else:
                    # Pass the message to the GUI Thread
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