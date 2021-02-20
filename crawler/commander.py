import functools
import threading
import logging
import multiprocessing as mp
import queue
from dataclasses import dataclass

import crawler.cache as cache
import crawler.parsing as parsing
import crawler.options as options
import crawler.mime as mime

from crawler.task import Grunt

from crawler.types import (
    Message,
    Blacklist,
    Stats,
    UrlData
)

from crawler.webrequest import (
    request_from_url,
    load_cookies
)

_Log = logging.getLogger(__name__)


@dataclass
class Commander:
    thread: threading.Thread
    queue: mp.Queue


def _add_stats(stats, data):
    stats.saved += data["saved"]
    stats.errors += data["errors"]
    stats.ignored += data["ignored"]
    return stats

def tasks_alive(tasks):
    """
    returns a list of tasks that are still alive
    """
    return list(filter(lambda grunt : grunt.is_alive(), tasks))

def _reset_comm_props(properties):
    properties.cancel_all.clear()
    properties.tasks = []
    properties.task_running = False
    properties.blacklist.clear()
    properties.time_counter = 0.0

def _start_max_tasks(tasks, max_tasks, counter):
    for th in tasks:
        if counter >= max_tasks:
            break
        else:
            th.start()
            counter += 1
    return counter

def create_commander(callback):
    """main handler for starting and keeping track of worker tasks

    Args:
        callback (function): function callback to respond to the main thread

    Returns:
        [object]: returns a Commander dataclass 
    """
    msgqueue = mp.Queue()
    return Commander(
        threading.Thread(target=_thread, kwargs={"callback": callback, "msgbox": msgqueue}),
        msgqueue)

def _thread(callback, msgbox):
    """main task handler thread

    Args:
        callback (function): The function callback to the main thread
        msgbox (object): the atomic Queue object to recieve messages from
    """
    # create an ignore table in the sqlite file
    cache.initialize_ignore()
    MessageMain = functools.partial(Message, thread="commander", type="message")
    FetchError = functools.partial(Message, thread="commander", type="fetch", status="error")

    callback(MessageMain(data={"message": "Commander thread has loaded. Waiting to scan"}))

    @dataclass
    class Properties:
        settings: dict
        scanned_urls: list
        counter: int = 0
        blacklist: Blacklist = None
        cancel_all: mp.Event = None
        task_running: bool = False
        tasks: list = None
        quit_thread: mp.Event = None
        time_counter: float = 0.0
    
    props = Properties(settings={}, scanned_urls=[], blacklist=Blacklist(), cancel_all=mp.Event(),
                       tasks=[], quit_thread=mp.Event())
    
    QUEUE_TIMEOUT = 0.1

    while not props.quit_thread.is_set():
        try:
            if props.task_running:
                r = msgbox.get(timeout=QUEUE_TIMEOUT)
            else:
                r = msgbox.get(timeout=None)
            if r.thread == "main":
                if r.type == "quit":
                    props.cancel_all.set()
                    callback(Message(thread="commander", type="quit"))
                    props.quit_thread.set()
                elif r.type == "start":
                    if not props.task_running:
                        props.tasks = []
                        props.task_running = True
                        stats = Stats()
                        props.blacklist.clear()
                        # load the settings from file
                        # create a new instance of it in memory
                        # we dont want these values to change
                        # whilst downloading and saving to file
                        props.settings = dict(options.load_settings())
                        cookiejar = load_cookies(props.settings)
                        # notify main thread so can intialize UI
                        callback(MessageMain(type="searching", status="start"))
                        filters = parsing.compile_filter_list(props.settings["filter-search"]["filters"])
                        _Log.info("Search Filters loaded")
                        for task_index, urldata in enumerate(props.scanned_urls):
                            grunt = Grunt(task_index, urldata, props.settings, 
                                          filters, msgbox, props.cancel_all)
                            props.tasks.append(grunt)
                        
                        _Log.info(f"Tasks loaded - {len(props.tasks)} tasks")
                            
                        # reset the tasks counter this is used to keep track of
                        # tasks that have been  started once a running thread has been notified
                        # this thread counter is incremenetet counter is checked with length of props.tasks
                        # once the counter has reached length then then all tasks have been complete
                        props.counter = 0
                        max_connections = round(int(props.settings["max_connections"]))
                        props.counter = _start_max_tasks(props.tasks, max_connections, props.counter)

                        _Log.info(
                            f"""Process Counter set to 0. Max Connections = \
                                {max_connections}. Current running tasks = {len(tasks_alive(props.tasks))}""")

                elif r.type == "fetch":                
                    if not props.task_running:
                        props.cancel_all.clear()
                        # Load settings
                        callback(Message(thread="commander", type="fetch", status="started"))
                        # Load the settings
                        props.settings = options.load_settings()
                        # get the document from the URL
                        callback(MessageMain(data={"message": f"Connecting to {r.data['url']}"}))
                        # Load the cookiejar
                        cookiejar = load_cookies(props.settings)
                        urldata = UrlData(r.data["url"], method="GET")
                        try:
                            webreq = options.load_from_file(r.data["url"])
                            if not webreq:
                                webreq = request_from_url(urldata, cookiejar, props.settings)
                            ext = mime.is_valid_content_type(
                                                             r.data["url"], 
                                                             webreq.headers["Content-Type"], 
                                                             props.settings["images_to_search"])
                            if ext == mime.EXT_HTML:
                                html_doc = webreq.text
                                # parse the html
                                soup = parsing.parse_html(html_doc)
                                # get the url title
                                # amd add a unique path name to the save path
                                html_title = getattr(soup.find("title"), "text", "")
                                options.assign_unique_name(
                                    webreq.url, html_title)
                                # scrape links and images from document
                                props.scanned_urls = []
                                # find images and links
                                # set the include_form to False on level 1 scan
                                # compile our filter matches only add those from the filter list
                                filters = parsing.compile_filter_list(props.settings["filter-search"]["filters"])
                                if parsing.sort_soup(url=r.data["url"],
                                                     soup=soup, 
                                                     urls=props.scanned_urls,
                                                     include_forms=False,
                                                     images_only=False, 
                                                     thumbnails_only=True,
                                                     filters=filters) > 0:
                                    callback(
                                        Message(thread="commander", type="fetch", 
                                                     status="finished", data={"urls": props.scanned_urls,
                                                     "title": html_title}))
                                else:
                                    # Nothing found notify main thread
                                    callback(MessageMain(data={"message": "No links found :("}))
                            webreq.close()
                        except Exception as err:
                            _Log.error(f"Commander web request failed - ")
                            callback(FetchError(data={"message": f"{str(err)}"}))
                    else:
                        callback(FetchError(data={"message": "Tasks still running"}))

                elif r.type == "cancel":
                    props.cancel_all.set()

            elif r.thread == "grunt":
                if r.type == "finished":
                    # one grunt is gone start another
                    if props.counter < len(props.tasks):
                        if not props.cancel_all.is_set():
                            props.tasks[props.counter].start()
                        else:
                            props.tasks[props.counter].run()
                        props.counter += 1
                        _Log.info(f"TASK#{r.id} is {r.status}")
                        if r.status == "complete":
                            callback(r)
                elif r.type == "stat-update":
                    # add stats up and notify main thread
                    _add_stats(stats, r.data)
                    callback(Message(thread="commander", 
                                     type="stat-update", data={"stats": stats}))
                elif r.type == "blacklist":
                    # check the props.blacklist with urldata and notify Grunt process
                    # if no duplicate and added then True returned
                    process_index = r.data["index"]
                    grunt = props.tasks[process_index]
                    if not props.blacklist.exists(r.data["urldata"]):
                        props.blacklist.add(r.data["urldata"])
                        blacklist_added = True
                    else:
                        blacklist_added = False
                    grunt.msgbox.put(Message(
                        thread="commander", type="blacklist",
                        status=blacklist_added
                    ))
                else:
                    # something pass onto main thread
                    callback(r)
                    
            elif r.thread == "settings":
                callback(MessageMain(data=r.data))

        except queue.Empty:
            pass

        finally:
            if props.task_running:
                # check if all props.tasks are finished
                # and that the grunt props.counter is greater or
                # equal to the size of grunt tasks 
                # if so cleanup
                # and notify main thread
                if len(tasks_alive(props.tasks)) == 0 and props.counter >= len(props.tasks):
                    callback(Message(thread="commander", type="complete"))
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
                            props.time_counter += QUEUE_TIMEOUT