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
import mimetypes
from collections import namedtuple

from crawler.mime import IMAGE_EXTS

DEBUG = True

VERSION = "0.1"

# Get settings folder path

APP_NAME = "pixgrabber"

if os.name == "nt":
    PATH = os.path.join(os.environ.get("USERPROFILE"), APP_NAME)
else:
    PATH = os.path.join(os.environ.get("HOME"), APP_NAME)

SETTINGS_PATH = os.path.join(PATH, "settings.json")
DEFAULT_PICTURE_PATH = "Pictures"

PROFILES_PATH = os.path.join(PATH, "profiles")
PROFILE_EXT = ".pro"

SQL_PATH = os.path.join(PATH, "cache.db")

_FILTER_SEARCH = [
    "imagevenue.com/", 
    "imagebam.com/", 
    "pixhost.to/",
    "lulzimg",
    "pimpandhost",
    "imagetwist",
    "imgbox",
    "turboimagehost",
    "imx.to/",
    "localhost:5000"]

DEFAULT_SETTINGS = {
    "profile-name": "default",
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
    "filter-search": {"enabled": True, "filters": _FILTER_SEARCH},
    "file_exists": "overwrite",
    "form_search": {"enabled": True, "include_original_host": False},
    "notify-done": True,
    "auto-download": False
    }

def setup():
    """call this at start of main script
    """
    if not os.path.exists(PATH):
        os.mkdir(PATH)
    if not os.path.exists(PROFILES_PATH):
        os.mkdir(PROFILES_PATH)
    save_settings(load_settings())
    if not load_profiles():
        save_profile(load_settings())

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
    """strips the url and converts the last path name which is normally the filename
    and uses the ext if no ext found in the Url. use is_valid_content_type
    in the parsing.py file to determine what the url content-type is.
    Returns formatted filename if successful empty string otherwise

    Args:
        url (str): the url to convert to a filename
        ext (str): the extension to associate the file to

    Returns:
        [str]: returns the converted filename. Empty string if unable to convert
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
    """checks the file for a match in the path. Creates a unique filename until no match is found

    Args:
        path (str): the path of the filename to be checked

    Returns:
        str: returns the new path name
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
    """scans the path for images and checks the checksum of the stream_bytes and file_bytes

    Args:
        path (str): The path to scan for images
        stream_bytes (b): byte stream of image

    Returns:
        str: returns the file path if their is a match. None if no match found
    """
    with os.scandir(path) as it:
        for entry in it:
            # check entry is an image first
            if entry.is_file() and entry.name.endswith(IMAGE_EXTS):
                # improve performance, check the file size first from stats
                if entry.stat().st_size == stream_bytes.__len__():
                    # if sizes match then read file check the md5 hash
                    with open(entry.path, "rb") as fp:
                        hash1 = hashlib.md5(fp.read()).digest()
                        hash2 = hashlib.md5(stream_bytes).digest()
                        if hash1 == hash2:
                            # weve got a duplicate return the pathname
                            return entry.path
    return None

def load_from_file(url):
    """bit of a patch to mimick the requests handle using a namedtuple
    no code broken and fits in ok

    Args:
        url (str): the fake url to be sent

    Returns:
        [tuple]: Requests namedtuple (text, url, headers, close) 
    """
    fake_request = None
    if os.path.exists(url):
        _type, ext = mimetypes.guess_type(url)
        if "text/html" in _type:
            with open(url, "r") as fp:
                html = fp.read()
                fake_request = namedtuple("Request", ["text", "url", "headers", "close"])(
                    html, "http://wasfromafile.com", {"Content-Type": _type},
                    lambda *args: args)
    return fake_request

def load_profiles():
    """loads all profile settings from profile dir

    Returns:
        [list]: list of profile name str found in the profiles folder
    """
    profiles = []
    if os.path.exists(PROFILES_PATH):
        with os.scandir(PROFILES_PATH) as it:
            for entry in it:
                if entry.is_file() and entry.path.endswith(PROFILE_EXT):
                    profiles.append(os.path.splitext(entry.name)[0])
    else:
        os.mkdir(PROFILES_PATH)

    return profiles

def save_profile(settings):
    """Creates a profile json file using settings["profile-name"] in the profiles dir

    Args:
        settings (dict): json settings object to be saved into profiles
    """
    if not os.path.exists(PROFILES_PATH):
        os.mkdir(PROFILES_PATH)
    path = os.path.join(PROFILES_PATH, settings["profile-name"] + PROFILE_EXT)
    with open(path, "w") as fp:
        fp.write(json.dumps(settings))

def use_profile(name):
    """loads the profile associated with name. Makes a copy of it and saves it to settings.json. 
    Also loads the previous profile and saves it to profiles dir

    Args:
        name (str): the name of the profile to be used

    Returns:
        [bool]: Returns True if profile is being used. False if error or no profile found
    """
    # save the current existing profile
    save_profile(load_settings())
    if os.path.exists(PROFILES_PATH):
        with os.scandir(PROFILES_PATH) as it:
            for entry in it:
                if entry.is_file() and entry.path.endswith(PROFILE_EXT):
                    if os.path.splitext(entry.name)[0] == name:
                        # overwrite the old settings with the newly selected one
                        with open(entry.path, "r") as fp:
                            save_settings(json.loads(fp.read()))
                        return True
    return False

def delete_profile(name):
    """deletes the profile file. If deleted profile is used then load default profile settings instead

    Args:
        name (str): Name of the Profile to delete

    Returns:
        [bool]: Returns True if successful. False if Error or no profile found
    """
    if name == "default":
        raise NameError("You cannot delete the default profile")
    else:
        if os.path.exists(PROFILES_PATH):
            path = os.path.join(PROFILES_PATH, name + PROFILE_EXT)
            if os.path.exists(path):
                os.remove(path)
                settings = load_settings()
                # check to see if settings.json is the deleted profile
                if name == settings["profile-name"]:
                    # it is so use default profile instead
                    save_settings(DEFAULT_SETTINGS)
                    #use_profile(DEFAULT_SETTINGS["profile-name"])
                return True
        
    return False