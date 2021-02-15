import wx

from gui.mainwindow import MainWindow

import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


class PixGrabberApp(wx.App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def _main():
    app = PixGrabberApp()
    window = MainWindow(
        parent=None,
        id=-1,
        title="PixGrabber", 
        size=(900, 600))
    window.Show()
    app.MainLoop()

if __name__ == '__main__':
    _main()