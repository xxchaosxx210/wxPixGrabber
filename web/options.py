"""
this file can be added to other projects and modified
loads and saves text on all platforms
"""

import os
import json
from urllib.request import url2pathname
import urllib.parse as parse
import string
import hashlib

VERSION = "0.1"

# Get settings folder path

APP_NAME = "wxpixgrabber"

if os.name == "nt":
    PATH = os.path.join(os.environ.get("USERPROFILE"), APP_NAME)
else:
    PATH = os.path.join(os.environ.get("HOME"), APP_NAME)

LOG_PATH = os.path.join(PATH, "log.txt")
SETTINGS_PATH = os.path.join(PATH, "settings.json")
DEFAULT_PICTURE_PATH = "Pictures"

_FILTER_SEARCH = [
    "imagevenue.com/", 
    "imagebam.com/", 
    "pixhost.to/",
    "lulzimg",
    "pimpandhost",
    "imagetwist",
    "imgbox",
    "turboimagehost",
    "imx.to/"]

DEFAULT_SETTINGS = {
    "app_version": VERSION,
    "cookies": {"firefox": True, "chrome": False, "opera": False, "edge": False, "all": False},
    "proxy": {"enable": False, "ip": "", "port": 0, "username": "", "password": ""},
    "max_connections": 10,
    "connection_timeout": 5,
    "minimum_image_resolution": {"width": 200, "height": 200},
    "thumbnails_only": True,
    "save_path": os.getcwd(),
    "unique_pathname": {"enabled": True, "name": ""},
    "generate_filenames": {"enabled": True, "name": "image"},
    "images_to_search": {
        "jpg": True, 
        "png": False,
        "gif": False,
        "bmp": False,
        "ico": False,
        "tiff": False,
        "tga": False},
    "filters": _FILTER_SEARCH,
    "file_exists": "overwrite",
    "form_search": {"enabled": True, "include_original_host": False},
    "notify-done": True,
    "auto-download": False
    }

def load_settings():
    """
    load_settings()
    takes in the name of the file to load. Doesnt require full path just the name of the file and extension
    returns loaded json object or None if no file exists
    """
    settings = DEFAULT_SETTINGS
    _check_path_exists()
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as fp:
            settings = json.loads(fp.read())
    return settings

def save_settings(settings):
    _check_path_exists()
    with open(SETTINGS_PATH, "w") as fp:
        fp.write(json.dumps(settings))

def _check_path_exists():
    if not os.path.exists(PATH):
        os.mkdir(PATH)

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

def assign_unique_name(url, title):
    """
    assign_unique_name(str, str)
    loads the settings file and adds a unique folder name
    to the settings and saves
    url to convert into path
    title is the string used from the html document title
    """
    if not title:
        title = url2pathname(url)
    settings = load_settings()
    settings["unique_pathname"]["name"] = format_filename(title)
    save_settings(settings)

def url_to_filename(url, ext):
    """
    url_ro_filename(str, str)
    strips the url and converts the last path name which is normally the filename
    and uses the ext if no ext found in the Url. use is_valid_content_type
    in the parsing.py file to determine what the url content-type is.
    Returns formatted filename if successful empty string otherwise
    """
    presult = parse.urlparse(url)
    if presult:
        pathname = url2pathname(getattr(presult, "path", ""))
        if pathname:
            split_paths = os.path.split(pathname)
            if split_paths:
                filename = split_paths[-1]
                filename, e = os.path.splitext(filename)
                if e:
                    ext = e
                filename = format_filename(filename + ext)
                return filename
    return ""

def rename_file(path):
    """
    rename_file(str)
    takes a full path of the file and adds a counter
    to the filename until no file with the name
    exists
    returns the full path
    """
    splitpath = os.path.split(path)
    if splitpath:
        filename = splitpath[-1]
        name, ext = os.path.splitext(filename)
        index = 0
        while os.path.exists(path):
            filename = f"{name}_{index}{ext}"
            path = os.path.join(splitpath[0], filename)
            index += 1
    return path

def image_exists(path, stream_bytes):
    """
    file_exists(str, byte[])
    loops through each file found in path checks the md5 hash with the stream_bytes hash
    returns the filename and path if there is a match. None if no match found
    """
    files_only = list(filter(
                          lambda item : os.path.isfile(os.path.join(path, item)), 
                          os.listdir(path)))
    for filename in iter(files_only):
        # remove this line if looking for files other than images
        if filename.endswith((".jpg", ".gif", ".png", ".tiff", ".bmp", ".jpeg", ".ico", ".tga")):
            filepath = os.path.join(path, filename)
            with open(filepath, "rb") as fp:
                # read the first 1kb
                hash1 = hashlib.md5(fp.read(1000))
                hash2 = hashlib.md5(stream_bytes[:1000])
                result = hash1.digest() == hash2.digest()
                if result:
                    fp.close()
                    return os.path.join(path, filename)
                fp.close()
    return None
                