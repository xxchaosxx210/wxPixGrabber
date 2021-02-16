from wx.adv import Sound
from dataclasses import dataclass

@dataclass
class Sfx:
    notify: Sound = None
    clipboard: Sound = None

def load_sounds():
    sfx = Sfx()
    sfx.notify = Sound(".\\resources\\notification.wav")
    sfx.clipboard = Sound(".\\resources\\clipboard.wav")
    sfx.complete = Sound(".\\resources\\complete.wav")
    return sfx
