___description__ ="""
cache.py

uses sqlite to store ignored images and broken links
this will optimize the performance of the scraper searches
"""

import sqlite3
import os
import time

from sqlite3 import Error

import web.options as options

import logging

_Log = logging.getLogger(__name__)

SQL_FILENAME = os.path.join(options.PATH, "cache.db")

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


def initialize_ignore():
    conn = _create_connection(SQL_FILENAME)
    if conn:
        _create_table(conn, CACHE_TABLE)
        conn.close()  

def add_ignore(url, reason, width, height):
    conn = _create_connection(SQL_FILENAME)
    if conn:
        _add_entry(conn, url, reason, width, height)
        conn.close()
    
def delete_ignore(url):
    conn = _create_connection(SQL_FILENAME)
    if conn:
        _delete_entries(conn, url)
        
def query_ignore(url):
    rows = []
    conn = _create_connection(SQL_FILENAME)
    if conn:
        cur = conn.cursor()
        cur.execute(QUERY_URL_IGNORE, (url,))
        rows = cur.fetchall()
        conn.close()
    return rows

def check_cache_for_image(url, settings):
    """
    checks if url is in database and checks the image
    minimum width and height returns false
    if no duplicate exists.
    """
    result = query_ignore(url)
    if result:
        urldata = result[0]
        if urldata[1] == "small-image":
            width = settings["minimum_image_resolution"]["width"]
            height = settings["minimum_image_resolution"]["height"]
            if width > urldata[2] and height > urldata[3]:
                # minimum resolution has changed
                # delete the entry
                delete_ignore(url)
                return False
            else:
                return True
    return False

def _create_connection(dbpath):
    """
    create_connection(str)
    path to the db want to connect to
    will create a new DB if no path found
    """
    conn = None
    try:
        conn = sqlite3.connect(dbpath, check_same_thread=False)
    except Error as err:
        _Log.error(err.__str__())
    return conn

def _add_entry(conn, url, reason, width, height):
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

def _delete_entries(conn, url):
    cur = conn.cursor()
    cur.execute(QUERY_DELETE_IGNORE, (url,))
    conn.commit()

def _create_table(conn, sql_table):
    try:
        cur = conn.cursor()
        cur.execute(sql_table)
    except Error as err:
        _Log.error(err.__str__())

def _test():
    initialize_ignore()
    _Log.info(query_ignore("https://imgbox.com/images/imgbox.png"))

if __name__ == '__main__':
    _test()