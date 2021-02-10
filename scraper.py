import threading
import queue
import functools
import os
from io import BytesIO
from dataclasses import dataclass

from webrequest import (
    request_from_url,
    Urls,
    load_cookies
)

# Image
from PIL import (
    Image,
    UnidentifiedImageError
)

from global_props import Settings

import parsing

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


class ImageFile:

    """
    thread safe. saves bytes read from requests
    and saves to disk
    """

    @staticmethod
    def write_to_file(path, filename, bytes_stream):
        parsing.Globals.new_folder_lock.acquire()
        if not os.path.exists(path):
            os.mkdir(path)
        parsing.Globals.new_folder_lock.release()
        full_path = os.path.join(path, filename)
        with open(full_path, "wb") as fp:
            fp.write(bytes_stream.getbuffer())
            fp.close()

def create_commander(callback):
    """
    create the main handler thread.
    this thread will stay iterating for the
    remainder of the programs life cycle
    """
    Threads.commander = threading.Thread(
        target=commander_thread, kwargs={"callback": callback})
    return Threads.commander

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
        image = None
        print(f"[IMAGE_ERROR]: {err.__str__()}, {response.url}")
    if image:
        width, height = image.size
        # if image requirements met then save
        if width > 200 and height > 200:
            # check if directory exists
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
            ImageFile.write_to_file(path, filename, byte_stream)
            notify_commander(Message(thread="grunt", type="image", status="ok", data={"pathname": filename, "url": response.url}))
        image.close()
    byte_stream.close()  


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
    
    def run(self):
        # partial function to avoid repetitive typing
        GruntMessage = functools.partial(Message, id=self.thread_index, thread="grunt")
        #Threads.semaphore.acquire()
        if not Threads.cancel.is_set():
            notify_commander(GruntMessage(status="ok", type="scanning"))
            # request the url
            r = request_from_url(self.urldata, Threads.cookie_jar, self.settings)
            if r:
                ext = parsing.is_valid_content_type(self.urldata.url, r.headers.get("Content-Type"), self.settings["images_to_search"])
                if ".html" == ext:
                    imgdata_list = []
                    # parse the document and search for images only
                    if parsing.parse_html(self.urldata.url, r.text, imgdata_list, images_only=True, thumbnails_only=False) > 0:
                        r.close()

                        # Might need to take an extra step in parsing form data
                        # if form data then submit request

                        for index, imgdata in enumerate(imgdata_list):
                            # check if url has already in global list
                            if not Urls.url_exists(imgdata.url):
                                # its ok then add it to the global list
                                Urls.add_url(imgdata.url)
                                # download each one and save it
                                imgresp = request_from_url(imgdata, Threads.cookie_jar, self.settings)

                                if imgresp:
                                    # check the content-type matches and image
                                    ext = parsing.is_valid_content_type(imgdata.url, 
                                                                        imgresp.headers.get("Content-Type"), 
                                                                        self.settings["images_to_search"])

                                    if ext in parsing.IMAGE_EXTS:
                                        # if image then create a file path and check
                                        # the image resolution size matches
                                        # if it does then save to file
                                        if self.settings["generate_filenames"]["enabled"]:
                                            filename = f'{self.settings["generate_filenames"]["name"]}{self.thread_index}{ext}'
                                        else:
                                            filename = f"test{self.thread_index}{ext}"
                                        download_image(filename, imgresp, self.settings)
                                    # close the image request handle
                                    imgresp.close()
                else:
                    if ext in parsing.IMAGE_EXTS:
                        if not Urls.url_exists(self.urldata.url):
                            Urls.add_url(self.urldata.url)
                            # if image then create a file path and check
                            # the image resolution size matches
                            # if it does then save to file
                            if self.settings["generate_filenames"]["enabled"]:
                                filename = f'{self.settings["generate_filenames"]["name"]}{self.thread_index}{ext}'
                            else:
                                filename = f"test{self.thread_index}{ext}"
                            download_image(filename, r, self.settings)
                    r.close()
        #Threads.semaphore.release()
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
                        # Set the max connections
                        max_connections = round(int(settings["max_connections"]))

                        callback(MessageMain(data={"message": "Starting Threads..."}))
                        for thread_index, urldata in enumerate(scanned_urldata):
                            grunts.append(Grunt(thread_index, urldata, settings))
                        counter = 0
                        max_connections = round(int(settings["max_connections"]))
                        if max_connections < len(grunts):
                            for x in range(max_connections):
                                grunts[x].start()
                                counter += 1
                        else:
                            for _grunt in grunts:
                                _grunt.start()
                                counter += 1

                elif r.type == "fetch":                
                    if not _task_running:
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
                                # get the url title
                                parsing.assign_unique_name(r.data["url"], html_doc)
                                callback(MessageMain(data={"message": "Parsing HTML Document..."}))
                                # scrape links and images from document
                                scanned_urldata = []
                                if parsing.parse_html(url=r.data["url"], 
                                                      html=html_doc, 
                                                      urls=scanned_urldata,
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
                # check if all grunts are finished if so cleanup
                # and notify main thread
                if len(grunts_alive(grunts)) == 0:
                    Threads.cancel.clear()
                    grunts = []
                    _task_running = False
                    Urls.clear()
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