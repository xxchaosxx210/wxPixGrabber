import threading
import queue
import wx

class ClipboardListener(threading.Thread):

    msgbox = queue.Queue()

    def __init__(self, callback):
        super().__init__(daemon=True)
        self.callback = callback

    def run(self):
        quit = threading.Event()
        previous_text = ""
        while not quit.is_set():
            try:
                msg = ClipboardListener.msgbox.get(timeout=1)
                if msg["type"] == "quit":
                    quit.set()
            except queue.Empty:
                do = wx.TextDataObject()
                if wx.TheClipboard.Open():
                    success = wx.TheClipboard.GetData(do)
                    wx.TheClipboard.Close()
                    if success:
                        if previous_text != do.GetText():
                            previous_text = do.GetText()
                            print(do.GetText())

def notify_clipboard_listener(msg):
    ClipboardListener.msgbox.put_nowait(msg)

if __name__ == '__main__':
    import wx
    app = wx.App()
    frame = wx.Frame(None, -1, "Clipboard Example", size=(500, 500))
    frame.Show()
    clip = ClipboardListener(lambda x: x)
    clip.start()
    app.MainLoop()
