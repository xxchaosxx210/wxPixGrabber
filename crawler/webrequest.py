import requests
import browser_cookie3
from http.cookiejar import CookieJar
from requests import Response
from dataclasses import dataclass
import crawler.cache as cache

FIREFOX_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0"


@dataclass
class UrlData:
    """
    url: the URL link of the source
    method: GET or POST method
    action: if POST FORM request then action will contain the URL
    data: contains POST data to send
    tag: can be either A or IMG
    """
    url: str
    method: str = "GET"
    action: str = ""
    data: dict = None
    tag: str = ""


def load_cookies(settings: dict) -> CookieJar:
    """Load Cookies from Installed Web Browser

    Args:
        settings (dict): The settings dict loaded from options.py

    Returns:
        object: cookiejar. Default CookieJar is used by default
    """
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


def request_from_url(url_data: UrlData, cj: CookieJar, settings: dict) -> Response:
    """sends a post or get request to Url

    Args:
        url_data (object): UrlData object which contains method (POST or GET) and url to request from
        cj (object): Cookie Jar. use load_cookies before using this function
        settings (dict): settings dict from options.py

    Raises:
        AttributeError: if url exists in the ignore database then raises this exception

    Returns:
        object: requests handle object (read requests pypi for more information onto how to use it)
    """
    # check the cache first before connecting
    if url_data.tag == "img":
        if cache.check_cache_for_image(url_data.url, settings):
            raise AttributeError("Url already exists in Cache")

    if url_data.method.lower() == "get":
        response = requests.get(url_data.url, cookies=cj, headers={"User-Agent": FIREFOX_USER_AGENT},
                                timeout=settings["connection_timeout"], data=url_data.data)
    elif url_data.method.lower() == "post":
        response = requests.post(url_data.url, cookies=cj, headers={"User-Agent": FIREFOX_USER_AGENT},
                                 timeout=settings["connection_timeout"], data=url_data.data)
    else:
        raise requests.exceptions.RequestsWarning("No Method Specified. Use either GET or POST")
    return response
