import re
from urllib import parse
from bs4 import BeautifulSoup
import logging

from crawler.types import UrlData
from crawler.mime import image_ext_pattern

_Log = logging.getLogger(__name__)

def compile_filter_list(filter_settings):
    if filter_settings["enabled"]:
        return re.compile("|".join(filter_settings["filters"]))
    # search for everything
    return re.compile("^.*?$")

def _construct_query_from_form(form):
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

def process_form(url, form):
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

def parse_html(html):
    return BeautifulSoup(html, features="html.parser")

def sort_soup(url, soup, urls, include_forms,
              images_only, thumbnails_only, filters):
    """Filters for Anchor, Image and Forms in the HTML soup object

    Args:
        url (str): The Url source of the soup being passed
        soup (object): The HTML soup object constructed from BeautifulSoup
        urls (list): The list container that will contain UrlData objects that have been filtered
        include_forms (bool): Add Form Tags and Input within the sort
        images_only (bool): Search only for images. Ignore Anchor tags
        thumbnails_only (bool): Only include anchor href if img tag within its tree
        filters (object): Compiled regular expression pattern. Only add links with filter matches

    Returns:
        int: the length of urls found. 0 if none found
    """

    # sort_soup(str, str, list, bool, bool)
    # searches for images, forms and anchor tags in BeatifulSoup object
    # stores them in urls and returns then size of the urls list
    # urls is a list of UrlData objects
    # returns tuple (int, str) length of urls and title name

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
    for metatag in soup.find_all("meta", content=image_ext_pattern):
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
        parsed_src = parse.urlparse(src)
        if not parsed_src.netloc:
            # if no net location then add it from source url
            url = parse.urljoin(full_url, src)
            parsed_src = parse.urlparse(url)
        else:
            url = src
        # parse the source URl
        parsed_url = parse.urlparse(full_url)
        if parsed_src.netloc == parsed_url.netloc:
            if parsed_src.path == parsed_url.path:
                return
            # same net location so make sure we dont search paths before the tree like the root index
            lensrc = len(list(filter(lambda item : item, parsed_src.path.split("/"))))
            lenurl = len(list(filter(lambda item : item, parsed_url.path.split("/"))))
            if lensrc <= lenurl:
                return
        # Filter the URL
        if filters.search(url):
            # make sure we dont have a duplicate
            # filter through the urldata list
            urldata = UrlData(url=url, action="", method="GET", data={}, tag=tag)
            if not list(filter(lambda d : d.url == url, url_data_list)):
                url_data_list.append(urldata)