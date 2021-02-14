"""
this file can be added to other projects and modified
loads and saves text on all platforms
"""

import os
import json
from threading import Lock
from urllib.request import url2pathname
import string

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

_file_lock = Lock()

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


class Settings:

    lock = Lock()

    @staticmethod
    def load():
        settings = DEFAULT_SETTINGS
        Settings.lock.acquire()
        data = load(SETTINGS_PATH)
        if data:
            settings = json.loads(data)
        Settings.lock.release()
        return settings
    
    @staticmethod
    def save(settings):
        Settings.lock.acquire()
        save(SETTINGS_PATH, json.dumps(settings))
        Settings.lock.release()


def check_path_exists():
    if not os.path.exists(PATH):
        _file_lock.acquire()
        os.mkdir(PATH)
        _file_lock.release()

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

def load(path):
    """
    load(str)
    takes in the name of the file to load. Doesnt require full path just the name of the file and extension
    returns loaded json object or None if no file exists
    """
    data = None
    check_path_exists()
    _file_lock.acquire()
    if os.path.exists(path):
        with open(path, "r") as fp:
            data = fp.read()
    _file_lock.release()
    return data

def save(path, data):
    _file_lock.acquire()
    check_path_exists()
    with open(path, "w") as fp:
        fp.write(data)
    _file_lock.release()

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
    settings = Settings.load()
    settings["unique_pathname"]["name"] = format_filename(title)
    Settings.save(settings)

