import re
import os
import threading
import string
from dataclasses import dataclass

from urllib.request import url2pathname
from urllib import parse

from bs4 import BeautifulSoup

from options import Settings

html_ext = ".html"

FILTER_SEARCH = [
    "imagevenue.com/", 
    "imagebam.com/", 
    "pixhost.to/",
    "lulzimg",
    "pimpandhost",
    "imagetwist",
    "imgbox",
    "turboimagehost",
    "imx.to/"]

IMAGE_EXTS = (".jpg", ".bmp", ".jpeg", ".png", ".gif", ".tiff", ".ico")

_image_ext_pattern = re.compile("|".join(IMAGE_EXTS))


@dataclass
class UrlData:
    url: str
    method: str = "GET"
    action: str = ""
    data: dict = None
    tag: str = ""


class Globals:
    regex_filter = None
    new_folder_lock = threading.Lock()


def assign_unique_name(url, soup):
    """
    assign_unique_name(str, object)
    loads the settings file and adds a unique folder name
    to the settings and saves
    url to convert into path
    object is a beautifulsoup html object
    """
    Globals.new_folder_lock.acquire()
    title = soup.find("title")
    if title:
        settings = Settings.load()
        settings["unique_pathname"]["name"] = format_filename(title.text)
        Settings.save(settings)
    else:
        unique_name = url2pathname(url)
        settings = Settings.load()
        settings["unique_pathname"]["name"] = format_filename(unique_name)
        Settings.save(settings)
    Globals.new_folder_lock.release()

def format_filename(s):
    """Take a string and return a valid filename constructed from the string.
        Uses a whitelist approach: any characters not present in valid_chars are
        removed. Also spaces are replaced with underscores.
        
        Note: this method may produce invalid filenames such as ``, `.` or `..`
        When I use this method I prepend a date string like '2009_01_15_19_46_32_'
        and append a file extension like '.txt', so I avoid the potential of using
        an invalid filename.
        
        """
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ','_') # I don't like spaces in filenames.
    return filename

def compile_regex_global_filter(filter_list=FILTER_SEARCH):
    Globals.regex_filter = re.compile("|".join(filter_list))

def is_valid_content_type(url, content_type, valid_types):
    """
    is_valid_content_type(str, str, dict)
    checks if mimetype is an image and matches valid images
    url           - the url of the content-type
    content_type  - is a string found in the headers['Content-Type'] dict
    valid_types   - a dict containing valid files for searching
    returns an empty string if not valid or a file extension related to the file type
    will always return a valid file extension if html document
    """
    ext = ""
    if 'text/html' in content_type:
        ext = ".html"
    elif content_type == 'image/gif' and valid_types["gif"]:
        ext = ".gif"
    elif content_type == 'image/png' and valid_types["png"]:
        ext = ".png"
    elif content_type == 'image/ico' and valid_types["ico"]:
        ext = ".ico"
    elif content_type == 'image/jpeg' and valid_types["jpg"]:
        ext = ".jpg"
    elif content_type == 'image/tiff' and valid_types["tiff"]:
        ext = ".tiff"
    elif content_type == 'image/tga' and valid_types["tga"]:
        ext = ".tga"
    elif content_type == 'image/bmp' and valid_types["bmp"]:
        ext = ".bmp"
    elif content_type == 'application/octet-stream':
        # file attachemnt use the extension from the url
        try:
            ext = os.path.splitext(url)[1]
        except IndexError as err:
            print(f"is_valid_content_type web.py: {err.__str__()}, {url}")
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
              include_forms=True,
              images_only=False, 
              thumbnails_only=False):
    """
    sort_soup(str, str, list, bool, bool)
    searches for images, forms and anchor tags in BeatifulSoup object
    stores them in urls and returns then size of the urls list
    urls is a list of UrlData objects
    returns n if any tags found
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
                        _appendlink(url, atag.get("href"), urls, "a")
                        ignore_list.append(imgtag.get("src"))
                else:
                    _appendlink(url, atag.get("href", ""), urls, "a")
    
    # search image tags
    for imgtag in soup.find_all("img"):
        if thumbnails_only:
            try:
                # ignore the thumbnail images
                ignore_list.index(imgtag.get("src"))
            except ValueError:
                # its not in our ignorelist
                _appendlink(url, imgtag.get("src", ""), urls, "img")
        else:
            _appendlink(url, imgtag.get("src", ""), urls, "img")

    # search images in meta data
    for metatag in soup.find_all("meta", content=_image_ext_pattern):
        _appendlink(url, metatag.get("content", ""), urls, "img")
    
    return len(urls)


def _appendlink(full_url, src, url_data_list, tag):
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
        if Globals.regex_filter.search(url):
            # make sure we dont have a duplicate
            # filter through the urldata list
            urldata = UrlData(url=url, action="", method="GET", data={}, tag=tag)
            if not list(filter(lambda d : d.url == url, url_data_list)):
                url_data_list.append(urldata)