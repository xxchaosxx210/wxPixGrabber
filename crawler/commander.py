import threading
import logging
import multiprocessing as mp
import queue
from dataclasses import dataclass

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
class CommanderProperties:
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


def _reset_comm_props(properties: CommanderProperties):
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
        threading.Thread(target=_thread, kwargs={"main_queue": main_queue, "msgbox": msg_queue}),
        msg_queue)


def _init_start(properties: CommanderProperties) -> tuple:
    # initialize commander threads variables and return new objects
    properties.tasks = []
    properties.task_running = 1
    properties.blacklist.clear()
    properties.settings = options.load_settings()
    cj = load_cookies(properties.settings)
    filters = parsing.compile_filter_list(properties.settings["filter-search"])
    return cj, filters


def _start_tasks(props: CommanderProperties) -> int:
    cookiejar, filters = _init_start(props)

    for task_index, url_data in enumerate(props.scanned_urls):
        task = Task(task_index, url_data, props.settings,
                    filters, msgbox, props.cancel_all)
        props.tasks.append(task)

    # reset the tasks counter this is used to keep track of
    # tasks that have been  started once a running thread has been notified
    # this thread counter is incremented counter is checked with length of props.tasks
    # once the counter has reached length then then all tasks have been complete
    max_connections = props.settings["max_connections"]
    props.counter = _start_max_tasks(props.tasks, max_connections)
    return props.counter


def _thread(main_queue: mp.Queue, msgbox: mp.Queue):
    """main task handler thread

    Args:
        main_queue (object): atomic Queue object used to send messages to main thread
        msgbox (object): the atomic Queue object to receive messages from
    """
    # create an ignore table in the sqlite file
    cache.initialize_ignore()

    main_queue.put_nowait(Message(
        thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
        data={"message": "Commander thread has loaded. Waiting to scan"}))

    props = CommanderProperties(settings={}, scanned_urls=[], blacklist=Blacklist(),
                                counter=0, cancel_all=mp.Event(), task_running=0,
                                tasks=[], quit_thread=mp.Event(), time_counter=0.0)

    while not props.quit_thread.is_set():
        try:
            if props.task_running:
                r = msgbox.get(timeout=_QUEUE_TIMEOUT)
            else:
                r = msgbox.get(timeout=None)
            if r.thread == const.THREAD_MAIN:
                if r.event == const.EVENT_QUIT:
                    props.cancel_all.set()
                    main_queue.put(
                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT, data={}))
                    props.quit_thread.set()
                elif r.event == const.EVENT_START:
                    if not props.task_running:
                        cookiejar, filters = _init_start(props)

                        for task_index, url_data in enumerate(props.scanned_urls):
                            task = Task(task_index, url_data, props.settings,
                                        filters, msgbox, props.cancel_all)
                            props.tasks.append(task)

                        # reset the tasks counter this is used to keep track of
                        # tasks that have been  started once a running thread has been notified
                        # this thread counter is incremented counter is checked with length of props.tasks
                        # once the counter has reached length then then all tasks have been complete
                        max_connections = props.settings["max_connections"]
                        props.counter = _start_max_tasks(props.tasks, max_connections)
                        # notify main thread so can initialize UI
                        main_queue.put_nowait(
                            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START, data={}))
                elif r.event == const.EVENT_FETCH:
                    if not props.task_running:
                        props.cancel_all.clear()
                        props.settings = options.load_settings()
                        cookiejar = load_cookies(props.settings)
                        url_data = UrlData(r.data["url"], method="GET")
                        main_queue.put_nowait(Message(
                            thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                            data={"message": f"Connecting to {r.data['url']}..."}))
                        try:
                            try:
                                fetch_response = options.load_from_file(r.data["url"])
                            except FileNotFoundError:
                                fetch_response = request_from_url(url_data, cookiejar, props.settings)
                            ext = mime.is_valid_content_type(r.data["url"],
                                                             fetch_response.headers["Content-Type"],
                                                             props.settings["images_to_search"])
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
                                props.scanned_urls = []
                                # find images and links
                                # set the include_form to False on level 1 scan
                                # compile our filter matches only add those from the filter list
                                filters = parsing.compile_filter_list(props.settings["filter-search"])
                                if parsing.sort_soup(url=r.data["url"], soup=soup,
                                                     urls=props.scanned_urls,
                                                     include_forms=False,
                                                     images_only=False,
                                                     thumbnails_only=props.settings.get("thumbnails_only", True),
                                                     filters=filters) > 0:
                                    main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                                data={"urls": props.scanned_urls,
                                                      "title": html_title,
                                                      "url": r.data["url"]}))
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
                    if props.task_running == 0:
                        # Initialize and load settings
                        props.cancel_all.clear()
                        props.scanned_urls = []
                        props.settings = options.load_settings()
                        # Parse the HTML sent from the Server and assign a unique Path name if required
                        soup = parsing.parse_html(r.data["html"])
                        html_title = getattr(soup.find("title"), "text", "")
                        options.assign_unique_name("", html_title)
                        # Setup Search filters and find matches within forms, links and images
                        filters = parsing.compile_filter_list(props.settings["filter-search"])
                        if parsing.sort_soup(url=r.data["url"], soup=soup,
                                             urls=props.scanned_urls, include_forms=False, images_only=False,
                                             thumbnails_only=props.settings.get("thumbnails_only", True),
                                             filters=filters) > 0:
                            main_queue.put_nowait(
                                Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH,
                                        data={"urls": props.scanned_urls, "title": html_title, "url": r.data["url"]}))
                            # Message ourselves and start the search
                            msgbox.put_nowait(
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
