import threading
import multiprocessing as mp
import queue
import functools
import os
from io import BytesIO
from dataclasses import dataclass
from collections import namedtuple
import logging

from web.webrequest import (
    request_from_url,
    load_cookies
)
import web.options as options
import web.parsing as parsing
import web.cache as cache

# Image
from PIL import (
    Image,
    UnidentifiedImageError
)

_Log = logging.getLogger(__name__)


class Blacklist:

    """
    thread safe container class for storing global links
    this is to check there arent duplicate links
    saves a lot of time and less scraping
    """

    def __init__(self):
        self.items = []

    def clear(self):
        self.items.clear()
    
    def add(self, item):
        self.items.append(item.__dict__)
    
    def exists(self, item):
        try:
            index = self.items.index(item.__dict__)
        except ValueError:
            index = -1
        return index >= 0


@dataclass
class Message:
    """
    for message handling sending to and from threads
    thread - thread name
    type   - the type of message
    id     - the thread index
    status - the types status
    data   - extra data. Depends on message type
    """
    type: str
    thread: str
    id: int = 0
    status: str = ""
    data: dict = None


@dataclass
class Stats:
    saved: int = 0
    errors: int = 0
    ignored: int = 0
    

def create_commander(callback, msgbox):
    """
    create the main handler thread.
    this thread will stay iterating for the
    remainder of the programs life cycle
    msgbox is a queue.Queue() object
    """
    return threading.Thread(target=commander_thread, 
                            kwargs={"callback": callback, "msgbox": msgbox})

def create_save_path(settings):
    """
    create_save_path(object)
    Settings object load from file
    append the unique folder path if required
    create the directory if not exists
    """
    if not os.path.exists(settings["save_path"]):
        try:
            os.mkdir(settings["save_path"])
        except FileExistsError:
            pass
    if settings["unique_pathname"]["enabled"]:
        path = os.path.join(settings["save_path"], settings["unique_pathname"]["name"])
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except FileExistsError:
                pass
    else:
        path = settings["save_path"]
    return path

def stream_to_file(path, bytes_stream):
    with open(path, "wb") as fp:
        fp.write(bytes_stream.getbuffer())
        fp.close()
        return True
    return False

def _response_to_stream(response):
    # read from requests object
    # store in memory
    byte_stream = BytesIO()
    for buff in response.iter_content(1000):
        byte_stream.write(buff)
    return byte_stream

def _download_image(filename, response, settings):
    """
    download_image(str, str, object, object)

    path should be the file path, filename should be the name of the file
    os.path.join is used to append path to filename
    response is the response returned from requests.get
    """
    stats = Stats()
    byte_stream = _response_to_stream(response)
    # check the image size is within our bounds
    minsize = settings["minimum_image_resolution"]
    image = Image.open(byte_stream)
    width, height = image.size
    if width > minsize["width"] and height > minsize["height"]:
        # create a new save path and write image to file
        path = create_save_path(settings)
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            _Log.info(f"{full_path} already exists...")
            # if file exists then check user settings on what to do
            if settings["file_exists"] == "rename":
                full_path = options.rename_file(full_path)
                _Log.info(f"Renaming to {full_path}")
            elif settings["file_exists"] == "skip":
                # close the stream and dont write to disk
                _Log.info(f"Skipping {full_path}")
                stats.ignored += 1
                byte_stream.close()
                return stats
        # everything ok. write image to disk
        if stream_to_file(full_path, byte_stream):
            stats.saved += 1
        else:
            stats.errors += 1
    else:
        # add the URl to the cache
        if not cache.query_ignore(response.url):
            cache.add_ignore(response.url, "small-image", width, height)
        stats.ignored += 1

    # close the file handle
    byte_stream.close()
    
    return stats


class Grunt(mp.Process):

    """
    Worker thread which will search for images on the url passed into __init__
    """

    def __init__(self, task_index, urldata, 
                 settings, filters, commander_msg, 
                 cancel_event):
        """
        __init__(int, str, **kwargs)
        task_index should be a unique number
        this can be used to create a unique filename
        and can also identify the thread
        first thread will be 0 and indexed that way
        url is the universal resource locator to search and parse
        """
        super().__init__()
        self.task_index = task_index
        # grunts starting url
        self.urldata = urldata
        self.settings = settings
        self.fileindex = 0
        self.filters = filters
        # Commander process message box
        self.comm_queue = commander_msg
        # Grunts message box
        self.msgbox = mp.Queue()
        self.cancel = cancel_event
    
    def search_response(self, response, include_forms):
        """
        if html parse look for image sources
        if image then save
        """
        # intialize the list containing UrlData objects
        datalist = []
        # check the file extension
        ext = parsing.is_valid_content_type(
            response.url,
            response.headers.get("Content-Type", ""),
            self.settings["images_to_search"]
        )
        if parsing.html_ext == ext:
            # if html document then parse the text
            soup = parsing.parse_html(response.text)
            # search for links in soup
            parsing.sort_soup(url=response.url,
                              soup=soup,
                              urls=datalist, 
                              include_forms=include_forms, 
                              images_only=True, 
                              thumbnails_only=False,
                              filters=self.filters)
        elif ext in parsing.IMAGE_EXTS:
            if self.settings["generate_filenames"]["enabled"]:
                # if so then append thread index and fileindex to make a unique identifier
                fileindex = f"{self.task_index}_{self.fileindex}{ext}"
                # increment the fileindex for the next image found
                self.fileindex += 1
                # append the saved unique name to our file path
                filename = f'{self.settings["generate_filenames"]["name"]}{fileindex}'
            else:
                # generate filename from url
                filename = options.url_to_filename(response.url, ext)
            # check the validity of the image and save
            try:
                stats = _download_image(filename, response, self.settings)
                self.comm_queue.put_nowait(
                    Message(
                        thread="grunt", type="stat-update", data={
                            "saved": stats.saved,
                            "errors": stats.errors,
                            "ignored": stats.ignored}))
            except UnidentifiedImageError:
                # Couldnt load the Image from Stream
                self.comm_queue.put_nowait(Message(
                                   thread="grunt", type="stat-update", 
                                   data={"saved": 0, "errors": 1, "ignored": 0}))
            return []
        else:
            if not cache.query_ignore(response.url):
                _Log.info(f"PROCESS#{self.task_index} - Url {response.url} ignored. Storing to cache")
                cache.add_ignore(response.url, "unknown-file-type", 0, 0)
        return datalist
    
    def add_url(self, urldata):
        """
        Query the Parent Process if this url dict exists
        if not then Parent Process will add it to its blacklist
        returns True if no entry found
        """
        self.comm_queue.put(Message(
            thread="grunt",
            type="blacklist",
            data={"index": self.task_index, "urldata": urldata}
        ))
        reply = self.msgbox.get()
        return reply.status
    
    def follow_url(self, urldata):
        """
        follow_url(object, object)
        request url and parse the response
        """
        try:
            resp = request_from_url(urldata, self.cookiejar, self.settings)
            urllist = self.search_response(resp, self.settings["form_search"]["enabled"])
        except Exception as err:
            _Log.error(f"PROCESS#{self.task_index} - {err.__str__()}")
            self.comm_queue.put_nowait(
                    Message(thread="grunt", type="stat-update", 
                            data={"saved": 0, "errors": 1, "ignored": 0}))  
            return []
        resp.close()
        return urllist

    def run(self):
        if not self.cancel.is_set():
            self.cookiejar = load_cookies(self.settings)
            self.comm_queue.put_nowait(
                Message(thread="grunt", id=self.task_index, status="ok", type="scanning"))
            # Three Levels of looping each level parses
            # finds new links to images. Saves images to file
            if self.add_url(self.urldata):
                ## Level 1
                level_one_urls = self.follow_url(self.urldata)
                for level_one_urldata in level_one_urls:
                    if self.add_url(level_one_urldata):
                        # Level 2
                        level_two_urls = self.follow_url(level_one_urldata)
                        for level_two_urldata in level_two_urls:
                            if self.add_url(level_two_urldata):
                                # Level 3
                                self.follow_url(level_two_urldata)

        if self.cancel.is_set():
            self.notify_finished("cancelled")
        else:
            self.notify_finished("complete")
    
    def notify_finished(self, status):
        self.comm_queue.put_nowait(Message(
                thread="grunt", status=status, type="finished", id=self.task_index))


def _start_max_threads(threads, max_threads, counter):
    for th in threads:
        if counter >= max_threads:
            break
        else:
            th.start()
            counter += 1
    return counter

def _add_stats(stats, data):
    stats.saved += data["saved"]
    stats.errors += data["errors"]
    stats.ignored += data["ignored"]
    return stats

def commander_thread(callback, msgbox):
    """
    commander_thread(function, object)

    function callback to main thread, msgbox is a Queue() FIFO object handed
    down from main thread

    callback(msg)
    msg is a Message object
        thread - str calling thread or process can be either main, commander or grunt
        type   - quit, start, fetch, cancel, message
        status - depended on the type
        data   - dict containing extra data depending on the type of message

        example to quit commander: msg = Message(thread="main", type="quit") 
                                  commander_queue.put(msg)
    """
    # Create the cache table
    cache.initialize_ignore()
    callback(Message(
        thread="commander", 
        type="message", 
        data={"message": "Commander thread has loaded. Waiting to scan"}))
    MessageMain = functools.partial(Message, thread="commander", type="message")

    @dataclass
    class Properties:
        settings: dict
        scanned_urls: list
        counter: int = 0
        blacklist: Blacklist = None
        cancel_all: mp.Event = None
        task_running: bool = False
        processes: list = None
        quit_thread: mp.Event = None
        time_counter: float = 0.0
    
    props = Properties(settings={}, scanned_urls=[], blacklist=Blacklist(), cancel_all=mp.Event(),
                       processes=[], quit_thread=mp.Event())
    
    QUEUE_TIMEOUT = 0.1

    while not props.quit_thread.is_set():
        try:
            if props.task_running:
                r = msgbox.get(timeout=QUEUE_TIMEOUT)
            else:
                r = msgbox.get(timeout=None)
            if r.thread == "main":
                if r.type == "quit":
                    props.cancel_all.set()
                    callback(Message(thread="commander", type="quit"))
                    props.quit_thread.set()
                elif r.type == "start":
                    if not props.task_running:
                        props.processes = []
                        props.task_running = True
                        stats = Stats()
                        props.blacklist.clear()
                        # load the settings from file
                        # create a new instance of it in memory
                        # we dont want these values to change
                        # whilst downloading and saving to file
                        props.settings = dict(options.load_settings())
                        cookiejar = load_cookies(props.settings)
                        # notify main thread so can intialize UI
                        callback(MessageMain(type="searching", status="start"))
                        filters = parsing.compile_filter_list(props.settings["filters"])
                        _Log.info("Search Filters loaded")
                        for task_index, urldata in enumerate(props.scanned_urls):
                            grunt = Grunt(task_index, urldata, props.settings, 
                                          filters, msgbox, props.cancel_all)
                            props.processes.append(grunt)
                        
                        _Log.info(f"Processes loaded - {len(props.processes)} processes")
                            
                        # reset the threads counter this is used to keep track of
                        # threads that have been  started once a running thread has been notified
                        # this thread counter is incremenetet counter is checked with length of props.processes
                        # once the counter has reached length then then all threads have been complete
                        props.counter = 0
                        max_connections = round(int(props.settings["max_connections"]))
                        props.counter = _start_max_threads(props.processes, max_connections, props.counter)

                        _Log.info(
                            f"""Process Counter set to 0. Max Connections = \
                                {max_connections}. Current running Processes = {len(tasks_alive(props.processes))}""")

                elif r.type == "fetch":                
                    if not props.task_running:
                        props.cancel_all.clear()
                        # Load settings
                        callback(Message(thread="commander", type="fetch", status="started"))
                        # Load the settings
                        props.settings = options.load_settings()
                        # get the document from the URL
                        callback(MessageMain(data={"message": f"Connecting to {r.data['url']}"}))
                        # Load the cookiejar
                        cookiejar = load_cookies(props.settings)
                        urldata = parsing.UrlData(r.data["url"], method="GET")
                        try:
                            webreq = request_from_url(urldata, cookiejar, props.settings)
                            # make sure is a text document to parse
                            ext = parsing.is_valid_content_type(
                                                                r.data["url"], 
                                                                webreq.headers["Content-type"], 
                                                                props.settings["images_to_search"])
                            if ext == ".html":
                                html_doc = webreq.text
                                # parse the html
                                soup = parsing.parse_html(html_doc)
                                # get the url title
                                # amd add a unique path name to the save path
                                options.assign_unique_name(
                                    webreq.url, getattr(soup.find("title"), "text", ""))
                                # scrape links and images from document
                                props.scanned_urls = []
                                # find images and links
                                # set the include_form to False on level 1 scan
                                # compile our filter matches only add those from the filter list
                                filters = parsing.compile_filter_list(props.settings["filters"])
                                if parsing.sort_soup(url=r.data["url"],
                                                     soup=soup, 
                                                     urls=props.scanned_urls,
                                                     include_forms=False,
                                                     images_only=False, 
                                                     thumbnails_only=True,
                                                     filters=filters) > 0:
                                    callback(
                                        Message(thread="commander", type="fetch", 
                                                     status="finished", data={"urls": props.scanned_urls}))
                                else:
                                    # Nothing found notify main thread
                                    callback(MessageMain(data={"message": "No links found :("}))
                            webreq.close()
                        except Exception as err:
                            _Log.error(f"Commander web request failed - {err.__str__()}")
                    else:
                        callback(MessageMain(
                            data={"message": "Still scanning for images please press cancel to start a new scan"}))

                elif r.type == "cancel":
                    props.cancel_all.set()

            elif r.thread == "grunt":
                if r.type == "finished":
                    # one grunt is gone start another
                    if props.counter < len(props.processes):
                        if not props.cancel_all.is_set():
                            props.processes[props.counter].start()
                        else:
                            props.processes[props.counter].run()
                        props.counter += 1
                        _Log.info(f"PROCESS#{r.id} is {r.status}")
                        if r.status == "complete":
                            callback(r)
                elif r.type == "stat-update":
                    # add stats up and notify main thread
                    _add_stats(stats, r.data)
                    callback(Message(thread="commander", 
                                     type="stat-update", data={"stats": stats}))
                elif r.type == "blacklist":
                    # check the props.blacklist with urldata and notify Grunt process
                    # if no duplicate and added then True returned
                    process_index = r.data["index"]
                    grunt = props.processes[process_index]
                    if not props.blacklist.exists(r.data["urldata"]):
                        props.blacklist.add(r.data["urldata"])
                        blacklist_added = True
                    else:
                        blacklist_added = False
                    grunt.msgbox.put(Message(
                        thread="commander", type="blacklist",
                        status=blacklist_added
                    ))
                else:
                    # something pass onto main thread
                    callback(r)
                    
            elif r.thread == "settings":
                callback(MessageMain(data=r.data))

        except queue.Empty:
            pass

        finally:
            if props.task_running:
                # check if all props.processes are finished
                # and that the grunt props.counter is greater or
                # equal to the size of grunt threads 
                # if so cleanup
                # and notify main thread
                if len(tasks_alive(props.processes)) == 0 and props.counter >= len(props.processes):
                    callback(Message(thread="commander", type="complete"))
                    _reset_comm_props(props)
                else:
                    # cancel flag is set. Start counting to timeout
                    # then start terminating processing
                    if props.cancel_all.is_set():
                        if props.time_counter >= props.settings["connection_timeout"]:
                            # kill any hanging processes
                            for task in props.processes:
                                if task.is_alive():
                                    task.terminate()
                                    props.counter += 1
                        else:
                            props.time_counter += QUEUE_TIMEOUT

def _reset_comm_props(properties):
    properties.cancel_all.clear()
    properties.processes = []
    properties.task_running = False
    properties.blacklist.clear()
    properties.time_counter = 0.0

def tasks_alive(processes):
    """
    returns a list of task processes that are still alive
    """
    return list(filter(lambda grunt : grunt.is_alive(), processes))