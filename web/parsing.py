import re
import os
from dataclasses import dataclass
from urllib import parse

import web.mime as mime

from bs4 import BeautifulSoup
import logging

_Log = logging.getLogger(__name__)

html_ext = ".html"

IMAGE_EXTS = (".jpg", ".bmp", ".jpeg", ".png", ".gif", ".tiff", ".ico")

_image_ext_pattern = re.compile("|".join(IMAGE_EXTS))


@dataclass
class UrlData:
    url: str
    method: str = "GET"
    action: str = ""
    data: dict = None
    tag: str = ""


def compile_filter_list(filter_list):
    return re.compile("|".join(filter_list))

def is_valid_content_type(url, content_type, valid_types):
    """Checks the MIME type to make sure it matches with a valid type either HTML or Image
    if an application/octet-stream is encountered the extension is used from the Url instead

    Args:
        url (str): The Source of the MIME type
        content_type (str): MIME type
        valid_types (dict): key, value pair of extension without the dot and boolean whether its valid.
                            example: {'jpg': True}, will only include jpg mime types and ignore other image formats

    Returns:
        [str]: returns the ext if a match is found or empty string if no match found
    """

    # check file attachement first and get its type
    if mime.is_octet_stream(content_type):
        # file attachemnt use the extension from the url
        try:
            content_type = mime.guess_mime_from_ext(os.path.splitext(url)[1])
        except IndexError as err:
            _Log.error(f"{err.__str__()}, {url}")

    ext = ""
    # HTML
    if mime.is_html(content_type):
        ext = ".html"
    # JPEG
    elif mime.is_jpeg(content_type):
        if valid_types.get("jpg", False):
            ext = ".jpg"
    # PNG
    elif mime.is_png(content_type):
        if valid_types.get("png", False):
            ext = ".png"
    # BITMAP
    elif mime.is_bitmap(content_type):
        if valid_types.get("bmp", False):
            ext = ".bmp"
    # GIF
    elif mime.is_gif(content_type):
        if valid_types.get("gif", False):
            ext = ".gif"
    # ICON
    elif mime.is_icon(content_type):
        if valid_types.get("ico", False):
            ext = ".ico"
    # TIFF
    elif mime.is_tiff(content_type):
        if valid_types.get("tiff", False):
            ext = ".tiff"
    # TGA 
    elif mime.is_tga(content_type):
        if valid_types.get("tga", False):
            ext = ".tga"
    return ext

def _construct_query_from_form(form):
    """
    looks for input types within form tags
    """
    inputs = form.find_all("input")
    data = {}
    for _input in inputs:
        name = _input.attrs.get("name", "")
        value = _input.attrs.get("value", "")
        data[name] = value
    return data

def process_form(url, form):
    """
    creates a UrlData object from form tag
    """
    action = form.attrs.get("action", "")
    req_type = form.attrs.get("method", "POST")
    data = _construct_query_from_form(form)
    submit_url = parse.urljoin(url, action)
    return UrlData(url=submit_url, action=action, method=req_type, data=data, tag="form")

def parse_html(html):
    return BeautifulSoup(html, features="html.parser")

def sort_soup(url,
              soup, 
              urls,
              include_forms,
              images_only, 
              thumbnails_only,
              filters):
    """
    sort_soup(str, str, list, bool, bool)
    searches for images, forms and anchor tags in BeatifulSoup object
    stores them in urls and returns then size of the urls list
    urls is a list of UrlData objects
    returns tuple (int, str) length of urls and title name
    """
    if include_forms:
        # scan forms
        for form in soup.find_all("form"):
            urldata = process_form(url, form)
            urls.append(urldata)

    ignore_list = []
    if not images_only:
        # search for links on document
        atags = soup.find_all("a")
        for atag in atags:
            # make sure were not adding the same link as our url
            if atag.get("href") != url:
                if thumbnails_only:
                    imgtag = atag.find("img")
                    if imgtag:
                        _appendlink(url, atag.get("href"), urls, "a", filters)
                        ignore_list.append(imgtag.get("src"))
                else:
                    _appendlink(url, atag.get("href", ""), urls, "a", filters)
    
    # search image tags
    for imgtag in soup.find_all("img"):
        if thumbnails_only:
            try:
                # ignore the thumbnail images
                ignore_list.index(imgtag.get("src"))
            except ValueError:
                # its not in our ignorelist
                _appendlink(url, imgtag.get("src", ""), urls, "img", filters)
        else:
            _appendlink(url, imgtag.get("src", ""), urls, "img", filters)

    # search images in meta data
    for metatag in soup.find_all("meta", content=_image_ext_pattern):
        _appendlink(url, metatag.get("content", ""), urls, "img", filters)
    
    return len(urls)


def _appendlink(full_url, src, url_data_list, tag, filters):
    """
    _appendlink(str, str, list)
    joins the url to the src and then uses a filter pattern
    to search for matches. If a match is found then it is checked
    in the urllist for conflicts if none found then it appends
    to the urllist
    """
    if src:
        url = parse.urljoin(full_url, src)
        # Filter the URL
        if filters.search(url):
            # make sure we dont have a duplicate
            # filter through the urldata list
            urldata = UrlData(url=url, action="", method="GET", data={}, tag=tag)
            if not list(filter(lambda d : d.url == url, url_data_list)):
                url_data_list.append(urldata)