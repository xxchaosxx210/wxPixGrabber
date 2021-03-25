import re
from urllib import parse
from bs4.element import Tag
from bs4 import BeautifulSoup
import logging
from typing import Pattern

from crawler.webrequest import UrlData
from crawler.mime import image_ext_pattern

_Log = logging.getLogger(__name__)

url_pattern = re.compile(
    r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+['
    r'a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})')


def compile_filter_list(filter_settings: dict) -> Pattern:
    """compiles a filter list into a regular expression pattern.
    Call this before, calling sort soup

    Args:
        filter_settings (dict): holds keys -
                                enabled (bool): if this is enabled then filters list is compiled and used else a wildcard expression will be used instead
                                filters (list): a list of words to add to the search pattern

    Returns:
        [re.Pattern]: a compiled regular expression pattern
    """
    if filter_settings["enabled"]:
        return re.compile("|".join(filter_settings["filters"]))
    # search for everything
    return re.compile("^.*?$")


def _construct_query_from_form(form: Tag) -> dict:
    """looks for input tags from soup

    Args:
        form (object): soup object normally a form tag as input tags are placed within them

    Returns:
        dict: returns name, value key pair of input tags found 
    """
    inputs = form.find_all("input")
    data = {}
    for _input in inputs:
        name = _input.attrs.get("name", "")
        value = _input.attrs.get("value", "")
        data[name] = value
    return data


def process_form(url: str, form: Tag) -> UrlData:
    """constructs a UrlData object from form tag tree

    Args:
        url (str): the url associated with the form tag. The action value will be joined to the Url to complete the form request
        form (object): The form tag tree parsed from BeautifulSoup

    Returns:
        [object]: formed UrlData is returned containing submit_url, action, method (GET or POST), data and the tagname 
    """
    action = form.attrs.get("action", "")
    req_type = form.attrs.get("method", "POST")
    data = _construct_query_from_form(form)
    submit_url = parse.urljoin(url, action)
    return UrlData(url=submit_url, action=action, method=req_type, data=data, tag="form")


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def sort_soup(url: str, soup: BeautifulSoup, include_forms: bool,
              images_only: bool, thumbnails_only: bool, filters: Pattern) -> dict:
    """Filters for Anchor, Image and Forms in the HTML soup object

    Args:
        url (str): The Url source of the soup being passed
        soup (object): The HTML soup object constructed from BeautifulSoup
        include_forms (bool): Add Form Tags and Input within the sort
        images_only (bool): Search only for images. Ignore Anchor tags
        thumbnails_only (bool): Only include anchor href if img tag within its tree
        filters (object): Compiled regular expression pattern. Only add links with filter matches

    Returns:
        urls (list): The list container that will contain UrlData objects that have been filtered
    """

    # sort_soup(str, str, list, bool, bool)
    # searches for images, forms and anchor tags in BeautifulSoup object
    # stores them in urls and returns then size of the urls list
    # urls is a list of UrlData objects
    # returns tuple (int, str) length of urls and title name

    urls = {}

    if include_forms:
        # scan forms
        for form in soup.find_all("form"):
            url_data = process_form(url, form)
            urls[url] = url_data

    ignored_images = {}
    if not images_only:
        # search for links on document
        a_tags = soup.find_all("a")
        for a_tag in a_tags:
            # make sure were not adding the same link as our url
            if a_tag.get("href") != url:
                if thumbnails_only:
                    img_tag = a_tag.find("img")
                    if img_tag:
                        _append_link(url, a_tag.get("href"), urls, "a", filters)
                        ignored_images[img_tag.get("src")] = 1
                else:
                    _append_link(url, a_tag.get("href", ""), urls, "a", filters)

    # search image tags
    for img_tag in soup.find_all("img"):
        if thumbnails_only:
            if not img_tag.get("src") in ignored_images:
                _append_link(url, img_tag.get("src", ""), urls, "img", filters)
        else:
            _append_link(url, img_tag.get("src", ""), urls, "img", filters)

    # search images in meta data
    for meta_tag in soup.find_all("meta", content=image_ext_pattern):
        _append_link(url, meta_tag.get("content", ""), urls, "img", filters)

    return urls


def _append_link(full_url: str, src: str, urls: dict, tag: str, filters: Pattern) -> bool:
    """appends Url to url_data_list if all patterns and filters match

    Args:
        full_url (str): The Url of the HTML source
        src (str): The Url to append
        urls (list): Global list of UrlData dicts. The src will appened to this list of all patterns match
        tag (str): The tag the src was found in..ie <a> or <img>
        filters (re.Pattern): compiled filter object used to match patterns
    """
    if src:
        parsed_src = parse.urlparse(src)
        if not parsed_src.netloc:
            # if no net location then add it from source url
            url = parse.urljoin(full_url, src)
            parsed_src = parse.urlparse(url)
        else:
            url = src
        if not parsed_src.scheme:
            # Try https?
            url = parse.urljoin("https://", url)
        # parse the source URl
        parsed_url = parse.urlparse(full_url)
        if parsed_src.netloc == parsed_url.netloc:
            if parsed_src.path == parsed_url.path:
                return False
            # same net location so make sure we don't search paths before the tree like the root index
            len_src = len(list(filter(lambda item: item, parsed_src.path.split("/"))))
            len_url = len(list(filter(lambda item: item, parsed_url.path.split("/"))))
            if len_src <= len_url:
                return False
        # Ignore root index. Maybe add option here?
        if not parsed_src.path or parsed_src.path == "/":
            return False
        # Filter the URL
        if filters.search(url):
            # make sure we don't have a duplicate
            # filter through the url_data list
            url_data = UrlData(url=url, action="", method="GET", data={}, tag=tag)
            if url not in urls:
                urls[url] = url_data
                return True
        return False
