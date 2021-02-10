import requests
import browser_cookie3
from urllib3.connection import HTTPConnection
from http.cookiejar import CookieJar

import threading

FIREFOX_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0"

class Urls:

    """
    thread safe container class for storing global links
    this is to check there arent duplicate links
    saves a lot of time and less scraping
    """

    links = []
    images = []
    lock = threading.Lock()

    @staticmethod
    def clear():
        Urls.lock.acquire()
        Urls.links.clear()
        Urls.images.clear()
        Urls.lock.release()
    
    @staticmethod
    def add_image_url(url):
        Urls.lock.acquire()
        Urls.images.append(url)
        Urls.lock.release()
    
    @staticmethod
    def image_url_exists(url):
        Urls.lock.acquire()
        try:
            index = Urls.images.index(url)
        except ValueError:
            index = -1
        Urls.lock.release()
        return index >= 0

    @staticmethod
    def add_url(url):
        Urls.lock.acquire()
        Urls.links.append(url)
        Urls.lock.release()
    
    @staticmethod
    def url_exists(url):
        Urls.lock.acquire()
        try:
            index = Urls.links.index(url)
        except ValueError:
            index = -1
        Urls.lock.release()
        return index >= 0


def load_cookies(settings):
    cookies = settings["cookies"]
    if cookies["firefox"]:
        cj = browser_cookie3.firefox()
    elif cookies["chrome"]:
        cj = browser_cookie3.chrome()
    elif cookies["opera"]:
        cj = browser_cookie3.opera()
    elif cookies["edge"]:
        cj = browser_cookie3.edge()
    else:
        cj = CookieJar()
    return cj

def request_from_url(urldata, cj, settings):
    """
    request_from_url(str)

    gets the request from url and returns the requests object
    """
    try:
        if urldata.method.lower() == "get":
            r = requests.get(urldata.url, 
                             cookies=cj, 
                             headers={"User-Agent": FIREFOX_USER_AGENT},
                             timeout=settings["connection_timeout"],
                             data=urldata.data)
        elif urldata.method.lower() == "post":
            # Post request
            r = requests.post(urldata.url, 
                             cookies=cj, 
                             headers={"User-Agent": FIREFOX_USER_AGENT},
                             timeout=settings["connection_timeout"],
                             data=urldata.data)
        else:
            r = None
    except Exception as err:
        print(f"[EXCEPTION]: request_from_url, {urldata}, {err.__str__()}")
        r = None
    return r