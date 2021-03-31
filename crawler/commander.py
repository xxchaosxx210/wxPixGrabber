import logging
import multiprocessing as mp
import threading
import queue

import crawler.cache as cache
import crawler.parsing as parsing
import crawler.options as options
import crawler.mime as mime
import crawler.message as const
from crawler.task import Task
from crawler.message import Message

from crawler.webrequest import (
    request_from_url,
    load_cookies,
    UrlData
)

_Log = logging.getLogger(__name__)

_QUEUE_TIMEOUT = 0.1


def _start_max_tasks(tasks: dict, max_tasks_to_start: int) -> int:
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
    for th in tasks.values():
        if counter >= max_tasks_to_start:
            break
        else:
            th.start()
            counter += 1
    return counter


def tasks_alive(tasks: dict) -> list:
    """checks how many tasks are still running

    Args:
        tasks (dict): The list of Tasks to check

    Returns:
        [list]: returns all active running tasks
    """
    return list(filter(lambda task: task.is_alive(), tasks.values()))


def _wake_tasks(tasks: dict):
    for task in tasks.values():
        if task.is_alive():
            task.msg_box.put("")


class Commander(mp.Process):

    def __init__(self, main_queue: mp.Queue):
        super().__init__()
        self.main_queue = main_queue
        self.queue = mp.Queue()
        self.settings = {}
        self.scanned_urls = {}
        self.blacklist = {}
        self.cancel_tasks = mp.Event()
        self.quit_thread = mp.Event()
        self.filters = None
        self.cookie_jar = None

    def _reset(self, tasks: dict):
        self.cancel_tasks.clear()
        tasks.clear()
        self.blacklist.clear()

    def message_main(self, message: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
            status=const.STATUS_OK, data={"message": message}))

    def message_quit(self):
        self.main_queue.put(
            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT))

    def message_start(self):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START))

    def fetch_complete_message(self, length: int, title: str):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER,
                    event=const.EVENT_FETCH_COMPLETE,
                    status=const.STATUS_OK,
                    data={"length": length, "title": title}))

    def fetch_update_message(self, index: int, url_data: UrlData):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER,
                    event=const.EVENT_FETCH,
                    data={"url_data": url_data, "index": index}))

    def fetch_start_message(self, title: str, url: str):
        self.main_queue.put_nowait(
            Message(thread=const.THREAD_COMMANDER,
                    event=const.EVENT_FETCH_START,
                    data={"title": title, "url": url}))

    def fetch_error_message(self, err: str, url: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH_COMPLETE, status=const.STATUS_ERROR,
            data={"message": err, "url": url}))

    def ignored_error_message(self, url: str, message: str):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH_COMPLETE, status=const.STATUS_IGNORED,
            data={"message": message, "url": url}))

    def message_complete(self):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_COMPLETE))

    def message_pause(self, pause: bool):
        self.main_queue.put_nowait(Message(
            thread=const.THREAD_COMMANDER, event=const.EVENT_PAUSE, data={"pause": pause}))

    def notify_cancel(self):
        self.main_queue.put_nowait(Message(thread=const.THREAD_COMMANDER, event=const.EVENT_CANCEL))

    def _check_blacklist(self, url_data: UrlData, task: Task):
        """
        This method gets called when a Task requests if a Url has already been searched from
        another Task.
        Args:
            url_data: the url to check
        """
        black_list_added = repr(url_data.__dict__) in self.blacklist
        if not black_list_added:
            self.blacklist[repr(url_data.__dict__)] = 1
        # flip the black_list_added boolean
        task.msg_box.put(Message(thread=const.THREAD_COMMANDER,
                                 event=const.EVENT_BLACKLIST,
                                 data={"added": not black_list_added}))

    def _init_start_tasks(self, tasks: dict):
        tasks.clear()
        self.blacklist.clear()
        self.settings = options.load_settings()
        self.cookie_jar = load_cookies(self.settings)
        self.filters = parsing.compile_filter_list(self.settings["filter-search"])

    def _init_fetch(self, tasks: dict, cancel_fetch: mp.Event):
        self.scanned_urls.clear()
        tasks.clear()
        cancel_fetch.clear()
        self.cancel_tasks.clear()
        self.settings = options.load_settings()
        self.cookie_jar = load_cookies(self.settings)

    def _search_html(self, html_doc: str, url: str, cancel_flag: mp.Event):
        soup = parsing.parse_html(html_doc)
        html_title = getattr(soup.find("title"), "text", "")
        options.assign_unique_name("", html_title)
        # Setup Search filters and find matches within forms, links and images
        self.filters = parsing.compile_filter_list(self.settings["filter-search"])
        # Notify the Main Process were starting the sort
        self.fetch_start_message(html_title, url)
        for scanned_index, url_data in enumerate(parsing.sort_soup(url=url,
                                                                   soup=soup,
                                                                   include_forms=False,
                                                                   images_only=False,
                                                                   thumbnails_only=self.settings.get("thumbnails_only",
                                                                                                     True),
                                                                   filters=self.filters,
                                                                   img_exts=self.settings["images_to_search"])):
            if url_data:
                self.scanned_urls[scanned_index] = url_data
                self.fetch_update_message(scanned_index, url_data)
            if cancel_flag.is_set():
                break
        self.fetch_complete_message(self.scanned_urls.__len__(), html_title)
        # call the commander process to set the fetch_running to False
        self.queue.put(Message(const.THREAD_MAIN, const.EVENT_FETCH_COMPLETE))
        if self.scanned_urls:
            if self.settings["auto-download"]:
                # Message ourselves and start the tasks
                self.queue.put_nowait(Message(thread=const.THREAD_MAIN, event=const.EVENT_START))
        else:
            self.message_main("No Links Found :(")

    def run(self):
        # create an ignore table in the sqlite file
        cache.initialize_ignore()
        # Notify main thread that Commander has started
        self.message_main("Commander thread has loaded. Waiting to scan")
        time_counter = 0.0
        task_running = False
        tasks = {}
        total_counter = 0
        paused = mp.Event()
        cancel_fetch = mp.Event()
        fetch_running = False
        while not self.quit_thread.is_set():
            try:
                if task_running:
                    msg = self.queue.get(timeout=_QUEUE_TIMEOUT)
                else:
                    msg = self.queue.get(timeout=None)

                if msg.thread == const.THREAD_MAIN:
                    if msg.event == const.EVENT_QUIT:
                        self.cancel_tasks.set()
                        self.message_quit()
                        self.quit_thread.set()

                    elif msg.event == const.EVENT_PAUSE:
                        if paused.is_set():
                            # Unpause any running tasks
                            paused.clear()
                            _wake_tasks(tasks)
                        else:
                            # Pause all tasks
                            paused.set()
                        self.message_pause(paused.is_set())

                    elif msg.event == const.EVENT_START:
                        if not task_running:
                            time_counter = 0.0
                            task_running = True
                            self._init_start_tasks(tasks)
                            for task_index, url_data in enumerate(self.scanned_urls.values()):
                                tasks[task_index] = Task(task_index,
                                                         url_data,
                                                         self.settings,
                                                         self.filters,
                                                         self.queue,
                                                         self.cancel_tasks,
                                                         paused)
                            total_counter = _start_max_tasks(tasks, self.settings["max_connections"])
                            if total_counter > 0:
                                # notify main thread so can initialize UI
                                self.message_start()
                            else:
                                task_running = False
                                self.message_main("Could not start Tasks")

                    elif msg.event == const.EVENT_FETCH_CANCEL:
                        if fetch_running:
                            cancel_fetch.set()

                    elif msg.event == const.EVENT_FETCH_COMPLETE:
                        fetch_running = False

                    elif msg.event == const.EVENT_FETCH:
                        if not task_running and not fetch_running:
                            self._init_fetch(tasks, cancel_fetch)
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
                                    fetch_running = True
                                    threading.Thread(target=self._search_html,
                                                     kwargs={"html_doc": fetch_response.text,
                                                             "url": msg.data["url"],
                                                             "cancel_flag": cancel_fetch}).start()
                                fetch_response.close()
                            except Exception as err:
                                # couldn't connect
                                fetch_running = False
                                self.fetch_error_message(err.__str__(), msg.data["url"])
                        else:
                            self.ignored_error_message(msg.data["url"], "Tasks still running")

                    elif msg.event == const.EVENT_CANCEL:
                        if task_running:
                            if paused.is_set():
                                # if paused then wake threads up
                                _wake_tasks(tasks)
                                paused.clear()
                                self.message_pause(paused.is_set())
                            self.cancel_tasks.set()
                            self.notify_cancel()

                elif msg.thread == const.THREAD_SERVER:
                    if msg.event == const.EVENT_SERVER_READY:
                        if not task_running and not fetch_running:
                            fetch_running = True
                            self._init_fetch(tasks, cancel_fetch)
                            threading.Thread(target=self._search_html,
                                             kwargs={"html_doc": msg.data["html"],
                                                     "url": "pixgrabber-extension",
                                                     "cancel_flag": cancel_fetch}).start()

                elif msg.thread == const.THREAD_TASK:
                    if msg.event == const.EVENT_FINISHED:
                        # one task is gone start another
                        if total_counter < self.scanned_urls.__len__():
                            if not self.cancel_tasks.is_set():
                                # start the next task if not cancelled and increment the total_counter
                                tasks.get(total_counter).start()
                                total_counter += 1
                            else:
                                # if cancel flag been set the total_counter to its limit and this will force a Task
                                # Complete
                                total_counter = self.scanned_urls.__len__()
                        # Pass the Task Finished event to the Main Thread
                        self.main_queue.put_nowait(msg)
                    elif msg.event == const.EVENT_BLACKLIST:
                        self._check_blacklist(msg.data["urldata"], tasks.get(msg.data["index"]))
                    else:
                        self.main_queue.put_nowait(msg)
            except queue.Empty:
                pass
            finally:
                if task_running:
                    # check if all self.tasks are finished and that the task total_counter is greater or
                    # equal to the size of task tasks. if so cleanup and notify main thread
                    if len(tasks_alive(tasks)) == 0 and total_counter >= self.scanned_urls.__len__():
                        self.message_complete()
                        self._reset(tasks)
                        task_running = False
                    else:
                        # cancel flag is set. Start counting to timeout, then start terminating processing
                        if self.cancel_tasks.is_set():
                            if time_counter >= self.settings["connection_timeout"]:
                                # kill any hanging tasks
                                for task in tasks.values():
                                    if task.is_alive():
                                        del task
                                        total_counter += 1
                            else:
                                time_counter += _QUEUE_TIMEOUT
