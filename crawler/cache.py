"""
cache.py

uses sqlite to store ignored images and broken links
this will optimize the performance of the scraper searches
"""

import sqlite3
import time
import logging
from sqlite3 import Error
from functools import partial

import crawler.options as options

_Log = logging.getLogger(__name__)

CACHE_TABLE = """CREATE TABLE IF NOT EXISTS ignored (
    url text NOT NULL,
    reason text NOT NULL,
    width integer,
    height integer,
    time_stamp integer
);
"""

QUERY_INSERT_IGNORE = """
INSERT INTO ignored(url,reason,width,height,time_stamp) 
VALUES(?,?,?,?,?)"""

QUERY_DELETE_IGNORE = """DELETE FROM ignored WHERE url=?
"""

QUERY_URL_IGNORE = "SELECT * FROM ignored WHERE url=?"

connect_to_cache = partial(sqlite3.connect, database=options.SQL_PATH, check_same_thread=False)


def initialize_ignore():
    """
    Creates the ignore table if one doesnt exist
    """
    try:
        conn = connect_to_cache()
        # Create the Table if not exist
        cur = conn.cursor()
        cur.execute(CACHE_TABLE)
        conn.close()
    except Error as err:
        _Log.error(err.__str__())


def add_ignore(url: str, reason: str, width: int, height: int):
    """Add an entry into ignore table

    Args:
        url (str): the url being added
        reason (str): The reason as to why its being added to the ignore list
        width (int): The width of the file if there isnt one then 0 is added
        height (int): The height. Same as width

        Note: A timestamp is also added to the entry
    """
    try:
        conn = connect_to_cache()
        _add_entry(conn, url, reason, width, height)
        conn.close()
    except Error as err:
        _Log.error(err.__str__())


def delete_ignore(url: str):
    """Delete entry with a url that matches in the database

    Args:
        url (str): The url to be deleted
    """
    try:
        conn = connect_to_cache()
        cur = conn.cursor()
        cur.execute(QUERY_DELETE_IGNORE, (url,))
        conn.commit()
    except Error as err:
        _Log.error(err.__str__())


def query_ignore(url: str) -> list:
    """Checks if a url is in the database

    Args:
        url (str): The url to be searched

    Returns:
        [str]: returns an iterator of urls that match None is nothing found
    """
    rows = []
    try:
        conn = connect_to_cache()
        cur = conn.cursor()
        cur.execute(QUERY_URL_IGNORE, (url,))
        rows = cur.fetchall()
        conn.close()
    except Error as err:
        _Log.error(err.__str__())
    finally:
        return rows


def check_cache_for_image(url: str, settings: dict) -> bool:
    """
    checks if url is in database and checks the image
    minimum width and height returns false
    if no duplicate exists.
    """
    result = query_ignore(url)
    if result:
        url_data = result[0]
        if url_data[1] == "small-image":
            width = settings["minimum_image_resolution"]["width"]
            height = settings["minimum_image_resolution"]["height"]
            if width > url_data[2] and height > url_data[3]:
                # minimum resolution has changed
                # delete the entry
                delete_ignore(url)
                return False
            else:
                return True
    return False


def _add_entry(conn: sqlite3.Connection, url: str, reason: str, width: int, height: int) -> int:
    # Returns the Row ID if match has been found
    values = (
        url,
        reason,
        width,
        height,
        time.time()
    )
    cur = conn.cursor()
    # append the time stamp on the end
    cur.execute(QUERY_INSERT_IGNORE, values)
    conn.commit()
    return cur.lastrowid
