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
    cpdef public object type
    cpdef public object thread
    cdef public int id
    cpdef public object data

    def __init__(self, type, thread, id, data):
        self.type = type
        self.thread = thread
        self.id = id
        self.data = data

cdef class CStats:
    cdef public int saved
    cdef public int errors
    cdef public ignored

    def __init__(self):
        self.saved = 0
        self.errors = 0
        self.ignored = 0