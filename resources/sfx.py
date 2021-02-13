from wx.adv import Sound

class Sfx:

    notify = None

    @staticmethod
    def load():
        Sfx.notify = Sound()
        Sfx.notify.Create("notification.wav")
