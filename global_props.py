"""
this file can be added to other projects and modified
loads and saves text on all platforms
"""

import os
import json
from threading import Lock

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
    "filter_search": {
        "filters": []},
    "file_exists": "overwrite",
    "form_search": True
    }

global_settings = DEFAULT_SETTINGS

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
