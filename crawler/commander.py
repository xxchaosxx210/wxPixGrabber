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

from crawler.constants import CStats as Stats
from crawler.constants import CMessage as Message
from crawler.constants import CommanderProperties
import crawler.constants as const

from crawler.types import (
    Blacklist,
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
    properties.task_running = 0
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

def create_commander(main_queue):
    """main handler for starting and keeping track of worker tasks

    Args:
        main_queue (object): atomic Queue object used to send messages to main thread

    Returns:
        [object]: returns a Commander dataclass 
    """
    msgqueue = mp.Queue()
    return Commander(
        threading.Thread(target=_thread, kwargs={"main_queue": main_queue, "msgbox": msgqueue}),
        msgqueue)

def _init_start(properties):
    properties.tasks = []
    properties.task_running = 1
    properties.blacklist.clear()
    properties.settings = options.load_settings()
    cj = load_cookies(properties.settings)
    filters = parsing.compile_filter_list(properties.settings["filter-search"]["filters"])
    return (Stats(), cj, filters)

def _thread(main_queue, msgbox):
    """main task handler thread

    Args:
        main_queue (object): atomic Queue object used to send messages to main thread
        msgbox (object): the atomic Queue object to recieve messages from
    """
    # create an ignore table in the sqlite file
    cache.initialize_ignore()

    main_queue.put_nowait(Message(
        thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
        status=const.STATUS_OK, id=0,
        data={"message": "Commander thread has loaded. Waiting to scan"}))
    
    props = CommanderProperties(settings={}, scanned_urls=[], blacklist=Blacklist(), cancel_all=mp.Event(),
                       tasks=[], quit_thread=mp.Event())
    
    QUEUE_TIMEOUT = 0.1

    while not props.quit_thread.is_set():
        try:
            if props.task_running:
                r = msgbox.get(timeout=QUEUE_TIMEOUT)
            else:
                r = msgbox.get(timeout=None)
            if r.thread == const.THREAD_MAIN:
                if r.event == const.EVENT_QUIT:
                    props.cancel_all.set()
                    main_queue.put(Message(thread=const.THREAD_COMMANDER, event=const.EVENT_QUIT, status=const.STATUS_OK,
                                   id=0, data=None))
                    props.quit_thread.set()
                elif r.event == const.EVENT_START:
                    if not props.task_running:        
                        stats, cookiejar, filters = _init_start(props)
                    
                        for task_index, urldata in enumerate(props.scanned_urls):
                            grunt = Grunt(task_index, urldata, props.settings, 
                                          filters, msgbox, props.cancel_all)
                            props.tasks.append(grunt)
                            
                        # reset the tasks counter this is used to keep track of
                        # tasks that have been  started once a running thread has been notified
                        # this thread counter is incremenetet counter is checked with length of props.tasks
                        # once the counter has reached length then then all tasks have been complete
                        props.counter = 0
                        max_connections = round(int(props.settings["max_connections"]))
                        props.counter = _start_max_tasks(props.tasks, max_connections, props.counter)
                        # notify main thread so can intialize UI
                        main_queue.put_nowait(
                            Message(thread=const.THREAD_COMMANDER, event=const.EVENT_START, id=0, status=const.STATUS_OK,
                                    data=None))
                elif r.event == const.EVENT_FETCH:
                    if not props.task_running:
                        props.cancel_all.clear()
                        props.settings = options.load_settings()
                        cookiejar = load_cookies(props.settings)
                        urldata = UrlData(r.data["url"], method="GET")
                        main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_MESSAGE,
                                status=const.STATUS_OK, id=0, data={"message": f"Connecting to {r.data['url']}..."}))
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
                                    main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, 
                                                     status=const.STATUS_OK, id=0, data={"urls": props.scanned_urls,
                                                     "title": html_title}))
                                else:
                                    main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, id=0, data={"message": "No Links Found :("}, status=const.STATUS_OK,
                                                event=const.EVENT_MESSAGE))
                            webreq.close()
                        except Exception as err:
                            _Log.error(f"Commander web request failed - ")
                            main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_ERROR,
                                id=0, data={"message": err.__str__()}))
                    else:
                        main_queue.put_nowait(Message(
                                thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, status=const.STATUS_ERROR,
                                id=0, data={"message": "Tasks still running"}))

                elif r.event == const.EVENT_CANCEL:
                    props.cancel_all.set()
            
            elif r.thread == const.THREAD_SERVER:
                if r.event == const.EVENT_SERVER_READY:
                    if props.task_running == 0:
                        props.cancel_all.clear()
                        props.settings = options.load_settings()
                        soup = parsing.parse_html(r.data["html"])
                        props.scanned_urls = []
                        html_title = getattr(soup.find("title"), "text", "")
                        options.assign_unique_name("", html_title)
                        filters = parsing.compile_filter_list(props.settings["filter-search"]["filters"])
                        if parsing.sort_soup(url=r.data["url"], soup=soup, 
                                             urls=props.scanned_urls, include_forms=False,
                                             images_only=False, thumbnails_only=True, filters=filters) > 0:
                            main_queue.put_nowait(
                                        Message(thread=const.THREAD_COMMANDER, event=const.EVENT_FETCH, 
                                                     status=const.STATUS_OK, id=0, data={"urls": props.scanned_urls,
                                                     "title": html_title}))
                            # Start the scan
                            msgbox.put_nowait(
                                Message(thread=const.THREAD_MAIN, event=const.EVENT_START, 
                                status=const.STATUS_OK, data=None, id=0))                         
                        else:
                            # Nothing found notify main thread
                            main_queue.put_nowait(
                                Message(thread=const.THREAD_COMMANDER, id=0, data={"message": "No Links Found :("}, status=const.STATUS_OK,
                                        event=const.EVENT_MESSAGE))


            elif r.thread == const.THREAD_TASK:
                if r.event == const.EVENT_FINISHED:
                    # one grunt is gone start another
                    if props.counter < len(props.tasks):
                        if not props.cancel_all.is_set():
                            props.tasks[props.counter].start()
                        else:
                            props.tasks[props.counter].run()
                        props.counter += 1
                        _Log.info(f"TASK#{r.id} is {r.status}")
                        if r.status == const.STATUS_OK:
                            main_queue.put_nowait(r)
                elif r.event == const.EVENT_STAT_UPDATE:
                    # add stats up and notify main thread
                    _add_stats(stats, r.data)
                    main_queue.put_nowait(Message(thread=const.THREAD_COMMANDER, 
                                     event=const.EVENT_STAT_UPDATE, id=0, status=const.STATUS_OK,
                                     data={"stats": stats}))
                elif r.event == const.EVENT_BLACKLIST:
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
                        thread=const.THREAD_COMMANDER, event=const.EVENT_BLACKLIST,
                        status=const.STATUS_OK, data={"added": blacklist_added}, id=0
                    ))
                else:
                    # something pass onto main thread
                    main_queue.put_nowait(r)
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
                    main_queue.put_nowait(Message(
                        thread=const.THREAD_COMMANDER, event=const.EVENT_COMPLETE,
                        id=0, status=const.STATUS_OK, data=None))
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