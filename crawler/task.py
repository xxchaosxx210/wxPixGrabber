import multiprocessing as mp
import logging
import os
from io import BytesIO

# Image
from PIL import (
    Image,
    UnidentifiedImageError
)

import crawler.parsing as parsing
import crawler.options as options
import crawler.cache as cache
import crawler.mime as mime

from crawler.types import (
    Message,
    Stats
)

from crawler.webrequest import (
    request_from_url,
    load_cookies
)

_Log = logging.getLogger(__name__)

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

def download_image(filename, response, settings):
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
        # create a new save path
        path = create_save_path(settings)
        full_path = os.path.join(path, filename)
        # check byte duplicate
        _duplicate = options.image_exists(path, response.content)
        # check filename duplicate
        if not _duplicate:
            if os.path.exists(full_path):
                _Log.info(f"{full_path} already exists...")
                # if file name exists then check user settings on what to do
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
            _Log.info(f"Bytes duplicate found locally with url {response.url} and {_duplicate}")
            stats.ignored += 1
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
        ext = mime.is_valid_content_type(
            response.url,
            response.headers.get("Content-Type", ""),
            self.settings["images_to_search"]
        )
        if mime.EXT_HTML == ext:
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
        elif ext in mime.IMAGE_EXTS:
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
                stats = download_image(filename, response, self.settings)
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