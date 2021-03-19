THREAD_COMMANDER = 1001
THREAD_TASK = 1002
THREAD_MAIN = 1003
THREAD_SERVER = 1004

EVENT_FETCH = 101
EVENT_COMPLETE = 102
EVENT_SEARCHING = 103
EVENT_FINISHED = 106
EVENT_START = 107
EVENT_QUIT = 108
EVENT_CANCEL = 109
EVENT_MESSAGE = 110
EVENT_BLACKLIST = 111
EVENT_SCANNING = 112
EVENT_SERVER_READY = 113

EVENT_DOWNLOAD_IMAGE = 114

STATUS_OK = 1
STATUS_ERROR = -1
STATUS_START = 12
STATUS_IGNORED = 13


class Message:

    def __init__(self, thread, event, status, _id, data):
        self.event = event
        self.thread = thread
        self.id = _id
        self.data = data
        self.status = status
