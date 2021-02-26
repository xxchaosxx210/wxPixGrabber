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

from crawler.constants import CMessage as Message

import crawler.constants as const

from crawler.webrequest import (
    request_from_url,
    load_cookies
)

_Log = logging.getLogger(__name__)

def stream_to_file(path, bytes_stream):
    with open(path, "wb") as fp:
        fp.write(bytes_stream.getbuffer())
        fp.close()
        return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                       status=const.STATUS_OK, id=0, data={"message": path})
    return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                       status=const.STATUS_ERROR, id=0, data={"message": "Unable to write to file", "path": path})

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

    message = Message(thread=const.THREAD_TASK, id=0, status=const.STATUS_IGNORED,
                          event=const.EVENT_DOWNLOAD_IMAGE, data={"message": "unknown"})

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
                # if file name exists then check user settings on what to do
                if settings["file_exists"] == "rename":
                    full_path = options.rename_file(full_path)
                    message.data["message"] = "Renamed path"
                    message.data["path"] = full_path
                elif settings["file_exists"] == "skip":
                    # close the stream and dont write to disk
                    message.data["message"] = "Skipped file"
                    message.data["path"] = full_path
                    byte_stream.close()
            # everything ok. write image to disk
            message = stream_to_file(full_path, byte_stream)
        else:
            message.data["message"] = f"Bytes duplicate found locally with url {response.url} and {_duplicate}"
    else:
        # add the URl to the cache
        if not cache.query_ignore(response.url):
            cache.add_ignore(response.url, "small-image", width, height)
        message.data["message"] = f"Image too small ({width}x{height})"

    # close the file handle
    byte_stream.close()

    return message

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
        self.comm_queue.put_nowait(Message(thread=const.THREAD_TASK, event=const.EVENT_SEARCHING,
                                   id=self.task_index, status=const.STATUS_OK, data=None))
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
                msg = download_image(filename, response, self.settings)
                msg.data["url"] = response.url
                msg.id = self.task_index
                self.comm_queue.put_nowait(msg)
            except UnidentifiedImageError as err:
                # Couldnt load the Image from Stream
                self.comm_queue.put_nowait(Message(
                    thread=const.THREAD_TASK, id=self.task_index, data={"url": response.url, "message": err.__str__()},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_ERROR))
            return []
        else:
            if not cache.query_ignore(response.url):
                cache.add_ignore(response.url, "unknown-file-type", 0, 0)
                self.comm_queue.put_nowait(Message(
                    thread=const.THREAD_TASK, id=self.task_index, data={"url": response.url, "message": "Unknown File Type"},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_IGNORED))
        return datalist
    
    def add_url(self, urldata):
        """
        Query the Parent Process if this url dict exists
        if not then Parent Process will add it to its blacklist
        returns True if no entry found
        """
        self.comm_queue.put(Message(
            thread=const.THREAD_TASK,
            event=const.EVENT_BLACKLIST,
            data={"index": self.task_index, "urldata": urldata},
            id=self.task_index, status=const.STATUS_OK
        ))
        reply = self.msgbox.get()
        return reply.data["added"]
    
    def follow_url(self, urldata):
        """
        follow_url(object, object)
        request url and parse the response
        """
        try:
            resp = request_from_url(urldata, self.cookiejar, self.settings)
            urllist = self.search_response(resp, self.settings["form_search"]["enabled"])
        except Exception as err:
            self.comm_queue.put_nowait(
                    Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE, 
                            data={"url": urldata.url, "message": err.__str__()},
                            id=self.task_index, status=const.STATUS_ERROR))  
            return []
        resp.close()
        return urllist

    def run(self):
        if not self.cancel.is_set():
            self.cookiejar = load_cookies(self.settings)
            self.comm_queue.put_nowait(
                Message(thread=const.THREAD_TASK, 
                id=self.task_index, status=const.STATUS_OK, event=const.EVENT_SCANNING, data=None))
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
            self.notify_finished(const.STATUS_ERROR)
        else:
            self.notify_finished(const.STATUS_OK)
    
    def notify_finished(self, status):
        self.comm_queue.put_nowait(Message(
                thread=const.THREAD_TASK, status=status, event=const.EVENT_FINISHED, 
                id=self.task_index, data=None))