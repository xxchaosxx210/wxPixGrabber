import os
import wx
from wx.adv import Sound

RESOURCE_PATH = f".{os.path.sep}resources"
IMAGE_PATH = os.path.join(RESOURCE_PATH, "images")
SOUND_PATH = os.path.join(RESOURCE_PATH, "sounds")


def load_wavs():
    sounds = {}
    with os.scandir(SOUND_PATH) as it:
        for entry in it:
            if entry.name.endswith(".wav") and entry.is_file():
                name, ext = os.path.splitext(entry.name)
                sounds[name] = Sound(entry.path)
    return sounds

def load_bitmaps():
    bitmaps = {}
    with os.scandir(IMAGE_PATH) as it:
        for entry in it:
            if entry.name.endswith(".png") and entry.is_file():
                name, ext = os.path.splitext(entry.name)
                bitmaps[name] = wx.Bitmap(entry.path, wx.BITMAP_TYPE_PNG)
    return bitmaps

if __name__ == '__main__':
    print(load_wavs())