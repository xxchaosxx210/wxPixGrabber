import os
import wx
from wx.adv import Sound

RESOURCE_PATH = f".{os.path.sep}resources"
IMAGE_PATH = os.path.join(RESOURCE_PATH, "images")
SOUND_PATH = os.path.join(RESOURCE_PATH, "sounds")

def load_wavs():
    wavfiles = os.listdir(SOUND_PATH)
    sounds = {}
    for wavfile in wavfiles:
        wavpath = os.path.join(SOUND_PATH, wavfile)
        name, ext = os.path.splitext(wavfile)
        sounds[name] = Sound(wavpath)
    return sounds

def load_bitmaps():
    pngfiles = os.listdir(IMAGE_PATH)
    bitmaps = {}
    for pngfile in pngfiles:
        full_bitmap_path = os.path.join(IMAGE_PATH, pngfile)
        name, ext = os.path.splitext(pngfile)
        bitmaps[name] = wx.Bitmap(full_bitmap_path, wx.BITMAP_TYPE_PNG)
    return bitmaps

if __name__ == '__main__':
    print(load_wavs())