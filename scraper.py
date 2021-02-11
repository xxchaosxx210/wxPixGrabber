import threading
import queue
import functools
import os
from io import BytesIO
from dataclasses import dataclass

from webrequest import (
    request_from_url,
    load_cookies
)

# Image
from PIL import (
    Image,
    UnidentifiedImageError
)

from global_props import Settings

import parsing

from cache import Sql

# Initialize the ignore table in the db file
Sql.initialize_ignore()

class Blacklist:

    """
    thread safe container class for storing global links
    this is to check there arent duplicate links
    saves a lot of time and less scraping
    """

    links = []
    lock = threading.Lock()

    @staticmethod
    def clear():
        Blacklist.lock.acquire()
        Blacklist.links.clear()
        Blacklist.lock.release()
    
    @staticmethod
    def add(item):
        Blacklist.lock.acquire()
        Blacklist.links.append(item.__dict__)
        Blacklist.lock.release()
    
    @staticmethod
    def exists(item):
        Blacklist.lock.acquire()
        try:
            index = Blacklist.links.index(item.__dict__)
        except ValueError:
            index = -1
        Blacklist.lock.release()
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


class Stats:

    saved = 0
    errors = 0
    ignored = 0

    @staticmethod
    def reset():
        Stats.saved = 0
        Stats.errors = 0
        Stats.ignored = 0


class Threads:

    """
    static class holding global scope variables
    """
    # commander thread reference
    commander = None
    # global list for containing runnning threads
    grunts = []
    # commander thread messaging queue
    commander_queue = queue.Queue()
    # global semaphore. this is related to max_connections
    # found in the settings file
    semaphore = threading.Semaphore(10)
    # global event to cancel current running task
    cancel = threading.Event()

    # Global cookie jar
    cookie_jar = None


def create_commander(callback):
    """
    create the main handler thread.
    this thread will stay iterating for the
    remainder of the programs life cycle
    """
    Threads.commander = threading.Thread(
        target=commander_thread, kwargs={"callback": callback})
    return Threads.commander

def create_save_path(settings):
    """
    create_save_path(object)
    Settings object load from file
    append the unique folder path if required
    create the directory if not exists
    """
    parsing.Globals.new_folder_lock.acquire()
    if not os.path.exists(settings["save_path"]):
        os.mkdir(settings["save_path"])
    if settings["unique_pathname"]["enabled"]:
        path = os.path.join(settings["save_path"], settings["unique_pathname"]["name"])
        if not os.path.exists(path):
            os.mkdir(path)
    else:
        path = settings["save_path"]
    parsing.Globals.new_folder_lock.release()
    return path

def stream_to_file(path, filename, bytes_stream):
    full_path = os.path.join(path, filename)
    with open(full_path, "wb") as fp:
        fp.write(bytes_stream.getbuffer())
        fp.close()
        # Update the images saved stats counter
        Stats.saved += 1

def download_image(filename, response, settings):
    """
    download_image(str, str, object)

    path should be the file path, filename should be the name of the file
    os.path.join is used to append path to filename
    response is the response returned from requests.get
    """
    # read from socket
    # store in memory
    # images shouldnt be too large
    byte_stream = BytesIO()
    for buff in response.iter_content(1000):
        byte_stream.write(buff)
    # load image from buffer io
    try:
        image = Image.open(byte_stream)
    except UnidentifiedImageError as err:
        print(f"[IMAGE_ERROR]: {err.__str__()}, {response.url}")
        Stats.errors += 1
        notify_commander(Message(thread="grunt", type="stat", status="error", data={"value": Stats.errors}))
        return
    width, height = image.size
    # if image requirements met then save
    if width > 200 and height > 200:
        # create a new save path and write image toi file
        path = create_save_path(settings)
        stream_to_file(path, filename, byte_stream)
        notify_commander(Message(
            thread="grunt", 
            type="image", 
            status="ok", 
            data={"pathname": filename, "url": response.url, "images_saved": Stats.saved}))
    else:
        # add the URl to the cache
        if not Sql.query_ignore(response.url):
            Sql.add_ignore(response.url, "small-image", width, height)

    # close the file handles
    byte_stream.close()
    image.close()
    

class Grunt(threading.Thread):

    """
    Worker thread which will search for images on the url passed into __init__
    """

    def __init__(self, thread_index, urldata, settings, **kwargs):
        """
        __init__(int, str, **kwargs)
        thread_index should be a unique number
        this can be used to create a unique filename
        and can also identify the thread
        first thread will be 0 and indexed that way
        url is the universal resource locator to search and parse
        """
        super().__init__(**kwargs)
        self.thread_index = thread_index
        self.urldata = urldata
        self.settings = settings
        self.fileindex = 0
    
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
            parsing.sort_soup(response.url,
                              soup,
                              datalist, 
                              include_forms=include_forms, 
                              images_only=True, 
                              thumbnails_only=False)
        elif ext in parsing.IMAGE_EXTS:
            # check if unique filename has been set in settings
            if self.settings["generate_filenames"]["enabled"]:
                # if so then append thread index and fileindex
                # to make a unique identifier
                fileindex = f"{self.thread_index}_{self.fileindex}{ext}"
                # increment the fileindex for the next image found
                self.fileindex += 1
                # append the saved unique name to our file path
                filename = f'{self.settings["generate_filenames"]["name"]}{fileindex}'
            else:
                # if not parse split the url and append the filename
                # found from the url and use that instead
                filename = f"test{self.thread_index}{ext}"
            # check the validity of the image and save
            download_image(filename, response, self.settings)
            return []
        else:
            # ingored counter goes up
            Stats.ignored += 1
            notify_commander(Message(thread="grunt", type="stat", status="ignored", data={"value": Stats.errors}))
            if not Sql.query_ignore(response.url):
                Sql.add_ignore(response.url, "unknown-file-type", 0, 0)
        return datalist
    
    def run(self):
        # partial function to avoid repetitive typing
        GruntMessage = functools.partial(Message, id=self.thread_index, thread="grunt")
        if not Threads.cancel.is_set():
            notify_commander(GruntMessage(status="ok", type="scanning"))
            # Three Levels of Searching

            if not Blacklist.exists(self.urldata):
                Blacklist.add(self.urldata)
                ## Level 1
                level_one_response = request_from_url(self.urldata, Threads.cookie_jar, self.settings)
                if level_one_response:
                    level_one_list = self.search_response(level_one_response, self.settings["form_search"]["enabled"])
                    for level_one_urldata in level_one_list:
                        if not Blacklist.exists(level_one_urldata):
                            Blacklist.add(level_one_urldata)
                            # Level 2
                            level_two_response = request_from_url(level_one_urldata, Threads.cookie_jar, self.settings)
                            if level_two_response:
                                level_two_list = self.search_response(level_two_response, self.settings["form_search"]["enabled"])
                                for level_two_urldata in level_two_list:
                                    if not Blacklist.exists(level_two_urldata):
                                        Blacklist.add(level_two_urldata)
                                        # Level 3
                                        level_three_response = request_from_url(level_two_urldata, Threads.cookie_jar, self.settings)
                                        if level_three_response:
                                            self.search_response(level_three_response, self.settings["form_search"]["enabled"])
                                            
                                            level_three_response.close()
                                level_two_response.close()
                    level_one_response.close()

        if Threads.cancel.is_set():
            notify_commander(GruntMessage(status="cancelled", type="finished"))
        else:
            notify_commander(GruntMessage(status="complete", type="finished"))


def commander_thread(callback):
    """
    main handler thread takes in filepath or url
    and then passes onto captain_thread for parsing

    Level 1 parser and image finder thread
    will create grunt threads if any links found on url
    """
    quit = False
    grunts = []
    _task_running = False
    callback(Message(thread="commander", type="message", data={"message": "Commander thread has loaded. Waiting to scan"}))
    # stops code getting to long verbose
    MessageMain = functools.partial(Message, thread="commander", type="message")
    # settings dict will contain the settings at start of scraping
    settings = {}
    scanned_urldata = []
    counter = 0
    while not quit:
        try:
            # Get the json object from the global queue
            r = Threads.commander_queue.get(0.2)
            if r.thread == "main":
                if r.type == "quit":
                    Threads.cancel.set()
                    callback(Message(thread="commander", type="quit"))
                    quit = True
                elif r.type == "start":
                    if not _task_running:
                        grunts = []
                        _task_running = True

                        # load the settings from file
                        # create a new instance of it in memory
                        # we dont want these values to change
                        # whilst downloading and saving to file
                        settings = dict(Settings.load())
                        # Load the cookiejar again
                        Threads.cookie_jar = load_cookies(settings)

                        # notify main thread so can intialize UI
                        callback(MessageMain(type="searching", status="start"))
                        for thread_index, urldata in enumerate(scanned_urldata):
                            grunts.append(Grunt(thread_index, urldata, settings))
                        # reset the threads counter
                        # this is used to keep track of
                        # threads that have been  started
                        # once a running thread has been notified
                        # this thread counter is incremeneted
                        # counter is checked with length of grunts
                        # once the counter has reached length then
                        # then all threads have been complete
                        counter = 0
                        max_connections = round(int(settings["max_connections"]))
                        # if maximum running threads allowed is less then
                        # size of link count. Then open length of max n
                        if max_connections < len(grunts):
                            for x in range(max_connections):
                                grunts[x].start()
                                counter += 1
                        else:
                            # just loop what is there
                            for _grunt in grunts:
                                _grunt.start()
                                counter += 1

                elif r.type == "fetch":                
                    if not _task_running:
                        Stats.reset()
                        # Load settings
                        callback(Message(thread="commander", type="fetch", status="started"))
                        # Load the settings
                        settings = Settings.load()
                        callback(MessageMain(data={"message": "Initializing the global search filter..."}))
                        # compile our filter matches only add those from the filter list
                        parsing.compile_regex_global_filter()
                        # get the document from the URL
                        callback(MessageMain(data={"message": f"Connecting to {r.data['url']}"}))
                        # Load the cookiejar
                        Threads.cookie_jar = load_cookies(settings)
                        urldata = parsing.UrlData(r.data["url"], method="GET")
                        webreq = request_from_url(urldata, Threads.cookie_jar, settings)
                        if webreq:
                            # make sure is a text document to parse
                            ext = parsing.is_valid_content_type(
                                                                r.data["url"], 
                                                                webreq.headers["Content-type"], 
                                                                settings["images_to_search"])
                            if ext == ".html":
                                html_doc = webreq.text
                                # parse the html
                                soup = parsing.parse_html(html_doc)
                                # get the url title
                                # amd add a unique path name to the save path
                                parsing.assign_unique_name(r.data["url"], soup)
                                callback(MessageMain(data={"message": "Parsing HTML Document..."}))
                                # scrape links and images from document
                                scanned_urldata = []
                                # find images and links
                                # set the include_form to False on level 1 scan
                                if parsing.sort_soup(url=r.data["url"],
                                                     soup=soup, 
                                                     urls=scanned_urldata,
                                                     include_forms=False,
                                                     images_only=False, 
                                                     thumbnails_only=True) > 0:
                                    # send the scanned urls to the main thread for processing
                                    callback(MessageMain(data={"message": f"Parsing succesful. Found {len(scanned_urldata)} links"}))
                                    data = {"urls": scanned_urldata}
                                    reqmsg = Message(thread="commander", type="fetch", status="finished", data=data)
                                    callback(reqmsg)
                                else:
                                    # Nothing found notify main thread
                                    callback(MessageMain(data={"message": "No links found :("}))
                            webreq.close()
                    else:
                        callback(MessageMain(data={"message": "Still scanning for images please press cancel to start a new scan"}))

                elif r.type == "cancel":
                    Threads.cancel.set()

            elif r.thread == "grunt":
                if r.type == "finished":
                    # one grunt is gone start another
                    if counter < len(grunts):
                        grunts[counter].start()
                        counter += 1
                callback(r)
            
            elif r.thread == "settings":
                callback(MessageMain(data=r.data))

        except queue.Empty as err:
            print(f"Queue error: {err.__str__()}")

        finally:
            if _task_running:
                # check if all grunts are finished
                # and that the grunt counter is greater or
                # equal to the size of grunt threads 
                # if so cleanup
                # and notify main thread
                if len(grunts_alive(grunts)) == 0 and counter >= len(grunts):
                    Threads.cancel.clear()
                    grunts = []
                    _task_running = False
                    Blacklist.clear()
                    callback(Message(thread="commander", type="complete"))

def grunts_alive(grunts):
    """
    returns a list of grunt threads that are still alive
    """
    return list(filter(lambda grunt : grunt.is_alive(), grunts))

def notify_commander(message):
    """
    send_message(object)
    FIFO queue puts a no wait message on the queue

    message is a Message object
    """
    Threads.commander_queue.put_nowait(message)