import requests
import browser_cookie3
from http.cookiejar import CookieJar

import cache

FIREFOX_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0"

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
    # check the cache first before connecting

    if urldata.tag == "img":
        if cache.check_cache_for_image(urldata.url, settings):
            raise AttributeError("Url already exists in Cache")

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
    return r