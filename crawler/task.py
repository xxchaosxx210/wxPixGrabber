import multiprocessing as mp
import threading
import os
import logging
import ctypes
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
from crawler.message import Message
import crawler.message as const

from crawler.webrequest import (
    request_from_url,
    load_cookies,
    UrlData
)


_Log = logging.getLogger(__name__)


def stream_to_file(path: str, bytes_stream: BytesIO) -> Message:
    """
    Writes the buffer to file
    Args:
        path: the file path to save to
        bytes_stream: the stream saving from

    Returns:
        Message object containing either STATUS_OK or STATUS_ERROR if could not save to file
    """
    with open(path, "wb") as fp:
        try:
            fp.write(bytes_stream.getbuffer())
            return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                           status=const.STATUS_OK, id=0, data={"message": "image saved", "path": path})
        except Exception as err:
            return Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                           status=const.STATUS_ERROR, id=0,
                           data={"message": err.__str__(), "path": path})


def _response_to_stream(response: Response) -> BytesIO:
    # read from requests object
    # store in memory
    byte_stream = BytesIO()
    for buff in response.iter_content(1000):
        byte_stream.write(buff)
    return byte_stream


def create_save_path(settings: dict):
    """
    Settings object load from file append the unique folder path if required. Create the directory if not exists
    Args:
        settings: the settings json object which contains the unique name if choosen

    Returns:
        path (str): returns the newly created path name
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


def download_image(filename: str, response: Response, settings: dict) -> Message:
    """

    Args:
        filename: the name of the file to be saved to. This may change depending on same filename
        response: Response object returned from requests
        settings: Settings json object used to find unique save path and what to do if same filename found

    Returns:
        message (object): Message object containing information about what happened. This should be passed
                          onto the Commander thread and handled
    """
    message = Message(thread=const.THREAD_TASK,
                      id=0,
                      status=const.STATUS_IGNORED,
                      event=const.EVENT_DOWNLOAD_IMAGE,
                      data={"message": "unknown", "url": response.url})

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


class Task(threading.Thread):

    """
    Worker thread for following the given Link and determining whether to save image
    """

    def __init__(self,
                 task_index: int,
                 url_data: UrlData,
                 settings: dict,
                 filters: Pattern,
                 commander_msg: mp.Queue,
                 cancel_event: mp.Event,
                 pause_event: mp.Event):
        super().__init__()
        self.task_index = task_index
        # tasks starting url
        self.url_data = url_data
        self.settings = settings
        self.file_index = 0
        self.filters = filters
        # Commander process message box
        self.comm_queue = commander_msg
        # Tasks message box
        self.msg_box = mp.Queue()
        self.cancel = cancel_event
        self.pause = pause_event
        # flag for checking network IO state. If this is set and cancel flag is also set
        # then an exception is raised outside of the thread. This is so if cancel is set
        # the thread doesnt wait until network connection timeout also makes it thread safe
        self._network_io = threading.Event()

    def search_response(self, response: Response, include_forms: bool) -> dict:
        """
        if html parse look for image sources
        if image then save
        """
        urls = {}
        self.comm_queue.put_nowait(Message(thread=const.THREAD_TASK, event=const.EVENT_SEARCHING,
                                           id=self.task_index, status=const.STATUS_OK, data={}))
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
            for url_index, url in enumerate(parsing.sort_soup(url=response.url,
                                                              soup=soup,
                                                              include_forms=include_forms,
                                                              images_only=True,
                                                              thumbnails_only=False,
                                                              filters=self.filters,
                                                              img_exts=self.settings["images_to_search"])):
                if url:
                    urls[url_index] = url
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
                    thread=const.THREAD_TASK, id=self.task_index, data={"url": response.url, "message": err.__str__()},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_ERROR))
            return {}
        else:
            if not cache.query_ignore(response.url):
                cache.add_ignore(response.url, "unknown-file-type", 0, 0)
                self.comm_queue.put_nowait(Message(
                    thread=const.THREAD_TASK, id=self.task_index,
                    data={"url": response.url, "message": "Unknown File Type"},
                    event=const.EVENT_DOWNLOAD_IMAGE, status=const.STATUS_IGNORED))
        return urls

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
            id=self.task_index, status=const.STATUS_OK
        ))
        reply = self.msg_box.get()
        return reply.data["added"]

    def _follow_url(self, url_data: UrlData, cookie_jar: CookieJar) -> dict:
        """

        Args:
            url_data: UrlData object
            cookie_jar: CookieJar object

        Returns:

        """
        # Hang the thread if Pause flag is set
        if self.pause.is_set():
            self.wait()
        urls = {}
        try:
            self._network_io.set()
            response = request_from_url(url_data, cookie_jar, self.settings)
            self._network_io.clear()
            if self.cancel.is_set():
                response.close()
                raise Exception("Task has been Cancelled")
            urls = self.search_response(response, self.settings["form_search"]["enabled"])
            response.close()
        except Exception as err:
            self.comm_queue.put_nowait(
                Message(thread=const.THREAD_TASK, event=const.EVENT_DOWNLOAD_IMAGE,
                        data={"url": url_data.url, "message": err.__str__()},
                        id=self.task_index, status=const.STATUS_ERROR))
        finally:
            return urls

    def run(self):
        if not self.cancel.is_set():
            cookie_jar = load_cookies(self.settings)
            self.comm_queue.put_nowait(
                Message(thread=const.THREAD_TASK,
                        id=self.task_index, status=const.STATUS_OK, event=const.EVENT_SCANNING,
                        data={"url": self.url_data.url}))
            # Three Levels of looping each level parses
            # finds new links to images. Saves images to file
            if self.add_url(self.url_data):
                # Level 1
                level_one_urls = self._follow_url(self.url_data, cookie_jar)
                for level_one_url_data in level_one_urls.values():
                    if self.add_url(level_one_url_data):
                        # Level 2
                        level_two_urls = self._follow_url(level_one_url_data, cookie_jar)
                        for level_two_url_data in level_two_urls.values():
                            if self.add_url(level_two_url_data):
                                # Level 3
                                self._follow_url(level_two_url_data, cookie_jar)

        if self.cancel.is_set():
            self.notify_finished(const.STATUS_ERROR, "Task has cancelled")
        else:
            self.notify_finished(const.STATUS_OK, "Task has completed")

    def notify_finished(self, status: int, message: str):
        if self.pause.is_set():
            self.wait()
        self.comm_queue.put_nowait(Message(
            thread=const.THREAD_TASK, status=status, event=const.EVENT_FINISHED,
            id=self.task_index, data={"message": message, "url": self.url_data.url}))

    def wait(self):
        _Log.info(f"Task #{self.task_index} has paused")
        self.msg_box.get()

    def terminate(self):
        """
        raises exception within thread if network IO operation.
        Make sure to set the cancel flag and call terminate
        """
        _Log.info(f"Pause state {self.pause.is_set()}")
        _Log.info(f"Cancel State {self.cancel.is_set()}")
        if self._network_io.is_set():
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, 0)
                _Log.info("Exception raise failure")
            else:
                self.notify_finished(const.STATUS_ERROR, "Task has Cancelled")
