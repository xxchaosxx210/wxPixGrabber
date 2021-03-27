"""
Description: Messaging system between Processes and Threads
"""
from dataclasses import dataclass

# thread ID
THREAD_COMMANDER = 1001
THREAD_TASK = 1002
THREAD_MAIN = 1003
THREAD_SERVER = 1004

# Event ID
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
EVENT_PAUSE = 115

# Status ID
STATUS_OK = 1
STATUS_ERROR = -1
STATUS_START = 12
STATUS_IGNORED = 13


@dataclass
class Message:

    thread: int
    event: int
    status: int = STATUS_OK
    id: int = 0
    data: dict = None
