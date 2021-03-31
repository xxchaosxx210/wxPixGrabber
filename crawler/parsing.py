import re
import os
from urllib import parse
from bs4.element import Tag
from bs4 import BeautifulSoup
import logging
from typing import Pattern

from crawler.webrequest import UrlData
from crawler.mime import (
    image_ext_pattern,
    IMAGE_EXTS
)

#_Log = logging.getLogger(__name__)
class _Log:
    @staticmethod
    def info(s: str):
        pass

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
              images_only: bool, thumbnails_only: bool, filters: Pattern, img_exts: dict):
    """Filters for Anchor, Image and Forms in the HTML soup object
    Use this function as a Generator

    Args:
        img_exts:
        url (str): The Url source of the soup being passed
        soup (object): The HTML soup object constructed from BeautifulSoup
        include_forms (bool): Add Form Tags and Input within the sort
        images_only (bool): Search only for images. Ignore Anchor tags
        thumbnails_only (bool): Only include anchor href if img tag within its tree
        filters (object): Compiled regular expression pattern. Only add links with filter matches

    Returns:
        generator object
    """
    urls = {}

    if include_forms:
        # scan forms
        for form in soup.find_all("form"):
            url_data = process_form(url, form)
            urls[url] = url_data
            yield url_data

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
                        try:
                            url_data = _append_link(url, a_tag.get("href"), urls, "a", filters, img_exts)
                            yield url_data
                        except LookupError as err:
                            _Log.info(err.__str__())
                        finally:
                            ignored_images[img_tag.get("src")] = 1
                else:
                    try:
                        url_data = _append_link(url, a_tag.get("href", ""), urls, "a", filters, img_exts)
                        yield url_data
                    except LookupError as err:
                        _Log.info(err.__str__())

    # search image tags
    for img_tag in soup.find_all("img"):
        if thumbnails_only:
            if not img_tag.get("src") in ignored_images:
                try:
                    url_data = _append_link(url, img_tag.get("src", ""), urls, "img", filters, img_exts)
                    yield url_data
                except LookupError as err:
                    _Log.info(err.__str__())
        else:
            try:
                url_data = _append_link(url, img_tag.get("src", ""), urls, "img", filters, img_exts)
                yield url_data
            except LookupError as err:
                _Log.info(err.__str__())

    # search images in meta data
    for meta_tag in soup.find_all("meta", content=image_ext_pattern):
        try:
            url_data = _append_link(url, meta_tag.get("content", ""), urls, "img", filters, img_exts)
            yield url_data
        except LookupError as err:
            _Log.info(err.__str__())


def _append_link(full_url: str, src: str, urls: dict, tag: str, filters: Pattern, img_ext: dict) -> UrlData:
    """
    Takes in the original Url and Src Url found from the Tag. Tries to join them together to get
    the correct path. Filters out Root index and Parent paths. Finally checks the Regex filtered pattern
    if match found and not already added to Urls dict then returns UrlData object
    Raises LookupError if criteria not met
    Args:
        full_url: the url from the source of the parsed Html
        src: the source Url found from the Tag on parsed Html
        urls: dict container which stores all added UrlData objects
        tag: TagName of src url either IMG or A. This will be added to the UrlData object
        filters: regex pattern. If match found then Url is added to urls dict

    Returns:
        UrlData object
    """
    if src:
        parsed_src = parse.urlparse(src)
        path, ext = os.path.splitext(parsed_src.path)
        if ext in IMAGE_EXTS:
            if not img_ext.get(ext[1:], False):
                raise LookupError(f"Image extension found. Not included in Search {src}")
        if not parsed_src.netloc:
            # if no net location then add it from source url
            _Log.info(f"No Netloc found for {src}. Joining {src} to full_url")
            url = parse.urljoin(full_url, src)
            parsed_src = parse.urlparse(url)
        else:
            url = src
        if not parsed_src.scheme:
            _Log.info(f"No Scheme found. Appending HTTPS scheme to {url}")
            url = parse.urljoin("https://", url)
        # parse the source URl
        parsed_url = parse.urlparse(full_url)
        if parsed_src.netloc == parsed_url.netloc:
            if parsed_src.path == parsed_url.path:
                raise LookupError(f"Url and src Url paths both match. Ignoring {src}")
            # same net location so make sure we don't search paths before the tree like the root index
            len_src = len(list(filter(lambda item: item, parsed_src.path.split("/"))))
            len_url = len(list(filter(lambda item: item, parsed_url.path.split("/"))))
            if len_src <= len_url:
                raise LookupError(f"Length of source is less or equal to length of url. Ignoring {src}")
        # Ignore root index. Maybe add option here?
        if not parsed_src.path or parsed_src.path == "/":
            raise LookupError(f"Ignoring Root index from {src}")
        # Filter the URL
        if filters.search(url):
            url_data = UrlData(url=url, action="", method="GET", data={}, tag=tag)
            if url not in urls:
                urls[url] = url_data
                return url_data
            else:
                raise LookupError(f"{url} already added to urls")
        else:
            LookupError(f"{url} did not match filtered pattern")
    else:
        raise LookupError(f"No src found in _append_link")
