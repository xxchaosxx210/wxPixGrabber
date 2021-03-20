import multiprocessing as mp
import os
from io import BytesIO
from http.cookiejar import CookieJar
from typing import Pattern
from requests import Response

# Image
from PIL import (
    Image,
    UnidentifiedImageError
)

import crawler.parsing as parsing
import crawler.options as options
import crawler.cache as cache
import crawler.mime as mime
from crawler.types import UrlData

from crawler.message import Message

import crawler.message as const

from crawler.webrequest import (
    request_from_url,
    load_cookies
)


def stream_to_file(path: str, bytes_stream: BytesIO) -> Message:
    with open(path, "wb") as fp:
        try:
            fp.write(bytes_stream.getbuffer())
            return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                           status=const.STATUS_OK, _id=0, data={"message": "image saved", "url": path})
        except Exception as err:
            return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                           status=const.STATUS_ERROR, _id=0,
                           data={"message": err.__str__(), "url": path})


def _response_to_stream(response: Response) -> BytesIO:
    # read from requests object
    # store in memory
    byte_stream = BytesIO()
    for buff in response.iter_content(1000):
        byte_stream.write(buff)
    return byte_stream


def create_save_path(settings: dict):
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


def download_image(filename: str, response: Response, settings: dict):
    message = Message(thread=const.THREAD_TASK, _id=0, status=const.STATUS_IGNORED,
                      event=const.EVENT_DOWNLOAD_IMAGE, data={"message": "unknown", "url": response.url})

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
                    # close the stream and don't write to disk
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

    def __init__(self, task_index: int, urldata: UrlData,
                 settings: dict, filters: Pattern, commander_msg: mp.Queue,
                 cancel_event: mp.Event):
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
        self.file_index = 0
        self.filters = filters
        # Commander process message box
        self.comm_queue = commander_msg
        # Grunts message box
        self.msgbox = mp.Queue()
        self.cancel = cancel_event

    def search_response(self, response: Response, include_forms: bool) -> list:
        """
        if html parse look for image sources
        if image then save
        """
        self.comm_queue.put_nowait(Message(thread=const.THREAD_TASK, event=const.EVENT_SEARCHING,
                                           _id=self.task_index, status=const.STATUS_OK, data={}))
        # initialize the list containing UrlData objects
        data_list = []
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
                              urls=data_list,
                              include_forms=include_forms,
                              images_only=True,
                              thumbnails_only=False,
                              filters=self.filters)
        elif ext in mime.IMAGE_EXTS:
            if self.settings["generate_filenames"]["enabled"]:
                # if so then append thread index and file_index to make a unique identifier
                file_index = f"{self.task_index}_{self.file_index}{ext}"
                # increment the file_index for the next image found
                self.file_index += 1
                # append the saved unique name to our file path
                filename = f'{self.settings["generate_filenames"]["name"]}{file_index}'
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
                # Couldn't load the Image from Stream
                self.comm_queue.put_nowait(Message(
                    thread=const.THREAD_TASK, _id=self.task_index, data={"url": response.url, "message": err.__str__()},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_ERROR))
            return []
        else:
            if not cache.query_ignore(response.url):
                cache.add_ignore(response.url, "unknown-file-type", 0, 0)
                self.comm_queue.put_nowait(Message(
                    thread=const.THREAD_TASK, _id=self.task_index,
                    data={"url": response.url, "message": "Unknown File Type"},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_IGNORED))
        return data_list

    def add_url(self, url_data: UrlData) -> bool:
        """
        Query the Parent Process if this url dict exists
        if not then Parent Process will add it to its blacklist
        returns True if no entry found
        """
        self.comm_queue.put(Message(
            thread=const.THREAD_TASK,
            event=const.EVENT_BLACKLIST,
            data={"index": self.task_index, "urldata": url_data, "url": url_data.url},
            _id=self.task_index, status=const.STATUS_OK
        ))
        reply = self.msgbox.get()
        return reply.data["added"]

    def follow_url(self, url_data: UrlData, cookie_jar: CookieJar) -> list:
        """
        follow_url(object, object)
        request url and parse the response
        """
        url_list = []
        try:
            response = request_from_url(url_data, cookie_jar, self.settings)
            url_list = self.search_response(response, self.settings["form_search"]["enabled"])
            response.close()
        except Exception as err:
            self.comm_queue.put_nowait(
                Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                        data={"url": url_data.url, "message": err.__str__()},
                        _id=self.task_index, status=const.STATUS_ERROR))
        finally:
            return url_list

    def run(self):
        if not self.cancel.is_set():
            cookie_jar = load_cookies(self.settings)
            self.comm_queue.put_nowait(
                Message(thread=const.THREAD_TASK,
                        _id=self.task_index, status=const.STATUS_OK, event=const.EVENT_SCANNING,
                        data={"url": self.urldata.url}))
            # Three Levels of looping each level parses
            # finds new links to images. Saves images to file
            if self.add_url(self.urldata):
                # Level 1
                level_one_urls = self.follow_url(self.urldata, cookie_jar)
                for level_one_url_data in level_one_urls:
                    if self.add_url(level_one_url_data):
                        # Level 2
                        level_two_urls = self.follow_url(level_one_url_data, cookie_jar)
                        for level_two_url_data in level_two_urls:
                            if self.add_url(level_two_url_data):
                                # Level 3
                                self.follow_url(level_two_url_data, cookie_jar)

        if self.cancel.is_set():
            self.notify_finished(const.STATUS_ERROR, "Task has cancelled")
        else:
            self.notify_finished(const.STATUS_OK, "Task has completed")

    def notify_finished(self, status: int, message: str):
        self.comm_queue.put_nowait(Message(
            thread=const.THREAD_TASK, status=status, event=const.EVENT_FINISHED,
            _id=self.task_index, data={"message": message, "url": self.urldata.url}))
