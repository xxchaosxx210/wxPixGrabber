from wx.adv import Sound
from dataclasses import dataclass

@dataclass
class Sfx:
    notify: Sound = None
    clipboard: Sound = None
    error: Sound = None
    complete: Sound = None

def load_sounds():
    sfx = Sfx()
    sfx.complete = Sound(".\\resources\\sounds\\notification.wav")
    sfx.clipboard = Sound(".\\resources\\sounds\\clipboard.wav")
    sfx.error = Sound(".\\resources\\sounds\\error.wav")
    return sfx
