"""
deals with the settings file and handles file operations.
also contains functions for handling Profile Settings
"""

import os
import json
from urllib.request import url2pathname
import urllib.parse as parse
import string
import hashlib
import mimetypes
import threading
from contextlib import contextmanager
from collections import namedtuple

from crawler.mime import IMAGE_EXTS

VALID_FILE_NAME_CHARS = f"-_.() {string.ascii_letters}{string.digits}"

DEBUG = True
VERSION = "0.1"
GIT_SOURCE = "https://github.com/xxchaosxx210"
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

_IMAGE_INDEX_LOCK = threading.Lock()
_IMAGE_INDEX_LOCKS = {}
_IMAGE_INDEXES = {}


def _image_directory_key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _image_directory_lock(path: str):
    key = _image_directory_key(path)
    with _IMAGE_INDEX_LOCK:
        lock = _IMAGE_INDEX_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _IMAGE_INDEX_LOCKS[key] = lock
        return lock


@contextmanager
def image_save_lock(path: str):
    """Keep duplicate checks and saves to one folder consistent across workers."""
    lock = _image_directory_lock(path)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def _hash_file(path: str) -> bytes:
    digest = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def _build_image_index(path: str):
    by_size_and_hash = {}
    unhashed_by_size = {}
    path_keys = {}
    path_sizes = {}
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if not entry.is_file() or not entry.name.endswith(IMAGE_EXTS):
                        continue
                    size = entry.stat().st_size
                except OSError:
                    continue
                unhashed_by_size.setdefault(size, []).append(entry.path)
                normalized_path = os.path.normcase(os.path.abspath(entry.path))
                path_keys[normalized_path] = None
                path_sizes[normalized_path] = size
        modified = os.stat(path).st_mtime_ns
    except OSError:
        modified = None

    index = {
        "modified": modified,
        "files": by_size_and_hash,
        "unhashed": unhashed_by_size,
        "path_keys": path_keys,
        "path_sizes": path_sizes,
    }
    _IMAGE_INDEXES[_image_directory_key(path)] = index
    return index


def _index_image_size(index, size: int):
    """Hash only existing files that could match this image's byte length."""
    paths = index["unhashed"].pop(size, ())
    for file_path in paths:
        normalized_path = os.path.normcase(os.path.abspath(file_path))
        try:
            if os.stat(file_path).st_size != size:
                index["path_keys"].pop(normalized_path, None)
                index["path_sizes"].pop(normalized_path, None)
                continue
            digest = _hash_file(file_path)
        except OSError:
            index["path_keys"].pop(normalized_path, None)
            index["path_sizes"].pop(normalized_path, None)
            continue
        key = (size, digest)
        index["files"].setdefault(key, []).append(file_path)
        index["path_keys"][normalized_path] = key


def _get_image_index(path: str):
    key = _image_directory_key(path)
    try:
        modified = os.stat(path).st_mtime_ns
    except OSError:
        modified = None

    index = _IMAGE_INDEXES.get(key)
    if index is None or index["modified"] != modified:
        return _build_image_index(path)
    return index

_FILTER_SEARCH = [
    "imagevenue.com/",
    "imagebam.com/",
    "pixhost.to/",
    "pixhost.cc/",
    "pixho.st/",
    "lulzimg",
    "pimpandhost",
    "imagetwist",
    "imgbox",
    "turboimagehost",
    "imx.to/",
    "localhost:5000",
    "turboimg.net/"]

DEFAULT_SETTINGS = {
    "profile-name": "default",
    "app_version": VERSION,
    "cookies": {
        "firefox": True,
        "chrome": False,
        "opera": False,
        "edge": False,
        "all": False,
        "app_bound": False,
    },
    "user_agent": {"mode": "automatic", "custom": ""},
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
        "tga": False,
        "webp": True},
    "filter-search": {"enabled": True, "filters": _FILTER_SEARCH},
    "file_exists": "overwrite",
    "form_search": {"enabled": True, "include_original_host": False},
    "notify-done": True,
    "auto-download": False,
    "results-collapsed-on-start": True,
    "compact-bottom-right": True
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


def load_settings() -> dict:
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
    # WebP support was added after the original settings format.
    # Enable it automatically for existing installations.
    settings.setdefault("images_to_search", {})
    settings["images_to_search"].setdefault("webp", True)
    settings.setdefault("results-collapsed-on-start", True)
    settings.setdefault("compact-bottom-right", True)
    settings.setdefault("user_agent", {})
    settings["user_agent"].setdefault("mode", "automatic")
    settings["user_agent"].setdefault("custom", "")

    # Pixhost also serves forum thumbnails through pixhost.cc.
    # Keep it in the default filter list and add it automatically to
    # existing installations without disturbing the user's other filters.
    settings.setdefault(
        "filter-search",
        {"enabled": True, "filters": list(_FILTER_SEARCH)}
    )
    settings["filter-search"].setdefault("enabled", True)
    settings["filter-search"].setdefault("filters", list(_FILTER_SEARCH))
    for pixhost_domain in ("pixhost.cc/", "pixho.st/"):
        if pixhost_domain not in settings["filter-search"]["filters"]:
            settings["filter-search"]["filters"].append(pixhost_domain)

    # Remove settings from retired UI features.
    settings.pop("detach-progress", None)
    return settings


def save_settings(settings: dict):
    _check_path_exists()
    settings.pop("detach-progress", None)
    with open(SETTINGS_PATH, "w") as fp:
        fp.write(json.dumps(settings))


def _check_path_exists():
    if not os.path.exists(PATH):
        os.mkdir(PATH)


def format_filename(s: str) -> str:
    """Take a string and return a valid filename constructed from the string.
        Uses a whitelist approach: any characters not present in valid_chars are
        removed. Also spaces are replaced with underscores.
        
        Note: this method may produce invalid filenames such as ``, `.` or `..`
        When I use this method I prepend a date string like '2009_01_15_19_46_32_'
        and append a file extension like '.txt', so I avoid the potential of using
        an invalid filename.
        
        """
    filename = ''.join(c for c in s if c in VALID_FILE_NAME_CHARS)
    filename = filename.replace(' ', '_')
    return filename


def assign_unique_name(url: str, title: str):
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


def url_to_filename(url: str, ext: str) -> str:
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
    parse_result = parse.urlparse(url)
    if parse_result:
        pathname = url2pathname(getattr(parse_result, "path", ""))
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


def rename_file(path: str) -> str:
    """checks the file for a match in the path. Creates a unique filename until no match is found

    Args:
        path (str): the path of the filename to be checked

    Returns:
        str: returns the new path name
    """
    split_path = os.path.split(path)
    if split_path:
        filename = split_path[-1]
        name, ext = os.path.splitext(filename)
        index = 0
        while os.path.exists(path):
            filename = f"{name}_{index}{ext}"
            path = os.path.join(split_path[0], filename)
            index += 1
    return path


def image_exists(path: str, stream_bytes: bytes, digest=None) -> str:
    """Check a cached size-and-hash index for a matching image.

    Args:
        path (str): The path to scan for images
        stream_bytes (b): downloaded image bytes or a bytes-like view

    Returns:
        str: returns the file path if their is a match.
    """
    lock = _image_directory_lock(path)
    with lock:
        digest = digest or image_digest(stream_bytes)
        index = _get_image_index(path)
        _index_image_size(index, len(stream_bytes))
        matches = index["files"].get((len(stream_bytes), digest), ())
        return matches[0] if matches else ""


def image_digest(stream_bytes: bytes) -> bytes:
    """Return the checksum used by the duplicate image index."""
    return hashlib.md5(stream_bytes).digest()


def register_saved_image(directory: str, file_path: str, stream_bytes: bytes, digest=None):
    """Add an image written by this run to the cached duplicate index."""
    lock = _image_directory_lock(directory)
    with lock:
        index = _IMAGE_INDEXES.get(_image_directory_key(directory))
        if index is None:
            index = _build_image_index(directory)
        key = (len(stream_bytes), digest or image_digest(stream_bytes))
        absolute_path = os.path.abspath(file_path)
        normalized_path = os.path.normcase(absolute_path)
        had_previous = normalized_path in index["path_sizes"]
        previous_size = index["path_sizes"].pop(normalized_path, None)
        previous_key = index["path_keys"].pop(normalized_path, None)
        if had_previous and previous_key is None:
            previous_paths = index["unhashed"].get(previous_size, [])
            index["unhashed"][previous_size] = [
                existing for existing in previous_paths
                if os.path.normcase(os.path.abspath(existing)) != normalized_path
            ]
            if not index["unhashed"][previous_size]:
                del index["unhashed"][previous_size]
        elif previous_key is not None:
            previous_paths = index["files"].get(previous_key, [])
            index["files"][previous_key] = [
                existing for existing in previous_paths
                if os.path.normcase(os.path.abspath(existing)) != normalized_path
            ]
            if not index["files"][previous_key]:
                del index["files"][previous_key]
        index["files"].setdefault(key, []).append(absolute_path)
        index["path_keys"][normalized_path] = key
        index["path_sizes"][normalized_path] = len(stream_bytes)
        try:
            index["modified"] = os.stat(directory).st_mtime_ns
        except OSError:
            index["modified"] = None


def load_from_file(url: str) -> tuple:
    """bit of a patch to mimic the requests handle using a namedtuple
    no code broken and fits in ok

    Args:
        url (str): the fake url to be sent

    Returns:
        [tuple]: Requests namedtuple (text, url, headers, close) 
    """
    if os.path.exists(url):
        _type, ext = mimetypes.guess_type(url)
        if "text/html" in _type:
            with open(url, "r") as fp:
                html = fp.read()
                return namedtuple("Request", ["text", "url", "headers", "close"])(
                    html, "http://wasfromafile.com", {"Content-Type": _type}, lambda *args: args)
    raise FileNotFoundError(f"unable to locate {url} on local disk")


def load_profiles() -> list:
    """loads all profile settings from profile dir

    Returns:
        [list]: list of profile name str found in the profiles folder
    """
    profiles = []
    if os.path.exists(PROFILES_PATH):
        it = os.scandir(PROFILES_PATH)
        while 1:
            try:
                entry = it.__next__()
                if entry.is_file() and entry.path.endswith(PROFILE_EXT):
                    profiles.append(os.path.splitext(entry.name)[0])
            except StopIteration:
                break
    else:
        os.mkdir(PROFILES_PATH)

    return profiles


def save_profile(settings: dict):
    """Creates a profile json file using settings["profile-name"] in the profiles dir

    Args:
        settings (dict): json settings object to be saved into profiles
    """
    if not os.path.exists(PROFILES_PATH):
        os.mkdir(PROFILES_PATH)
    path = os.path.join(PROFILES_PATH, settings["profile-name"] + PROFILE_EXT)
    with open(path, "w") as fp:
        fp.write(json.dumps(settings))


def use_profile(name: str) -> bool:
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
        it = os.scandir(PROFILES_PATH)
        while 1:
            try:
                entry = it.__next__()
                if entry.is_file() and entry.path.endswith(PROFILE_EXT):
                    if os.path.splitext(entry.name)[0] == name:
                        # overwrite the old settings with the newly selected one
                        with open(entry.path, "r") as fp:
                            save_settings(json.loads(fp.read()))
                        return True
            except StopIteration:
                break
    return False


def delete_profile(name: str) -> bool:
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
                return True

    return False
