THREAD_COMMANDER = 1001
THREAD_TASK = 1002
THREAD_MAIN = 1003

EVENT_FETCH = 101
EVENT_COMPLETE = 102
EVENT_SEARCHING = 103
EVENT_STAT_UPDATE = 104
EVENT_IMAGE = 105
EVENT_FINISHED = 106
EVENT_START = 107
EVENT_QUIT = 108
EVENT_CANCEL = 109
EVENT_MESSAGE = 110
EVENT_BLACKLIST = 111
EVENT_SCANNING = 112

STATUS_OK = 1
STATUS_ERROR = -1
STATUS_START = 12


cdef class CommanderProperties:
    cpdef public object settings
    cpdef public object scanned_urls
    cdef public int counter
    cpdef public object blacklist
    cpdef public object cancel_all
    cdef public int task_running
    cpdef public object tasks
    cpdef public object quit_thread
    cdef public double time_counter

    def __init__(self, settings=None, scanned_urls=[], blacklist=None, counter=0, cancel_all=None,
                 task_running=0, tasks=[], quit_thread=None, time_counter=0.0):
        self.settings = settings
        self.scanned_urls = scanned_urls
        self.blacklist = blacklist
        self.counter = counter
        self.cancel_all = cancel_all
        self.task_running = task_running
        self.tasks = tasks
        self.quit_thread = quit_thread
        self.time_counter = time_counter


cdef class CUrlData:
    cpdef public object url
    cpdef public object method
    cpdef public object action
    cpdef public object data
    cpdef public object tag

    def __init__(self, url, method, action, data, tag):
        self.url = url
        self.method = method
        self.action = action
        self.data = data
        self.tag = tag


cdef class CMessage:
    cdef public int event
    cdef public int thread
    cdef public int id
    cdef public int status
    cpdef public object data

    def __init__(self, thread, event, status, id, data):
        self.event = event
        self.thread = thread
        self.id = id
        self.data = data
        self.status = status


cdef class CStats:
    cdef public int saved
    cdef public int errors
    cdef public ignored

    def __init__(self):
        self.saved = 0
        self.errors = 0
        self.ignored = 0