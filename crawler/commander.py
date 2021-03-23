import threading
import logging
import multiprocessing as mp
import queue
from dataclasses import dataclass
from requests import Response
from http.cookiejar import CookieJar

import crawler.cache as cache
import crawler.parsing as parsing
import crawler.options as options
import crawler.mime as mime

from crawler.task import Task

from crawler.message import Message
import crawler.message as const

from crawler.types import (
    Blacklist,
    UrlData
)

from crawler.webrequest import (
    request_from_url,
    load_cookies
)

_Log = logging.getLogger(__name__)

_QUEUE_TIMEOUT = 0.1


@dataclass
class Commander:
    thread: threading.Thread
    queue: mp.Queue


@dataclass
class _CommanderProperties:
    settings: dict
    scanned_urls: list
    blacklist: Blacklist
    counter: int
    cancel_all: mp.Event
    task_running: int
    tasks: list
    quit_thread: mp.Event
    time_counter: float
    msg_box: queue.Queue


def tasks_alive(tasks: list) -> list:
    """checks how many tasks are still running

    Args:
        tasks (list): The list of Tasks to check

    Returns:
        [list]: returns all active running tasks
    """
    return list(filter(lambda task: task.is_alive(), tasks))


def _reset_comm_props(properties: _CommanderProperties):
    properties.cancel_all.clear()
    properties.tasks = []
    properties.task_running = 0
    properties.blacklist.clear()
    properties.time_counter = 0.0


def _start_max_tasks(tasks: list, max_tasks: int) -> int:
    # This function will be called to start the Process Pool
    # returns an integer to how many Tasks have been started
    counter = 0
    for th in tasks:
        if counter >= max_tasks:
            break
        else:
            th.start()
            counter += 1
    return counter


def create_commander(main_queue: mp.Queue) -> Commander:
    """main handler for starting and keeping track of worker tasks

    Args:
        main_queue (object): atomic Queue object used to send messages to main thread

    Returns:
        [object]: returns a Commander dataclass 
    """
    msg_queue = mp.Queue()
    return Commander(
        threading.Thread(target=_thread, kwargs={"main_queue": main_queue, "msg_box": msg_queue}),
        msg_queue)


def _init_start(properties: _CommanderProperties) -> tuple:
    # initialize commander threads variables and return new objects
    properties.tasks = []
    properties.task_running = 1
    properties.blacklist.clear()
    properties.settings = options.load_settings()
    cj = load_cookies(properties.settings)
    filters = parsing.compile_filter_list(properties.settings["filter-search"])
    return cj, filters


def _start_tasks(props: _CommanderProperties) -> int:
    cookiejar, filters = _init_start(props)
    for task_index, url_data in enumerate(props.scanned_urls):
        props.tasks.append(Task(task_index, url_data, props.settings, filters, props.msg_box, props.cancel_all))
    # reset the tasks counter this is used to keep track of
    # tasks that have been  started once a running thread has been notified
    # this thread counter is incremented counter is checked with length of props.tasks
    # once the counter has reached length then then all tasks have been complete
    max_connections = props.settings["max_connections"]
    props.counter = _start_max_tasks(props.tasks, max_connections)
    return props.counter


def _init_fetch(url: str, props: _CommanderProperties) -> tuple:
    """
    clears initializes the CommanderProperties, loads settings and returns
    Args:
        url: the url to go fetch from
        props: the commander property dataclass

    Returns:
        tuple - UrlData, CookieJar

    """
    props.scanned_urls = []
    props.cancel_all.clear()
    props.settings = options.load_settings()
    if url:
        cookie_jar = load_cookies(props.settings)
        url_data = UrlData(url, method="GET")
    else:
        cookie_jar = None
        url_data = None
    return url_data, cookie_jar


def _parse_response(html_doc: str, url: str, filter_settings: dict) -> tuple:
    """
    Parses the HTML
    Args:
        html_doc: html text to parse
        url: the url to convert a unique folder name into
        filter_settings: a dict of words to search for this will be compiled to a regex pattern

    Returns:
        tuple - BeautifulSoup, str, Pattern

    """
    soup = parsing.parse_html(html_doc)
    html_title = getattr(soup.find("title"), "text", "")
    options.assign_unique_name(url, html_title)
    filters = parsing.compile_filter_list(filter_settings)
    return soup, html_title, filters


def _request_url(url_data: UrlData, cookie_jar: CookieJar, props: _CommanderProperties) -> Response:
    """
    Attempts to load from file first and connects to Url if filenotfound
    Args:
        url_data:
        cookie_jar:
        props:

    Returns:
        Tuple: requests.Response
    """
    response = None
    try:
        response = options.load_from_file(url_data.url)
    except FileNotFoundError:
        response = request_from_url(url_data, cookie_jar, props.settings)
    finally:
        return response


class Commander(threading.Thread):

    def __init__(self, main_queue: mp.Queue):
        super().__init__()
        self.main_queue = main_queue
        self.msg_box = mp.Queue()
        self.settings = None
        self.scanned_urls = []
        self.blacklist = []
        self.counter = 0
        self.cancel_all = mp.Event()
        self.task_running = False
        self.tasks = []
        self.quit_thread = mp.Event()
        self.time_counter = 0.0

    def run(self):
        # create an ignore table in the sqlite file
        cache.initialize_ignore()
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
            data={"message": "Commander thread has loaded. Waiting to scan"}))
        while not self.quit_thread.is_set():
            try:
                if self.task_running:
                    r = self.msg_box.get(timeout=_QUEUE_TIMEOUT)
                else:
                    r = self.msg_box.get(timeout=None)
                if r.thread == const.THREAD_MAIN:
                    if r.event == const.EVENT_QUIT:
                        self.cancel_all.set()
                        self.main_queue.put(
                            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT, data={}))
                        self.quit_thread.set()
                    elif r.event == const.EVENT_START:
                        if not self.task_running:
                            if self._start_tasks() > 0:
                                # notify main thread so can initialize UI
                                self.main_queue.put_nowait(
                                    Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START, data={}))
                            else:
                                self.main_queue.put_nowait(Message(const.THREAD_COMMANDER, const.EVENT_MESSAGE,
                                                              data={"message": "Could not start Tasks"}))
                    elif r.event == const.EVENT_FETCH:
                        if not self.task_running:
                            self.main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                                data={"message": f"Connecting to {r.data['url']}..."}))
                            try:
                                url_data, cookie_jar = _init_fetch(r.data["url"], self)
                                fetch_response = _request_url(url_data, cookie_jar, self)
                                ext = mime.is_valid_content_type(r.data["url"], fetch_response.headers["Content-Type"],
                                                                 self.settings["images_to_search"])
                                if ext == mime.EXT_HTML:
                                    soup, html_title, filters = _parse_response(fetch_response.text, r.data["url"],
                                                                                self.settings["filter-search"])
                                    # find images and links, set the include_form to False on level 1 scan
                                    # compile our filter matches only add those from the filter list
                                    if parsing.sort_soup(url=r.data["url"], soup=soup, urls=self.scanned_urls,
                                                         include_forms=False, images_only=False,
                                                         thumbnails_only=self.settings.get("thumbnails_only", True),
                                                         filters=filters) > 0:
                                        self.main_queue.put_nowait(
                                            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                                    data={"urls": self.scanned_urls,
                                                          "title": html_title, "url": r.data["url"]}))
                                    else:
                                        self.main_queue.put_nowait(
                                            Message(thread=const.THREAD_COMMANDER,
                                                    data={"message": "No Links Found :("},
                                                    event=const.EVENT_MESSAGE))
                                fetch_response.close()
                            except Exception as err:
                                # couldn't connect
                                self.main_queue.put_nowait(Message(
                                    thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_ERROR,
                                    data={"message": err.__str__(), "url": r.data["url"]}))
                        else:
                            # Task still running ignore request
                            self.main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_IGNORED,
                                data={"message": "Tasks still running", "url": r.data["url"]}))

                    elif r.event == const.EVENT_CANCEL:
                        self.cancel_all.set()

                elif r.thread == const.THREAD_SERVER:
                    if r.event == const.EVENT_SERVER_READY:
                        if not self.task_running:
                            # Initialize and load settings
                            _init_fetch("", self)
                            soup, html_title, filters = _parse_response(r.data["html"], "",
                                                                        self.settings["filter-search"])
                            if parsing.sort_soup(url=r.data["url"], soup=soup,
                                                 urls=self.scanned_urls, include_forms=False, images_only=False,
                                                 thumbnails_only=self.settings.get("thumbnails_only", True),
                                                 filters=filters) > 0:
                                self.main_queue.put_nowait(
                                    Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                            data={"urls": self.scanned_urls, "title": html_title,
                                                  "url": r.data["url"]}))
                                # Message ourselves and start the search
                                self.msg_box.put_nowait(
                                    Message(thread=const.THREAD_MAIN, event=const.EVENT_START, data={}))
                            else:
                                # Nothing found notify main thread
                                self.main_queue.put_nowait(
                                    Message(thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                                            data={"message": "No Links Found :("}))

                elif r.thread == const.THREAD_TASK:
                    if r.event == const.EVENT_FINISHED:
                        # one task is gone start another
                        if self.counter < len(self.tasks):
                            if not self.cancel_all.is_set():
                                # start the next task if not cancelled and increment the counter
                                self.tasks[self.counter].start()
                                self.counter += 1
                            else:
                                # if cancel flag been set the counter to its limit and this will force a Task Complete
                                self.counter = len(self.tasks)
                        self.main_queue.put_nowait(r)
                    elif r.event == const.EVENT_BLACKLIST:
                        # check the self.blacklist with url_data and notify Task process
                        # if no duplicate and added then True returned
                        process_index = r.data["index"]
                        task = self.tasks[process_index]
                        if not self.blacklist.exists(r.data["urldata"]):
                            self.blacklist.add(r.data["urldata"])
                            blacklist_added = True
                        else:
                            blacklist_added = False
                        task.msgbox.put(Message(
                            thread=const.THREAD_COMMANDER, event=const.EVENT_BLACKLIST,
                            data={"added": blacklist_added}))
                    else:
                        # something pass onto main thread
                        self.main_queue.put_nowait(r)
            except queue.Empty:
                pass

            finally:
                if self.task_running:
                    # check if all self.tasks are finished
                    # and that the task self.counter is greater or
                    # equal to the size of task tasks
                    # if so cleanup
                    # and notify main thread
                    if len(tasks_alive(self.tasks)) == 0 and self.counter >= len(self.tasks):
                        self.main_queue.put_nowait(Message(
                            thread=const.THREAD_COMMANDER, event=const.EVENT_COMPLETE,
                            id=0, status=const.STATUS_OK, data={}))
                        self._reset()
                    else:
                        # cancel flag is set. Start counting to timeout
                        # then start terminating processing
                        if self.cancel_all.is_set():
                            if self.time_counter >= self.settings["connection_timeout"]:
                                # kill any hanging tasks
                                for task in self.tasks:
                                    if task.is_alive():
                                        task.terminate()
                                        self.counter += 1
                            else:
                                self.time_counter += _QUEUE_TIMEOUT

    def _start_max_tasks(self, max_tasks: int):
        # This function will be called to start the Process Pool
        # returns an integer to how many Tasks have been started
        self.counter = 0
        for th in self.tasks:
            if self.counter >= max_tasks:
                break
            else:
                th.start()
                self.counter += 1

    def _start_tasks(self) -> int:
        cookiejar, filters = _init_start(self)
        for task_index, url_data in enumerate(self.scanned_urls):
            self.tasks.append(Task(task_index, url_data, self.settings, filters, self.msg_box, self.cancel_all))
        # reset the tasks counter this is used to keep track of
        # tasks that have been  started once a running thread has been notified
        # this thread counter is incremented counter is checked with length of self.tasks
        # once the counter has reached length then then all tasks have been complete
        self._start_max_tasks(self.settings["max_connections"])
        return self.counter

    def _reset(self):
        self.cancel_all.clear()
        self.tasks = []
        self.task_running = 0
        self.blacklist.clear()
        self.time_counter = 0.0



def _thread(main_queue: mp.Queue, msg_box: mp.Queue):
    """main task handler thread

    Args:
        main_queue (Queue): atomic Queue object used to send messages to main thread
        msg_box (Queue): the atomic Queue object to receive messages from
    """
    # create an ignore table in the sqlite file
    cache.initialize_ignore()

    main_queue.put_nowait(Message(
        thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
        data={"message": "Commander thread has loaded. Waiting to scan"}))

    props = _CommanderProperties(settings={}, scanned_urls=[], blacklist=Blacklist(),
                                 counter=0, cancel_all=mp.Event(), task_running=0,
                                 tasks=[], quit_thread=mp.Event(), time_counter=0.0,
                                 msg_box=msg_box)

    while not props.quit_thread.is_set():
        try:
            if props.task_running:
                r = props.msg_box.get(timeout=_QUEUE_TIMEOUT)
            else:
                r = props.msg_box.get(timeout=None)
            if r.thread == const.THREAD_MAIN:
                if r.event == const.EVENT_QUIT:
                    props.cancel_all.set()
                    main_queue.put(
                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT, data={}))
                    props.quit_thread.set()
                elif r.event == const.EVENT_START:
                    if not props.task_running:
                        if _start_tasks(props) > 0:
                            # notify main thread so can initialize UI
                            main_queue.put_nowait(
                                Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START, data={}))
                        else:
                            main_queue.put_nowait(Message(const.THREAD_COMMANDER, const.EVENT_MESSAGE,
                                                          data={"message": "Could not start Tasks"}))
                elif r.event == const.EVENT_FETCH:
                    if not props.task_running:
                        main_queue.put_nowait(Message(
                            thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                            data={"message": f"Connecting to {r.data['url']}..."}))
                        try:
                            url_data, cookie_jar = _init_fetch(r.data["url"], props)
                            fetch_response = _request_url(url_data, cookie_jar, props)
                            ext = mime.is_valid_content_type(r.data["url"], fetch_response.headers["Content-Type"],
                                                             props.settings["images_to_search"])
                            if ext == mime.EXT_HTML:
                                soup, html_title, filters = _parse_response(fetch_response.text, r.data["url"],
                                                                            props.settings["filter-search"])
                                # find images and links, set the include_form to False on level 1 scan
                                # compile our filter matches only add those from the filter list
                                if parsing.sort_soup(url=r.data["url"], soup=soup, urls=props.scanned_urls,
                                                     include_forms=False, images_only=False,
                                                     thumbnails_only=props.settings.get("thumbnails_only", True),
                                                     filters=filters) > 0:
                                    main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                                data={"urls": props.scanned_urls,
                                                      "title": html_title, "url": r.data["url"]}))
                                else:
                                    main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, data={"message": "No Links Found :("},
                                                event=const.EVENT_MESSAGE))
                            fetch_response.close()
                        except Exception as err:
                            # couldn't connect
                            main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_ERROR,
                                data={"message": err.__str__(), "url": r.data["url"]}))
                    else:
                        # Task still running ignore request
                        main_queue.put_nowait(Message(
                            thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_IGNORED,
                            data={"message": "Tasks still running", "url": r.data["url"]}))

                elif r.event == const.EVENT_CANCEL:
                    props.cancel_all.set()

            elif r.thread == const.THREAD_SERVER:
                if r.event == const.EVENT_SERVER_READY:
                    if not props.task_running:
                        # Initialize and load settings
                        _init_fetch("", props)
                        soup, html_title, filters = _parse_response(r.data["html"], "", props.settings["filter-search"])
                        if parsing.sort_soup(url=r.data["url"], soup=soup,
                                             urls=props.scanned_urls, include_forms=False, images_only=False,
                                             thumbnails_only=props.settings.get("thumbnails_only", True),
                                             filters=filters) > 0:
                            main_queue.put_nowait(
                                Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                        data={"urls": props.scanned_urls, "title": html_title, "url": r.data["url"]}))
                            # Message ourselves and start the search
                            props.msg_box.put_nowait(
                                Message(thread=const.THREAD_MAIN, event=const.EVENT_START, data={}))
                        else:
                            # Nothing found notify main thread
                            main_queue.put_nowait(
                                Message(thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                                        data={"message": "No Links Found :("}))

            elif r.thread == const.THREAD_TASK:
                if r.event == const.EVENT_FINISHED:
                    # one task is gone start another
                    if props.counter < len(props.tasks):
                        if not props.cancel_all.is_set():
                            # start the next task if not cancelled and increment the counter
                            props.tasks[props.counter].start()
                            props.counter += 1
                        else:
                            # if cancel flag been set the counter to its limit and this will force a Task Complete
                            props.counter = len(props.tasks)
                    main_queue.put_nowait(r)
                elif r.event == const.EVENT_BLACKLIST:
                    # check the props.blacklist with url_data and notify Task process
                    # if no duplicate and added then True returned
                    process_index = r.data["index"]
                    task = props.tasks[process_index]
                    if not props.blacklist.exists(r.data["urldata"]):
                        props.blacklist.add(r.data["urldata"])
                        blacklist_added = True
                    else:
                        blacklist_added = False
                    task.msgbox.put(Message(
                        thread=const.THREAD_COMMANDER, event=const.EVENT_BLACKLIST, data={"added": blacklist_added}))
                else:
                    # something pass onto main thread
                    main_queue.put_nowait(r)
        except queue.Empty:
            pass

        finally:
            if props.task_running:
                # check if all props.tasks are finished
                # and that the task props.counter is greater or
                # equal to the size of task tasks
                # if so cleanup
                # and notify main thread
                if len(tasks_alive(props.tasks)) == 0 and props.counter >= len(props.tasks):
                    main_queue.put_nowait(Message(
                        thread=const.THREAD_COMMANDER, event=const.EVENT_COMPLETE,
                        id=0, status=const.STATUS_OK, data={}))
                    _reset_comm_props(props)
                else:
                    # cancel flag is set. Start counting to timeout
                    # then start terminating processing
                    if props.cancel_all.is_set():
                        if props.time_counter >= props.settings["connection_timeout"]:
                            # kill any hanging tasks
                            for task in props.tasks:
                                if task.is_alive():
                                    task.terminate()
                                    props.counter += 1
                        else:
                            props.time_counter += _QUEUE_TIMEOUT
