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

from crawler.webrequest import (
    request_from_url,
    load_cookies,
    UrlData
)

_Log = logging.getLogger(__name__)

_QUEUE_TIMEOUT = 0.1


def _start_max_tasks(tasks: list, max_tasks_to_start: int) -> int:
    """
    Start the Process Pool by Max Connections
    Args:
        tasks:
        max_tasks_to_start:

    Returns:
        int: the amount of tasks started
    """
    # start the Process Pool
    # returns an integer to how many Tasks have been started
    counter = 0
    for th in tasks:
        if counter >= max_tasks_to_start:
            break
        else:
            th.start()
            counter += 1
    return counter


def tasks_alive(tasks: list) -> list:
    """checks how many tasks are still running

    Args:
        tasks (list): The list of Tasks to check

    Returns:
        [list]: returns all active running tasks
    """
    return list(filter(lambda task: task.is_alive(), tasks))


class Commander(threading.Thread):

    def __init__(self, main_queue: mp.Queue):
        super().__init__()
        self.main_queue = main_queue
        self.queue = mp.Queue()
        self.settings = {}
        self.scanned_urls = {}
        self.blacklist = {}
        self.cancel_all = mp.Event()
        self.tasks = []
        self.quit_thread = mp.Event()
        self.filters = None
        self.cookie_jar = None

    def _reset(self):
        self.cancel_all.clear()
        self.tasks.clear()
        self.blacklist.clear()

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
        """
        This method gets called when a Task requests if a Url has already been searched from
        another Task.
        Args:
            url_data: the url to check
            task_index: The index of the task
        """
        black_list_added = repr(url_data.__dict__) in self.blacklist
        if not black_list_added:
            self.blacklist[repr(url_data.__dict__)] = 1
        task = self.tasks[task_index]
        # flip the black_list_added boolean
        task.msgbox.put(Message(thread=const.THREAD_COMMANDER,
                                event=const.EVENT_BLACKLIST,
                                data={"added": not black_list_added}))

    def _init_start_tasks(self):
        self.tasks = []
        self.blacklist.clear()
        self.settings = options.load_settings()
        self.cookie_jar = load_cookies(self.settings)
        self.filters = parsing.compile_filter_list(self.settings["filter-search"])

    def _init_fetch(self):
        self.scanned_urls = {}
        self.tasks = []
        self.cancel_all.clear()
        self.settings = options.load_settings()
        self.cookie_jar = load_cookies(self.settings)

    def _search_html(self, html_doc: str, url: str):
        soup = parsing.parse_html(html_doc)
        html_title = getattr(soup.find("title"), "text", "")
        options.assign_unique_name("", html_title)
        # Setup Search filters and find matches within forms, links and images
        self.filters = parsing.compile_filter_list(self.settings["filter-search"])
        self.scanned_urls = parsing.sort_soup(url=url,
                                              soup=soup,
                                              include_forms=False,
                                              images_only=False,
                                              thumbnails_only=self.settings.get("thumbnails_only", True),
                                              filters=self.filters)
        if self.scanned_urls:
            self.message_fetch_ok(html_title, url)
            if self.settings["auto-download"]:
                # Message ourselves and start the tasks
                self.queue.put_nowait(
                    Message(thread=const.THREAD_MAIN, event=const.EVENT_START, data={}))
        else:
            self.message_main("No Links Found :(")

    def run(self):
        # create an ignore table in the sqlite file
        cache.initialize_ignore()
        # Notify main thread that Commander has started
        self.message_main("Commander thread has loaded. Waiting to scan")
        time_counter = 0.0
        task_running = False
        counter = 0
        while not self.quit_thread.is_set():
            try:
                if task_running:
                    msg = self.queue.get(timeout=_QUEUE_TIMEOUT)
                else:
                    msg = self.queue.get(timeout=None)

                if msg.thread == const.THREAD_MAIN:
                    if msg.event == const.EVENT_QUIT:
                        self.cancel_all.set()
                        self.message_quit()
                        self.quit_thread.set()

                    elif msg.event == const.EVENT_START:
                        if not task_running:
                            time_counter = 0.0
                            task_running = True
                            self._init_start_tasks()
                            for task_index, url_data in enumerate(self.scanned_urls.values()):
                                self.tasks.append(Task(task_index, url_data, self.settings,
                                                       self.filters, self.queue, self.cancel_all))
                            counter = _start_max_tasks(self.tasks, self.settings["max_connections"])
                            if counter > 0:
                                # notify main thread so can initialize UI
                                self.message_start()
                            else:
                                task_running = False
                                self._reset()
                                self.message_main("Could not start Tasks")

                    elif msg.event == const.EVENT_FETCH:
                        if not task_running:
                            self._init_fetch()
                            url_data = UrlData(msg.data["url"], method="GET")
                            self.message_main(f"Connecting to {msg.data['url']}...")
                            try:
                                try:
                                    fetch_response = options.load_from_file(msg.data["url"])
                                except FileNotFoundError:
                                    fetch_response = request_from_url(url_data, self.cookie_jar, self.settings)
                                ext = mime.is_valid_content_type(msg.data["url"],
                                                                 fetch_response.headers["Content-Type"],
                                                                 self.settings["images_to_search"])
                                if ext == mime.EXT_HTML:
                                    self._search_html(fetch_response.text, msg.data["url"])
                                fetch_response.close()
                            except Exception as err:
                                # couldn't connect
                                self.message_fetch_error(err.__str__(), msg.data["url"])
                        else:
                            self.message_fetch_ignored(msg.data["url"], "Tasks still running")

                    elif msg.event == const.EVENT_CANCEL:
                        self.cancel_all.set()

                elif msg.thread == const.THREAD_SERVER:
                    if msg.event == const.EVENT_SERVER_READY:
                        if not task_running:
                            self._init_fetch()
                            self._search_html(msg.data["html"], "pixgrabber-extension")

                elif msg.thread == const.THREAD_TASK:
                    if msg.event == const.EVENT_FINISHED:
                        # one task is gone start another
                        if counter < len(self.tasks):
                            if not self.cancel_all.is_set():
                                # start the next task if not cancelled and increment the counter
                                self.tasks[counter].start()
                                counter += 1
                            else:
                                # if cancel flag been set the counter to its limit and this will force a Task Complete
                                counter = len(self.tasks)
                        # Pass the Task Finished event to the Main Thread
                        self.main_queue.put_nowait(msg)
                    elif msg.event == const.EVENT_BLACKLIST:
                        self._check_blacklist(msg.data["urldata"], msg.data["index"])
                    else:
                        self.main_queue.put_nowait(msg)
            except queue.Empty:
                pass
            finally:
                if task_running:
                    # check if all self.tasks are finished and that the task counter is greater or
                    # equal to the size of task tasks. if so cleanup and notify main thread
                    if len(tasks_alive(self.tasks)) == 0 and counter >= len(self.tasks):
                        self.message_complete()
                        self._reset()
                        task_running = False
                    else:
                        # cancel flag is set. Start counting to timeout, then start terminating processing
                        if self.cancel_all.is_set():
                            if time_counter >= self.settings["connection_timeout"]:
                                # kill any hanging tasks
                                for task in self.tasks:
                                    if task.is_alive():
                                        task.terminate()
                                        counter += 1
                            else:
                                time_counter += _QUEUE_TIMEOUT

