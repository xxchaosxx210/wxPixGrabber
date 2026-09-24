import time
import requests
import browser_cookie3
from http.cookiejar import CookieJar
from requests import Response
from dataclasses import dataclass
import crawler.cache as cache
from crawler.diagnostics import get_logger

FIREFOX_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0"

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = (1, 2)

_Log = get_logger("webrequest")


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


def _send_request(url_data: UrlData, cj: CookieJar, settings: dict) -> Response:
    """Send one HTTP request without retrying."""
    method = url_data.method.lower()
    request_args = {
        "cookies": cj,
        "headers": {"User-Agent": FIREFOX_USER_AGENT},
        "timeout": settings["connection_timeout"],
        "data": url_data.data
    }

    if method == "get":
        return requests.get(url_data.url, **request_args)
    elif method == "post":
        return requests.post(url_data.url, **request_args)

    raise requests.exceptions.RequestsWarning("No Method Specified. Use either GET or POST")


def request_from_url(url_data: UrlData, cj: CookieJar, settings: dict) -> Response:
    """Send a request and retry temporary network/server failures.

    Successful requests are not delayed. Retries only happen for connection
    failures/timeouts or temporary HTTP responses such as 429/5xx errors.

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

    method = url_data.method.lower()
    _Log.info("REQUEST method=%s url=%s", method.upper(), url_data.url)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = _send_request(url_data, cj, settings)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            if attempt < MAX_RETRIES:
                delay = RETRY_BACKOFF_SECONDS[attempt]
                _Log.warning(
                    "REQUEST_RETRY attempt=%s/%s delay=%ss method=%s url=%s error=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                    method.upper(),
                    url_data.url,
                    err
                )
                time.sleep(delay)
                continue

            _Log.error("REQUEST_FAILED method=%s url=%s error=%s", method.upper(), url_data.url, err)
            raise
        except Exception as err:
            _Log.error("REQUEST_FAILED method=%s url=%s error=%s", method.upper(), url_data.url, err)
            raise

        _Log.info(
            "RESPONSE status=%s content_type=%s requested_url=%s final_url=%s redirects=%s",
            response.status_code,
            response.headers.get("Content-Type", ""),
            url_data.url,
            response.url,
            len(response.history)
        )

        if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF_SECONDS[attempt]
            _Log.warning(
                "HTTP_RETRY attempt=%s/%s delay=%ss status=%s url=%s",
                attempt + 1,
                MAX_RETRIES,
                delay,
                response.status_code,
                response.url
            )
            response.close()
            time.sleep(delay)
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            _Log.error(
                "HTTP_ERROR status=%s requested_url=%s final_url=%s error=%s",
                response.status_code,
                url_data.url,
                response.url,
                err
            )
            response.close()
            raise

        return response

    raise requests.exceptions.RequestException("Request failed after retries")
