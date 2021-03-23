import threading
import logging
import multiprocessing as mp
import queue

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


class Commander(threading.Thread):

    def __init__(self, main_queue: mp.Queue):
        super().__init__()
        self.main_queue = main_queue
        self.queue = mp.Queue()
        self.settings = {}
        self.scanned_urls = []
        self.blacklist = Blacklist()
        self.counter = 0
        self.cancel_all = mp.Event()
        self.task_running = False
        self.tasks = []
        self.quit_thread = mp.Event()
        self.time_counter = 0.0

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

    def _reset(self):
        self.cancel_all.clear()
        self.tasks = []
        self.task_running = False
        self.blacklist.clear()
        self.time_counter = 0.0

    def message_main(self, message: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
            status=const.STATUS_OK, data={"message": message}))

    def message_quit(self):
        self.main_queue.put(
            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT, data={}))

    def message_start(self):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START, data={}))

    def message_fetch_ok(self, html_title: str, url: str):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                    data={"urls": self.scanned_urls, "title": html_title, "url": url}))

    def message_fetch_error(self, err: str, url: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_ERROR,
            data={"message": err, "url": url}))

    def message_fetch_ignored(self, url: str, message: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_IGNORED,
            data={"message": message, "url": url}))

    def message_complete(self):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_COMPLETE, data={}))

    def _check_blacklist(self, url_data: UrlData, task_index: int):
        # check the self.blacklist with urldata and notify Task process
        # if no duplicate and added then True returned
        blacklist_added = self.blacklist.exists(url_data)
        if not blacklist_added:
            self.blacklist.add(url_data)
        # flip the boolean to tell the task thread to either continue or not search for the next link
        blacklist_added = not blacklist_added
        task = self.tasks[task_index]
        task.msgbox.put(Message(thread=const.THREAD_COMMANDER, event=const.EVENT_BLACKLIST,
                                data={"added": blacklist_added}))

    def run(self):
        # create an ignore table in the sqlite file
        cache.initialize_ignore()
        self.message_main("Commander thread has loaded. Waiting to scan")

        while not self.quit_thread.is_set():
            try:
                if self.task_running:
                    r = self.queue.get(timeout=_QUEUE_TIMEOUT)
                else:
                    r = self.queue.get(timeout=None)
                if r.thread == const.THREAD_MAIN:
                    if r.event == const.EVENT_QUIT:
                        self.cancel_all.set()
                        self.message_quit()
                        self.quit_thread.set()
                    elif r.event == const.EVENT_START:
                        if not self.task_running:
                            cookiejar, filters = _init_start(self)

                            for task_index, urldata in enumerate(self.scanned_urls):
                                task = Task(task_index, urldata, self.settings,
                                            filters, self.queue, self.cancel_all)
                                self.tasks.append(task)

                            # reset the tasks counter this is used to keep track of
                            # tasks that have been  started once a running thread has been notified
                            # this thread counter is incremented counter is checked with length of self.tasks
                            # once the counter has reached length then then all tasks have been complete
                            self._start_max_tasks(self.settings["max_connections"])
                            # notify main thread so can initialize UI
                            self.message_start()
                    elif r.event == const.EVENT_FETCH:
                        if not self.task_running:
                            self.cancel_all.clear()
                            self.settings = options.load_settings()
                            cookiejar = load_cookies(self.settings)
                            urldata = UrlData(r.data["url"], method="GET")
                            self.message_main(f"Connecting to {r.data['url']}...")
                            try:
                                try:
                                    fetch_response = options.load_from_file(r.data["url"])
                                except FileNotFoundError:
                                    fetch_response = request_from_url(urldata, cookiejar, self.settings)
                                ext = mime.is_valid_content_type(r.data["url"],
                                                                 fetch_response.headers["Content-Type"],
                                                                 self.settings["images_to_search"])
                                if ext == mime.EXT_HTML:
                                    html_doc = fetch_response.text
                                    # parse the html
                                    soup = parsing.parse_html(html_doc)
                                    # get the url title
                                    # amd add a unique path name to the save path
                                    html_title = getattr(soup.find("title"), "text", "")
                                    options.assign_unique_name(
                                        fetch_response.url, html_title)
                                    # scrape links and images from document
                                    self.scanned_urls = []
                                    # find images and links
                                    # set the include_form to False on level 1 scan
                                    # compile our filter matches only add those from the filter list
                                    filters = parsing.compile_filter_list(self.settings["filter-search"])
                                    if parsing.sort_soup(url=r.data["url"], soup=soup,
                                                         urls=self.scanned_urls, include_forms=False,
                                                         images_only=False,
                                                         thumbnails_only=self.settings.get("thumbnails_only", True),
                                                         filters=filters) > 0:
                                        self.message_fetch_ok(html_title, r.data["url"])
                                    else:
                                        self.message_main("No Links Found :(")
                                fetch_response.close()
                            except Exception as err:
                                # couldn't connect
                                self.message_fetch_error(err.__str__(), r.data["url"])
                        else:
                            self.message_fetch_ignored(r.data["url"], "Tasks still running")

                    elif r.event == const.EVENT_CANCEL:
                        self.cancel_all.set()

                elif r.thread == const.THREAD_SERVER:
                    if r.event == const.EVENT_SERVER_READY:
                        if not self.task_running:
                            # Initialize and load settings
                            self.cancel_all.clear()
                            self.scanned_urls = []
                            self.settings = options.load_settings()
                            # Parse the HTML sent from the Server and assign a unique Path name if required
                            soup = parsing.parse_html(r.data["html"])
                            html_title = getattr(soup.find("title"), "text", "")
                            options.assign_unique_name("", html_title)
                            # Setup Search filters and find matches within forms, links and images
                            filters = parsing.compile_filter_list(self.settings["filter-search"])
                            if parsing.sort_soup(url=r.data["url"], soup=soup,
                                                 urls=self.scanned_urls, include_forms=False, images_only=False,
                                                 thumbnails_only=self.settings.get("thumbnails_only", True),
                                                 filters=filters) > 0:
                                self.message_fetch_ok(html_title, r.data["url"])
                                # Message ourselves and start the search
                                self.queue.put_nowait(
                                    Message(thread=const.THREAD_MAIN, event=const.EVENT_START, data={}))
                            else:
                                self.message_main("No Links Found :(")

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
                        # Pass the Task Finished event to the Main Thread
                        self.main_queue.put_nowait(r)
                    elif r.event == const.EVENT_BLACKLIST:
                        self._check_blacklist(r.data["urldata"], r.data["index"])
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
                        self.message_complete()
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


def tasks_alive(tasks: list) -> list:
    """checks how many tasks are still running

    Args:
        tasks (list): The list of Tasks to check

    Returns:
        [list]: returns all active running tasks
    """
    return list(filter(lambda task: task.is_alive(), tasks))


def _init_start(properties: Commander) -> tuple:
    # initialize commander threads variables and return new objects
    properties.tasks = []
    properties.task_running = True
    properties.blacklist.clear()
    properties.settings = options.load_settings()
    cj = load_cookies(properties.settings)
    filters = parsing.compile_filter_list(properties.settings["filter-search"])
    return cj, filters
