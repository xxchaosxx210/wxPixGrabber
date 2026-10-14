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

from crawler.commander import Commander
import crawler.message as const
from crawler.server import server_process
from crawler.options import setup as setup_options

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        self.window = None
        super().__init__(**kwargs)

    def OnInit(self):
        self._initialize_resources()
        setup_options()
        self.window = MainWindow(parent=None, id=-1, title="PixGrabber")
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
        self.commander = Commander(self.queue)
        self.commander.start()

        # Start the local helper/test server. Port 5000 is kept fixed for
        # compatibility with the browser extension /set-html endpoint.
        self.server = mp.Process(
            target=server_process,
            kwargs={"host": "localhost", "port": 5000, "a_queue": self.queue}
        )
        self.server.start()

    def commander_message_handler(self):
        """handles messages sent from the commander thread and task processes
        """
        _quit = mp.Event()
        pending_results = []

        def flush_results():
            if pending_results:
                batch = pending_results[:]
                pending_results.clear()
                wx.CallAfter(self.window.message_batch_from_thread, batch)

        while not _quit.is_set():
            try:
                msg = self.queue.get(timeout=0.05)
                if (msg.thread == const.THREAD_TASK
                        and msg.event == const.EVENT_DOWNLOAD_IMAGE):
                    pending_results.append(msg)
                    if len(pending_results) >= 64:
                        flush_results()
                    continue

                # Keep result rows ahead of later status or completion events.
                flush_results()
                if msg.thread == const.THREAD_COMMANDER and msg.event == const.EVENT_QUIT:
                    if self.server is not None and self.server.is_alive():
                        self.server.terminate()
                    _quit.set()
                elif msg.thread == const.THREAD_SERVER and msg.event == const.EVENT_SERVER_READY:
                    self.commander.queue.put_nowait(msg)
                else:
                    # Pass the message to the GUI Thread
                    wx.CallAfter(self.window.message_from_thread, msg)
            except queue.Empty:
                flush_results()


def _main():
    # pyinstaller requires this. Otherwise multiple windows are spawned
    mp.freeze_support()
    app = PixGrabberApp()
    app.window.Show()
    app.MainLoop()


if __name__ == '__main__':
    _main()
