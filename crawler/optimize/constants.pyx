cimport cython
from libc.stdlib cimport (
    malloc,
    free,
    srand,
    rand,
    realloc
)

from libc.time cimport (
    time_t,
    time
)

cdef class RandomIDGen:
    cdef int *ids
    cdef int length

    def __init__(self):
        cdef time_t t
        # seed the randomizer
        srand(<unsigned>time(&t))
        self.length = 0

    def has_id(self, id):
        for i in range(self.length):
            if self.ids[i] == id:
                return 1
        return 0
    
    def generate_id(self):
        while 1:
            r = rand()
            if self.has_id(r) == 0:
                self.add_id(r)
                break
        return r

    def add_id(self, i):
        if self.length == 0:
            self.ids = <int *>malloc(cython.sizeof(int))
        else:
            self.ids = <int *>realloc(self.ids, cython.sizeof(int) * (self.length+1))
        if self.ids == NULL:
            self.length = 0
            MemoryError("Unable to allocate more memory")
        self.ids[self.length] = i
        self.length += 1
    
    def complete(self):
        self.length = 0
        free(self.ids)

_rand = RandomIDGen()

THREAD_COMMANDER = _rand.generate_id()
THREAD_TASK = _rand.generate_id()
THREAD_MAIN = _rand.generate_id()
THREAD_SERVER = _rand.generate_id()

EVENT_FETCH = _rand.generate_id()
EVENT_COMPLETE = _rand.generate_id()
EVENT_SEARCHING = _rand.generate_id()
EVENT_FINISHED = _rand.generate_id()
EVENT_START = _rand.generate_id()
EVENT_QUIT = _rand.generate_id()
EVENT_CANCEL = _rand.generate_id()
EVENT_MESSAGE = _rand.generate_id()
EVENT_BLACKLIST = _rand.generate_id()
EVENT_SCANNING = _rand.generate_id()
EVENT_SERVER_READY = _rand.generate_id()
EVENT_UNKNOWN = _rand.generate_id()

EVENT_DOWNLOAD_IMAGE = _rand.generate_id()

STATUS_OK = _rand.generate_id()
STATUS_ERROR = _rand.generate_id()
STATUS_START = _rand.generate_id()
STATUS_IGNORED = _rand.generate_id()

# Free up memory
_rand.complete()

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