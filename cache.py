___description__ ="""
cache.py

uses sqlite to store ignored images and broken links
this will optimize the performance of the scraper searches
"""

import sqlite3
import os
import time
import threading

from sqlite3 import Error

import global_props

SQL_FILENAME = os.path.join(global_props.PATH, "cache.db")

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


class Sql:

    _lock = threading.Lock()

    @staticmethod
    def initialize_ignore():
        Sql._lock.acquire()
        conn = _create_connection(SQL_FILENAME)
        if conn:
            _create_table(conn, CACHE_TABLE)
            conn.close()
        Sql._lock.release()

    @staticmethod
    def add_ignore(url, reason, width, height):
        Sql._lock.acquire()
        conn = _create_connection(SQL_FILENAME)
        if conn:
            _add_entry(conn, url, reason, width, height)
            conn.close()
        Sql._lock.release()
    
    @staticmethod
    def delete_ignore(url):
        Sql._lock.acquire()
        conn = _create_connection(SQL_FILENAME)
        if conn:
            _delete_entries(conn, url)
        Sql._lock.release()

    @staticmethod
    def query_ignore(url):
        Sql._lock.acquire()
        Sql._lock.release()


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
        print(err.__str__())
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
        print(err.__str__())

def _test():
    Sql.initialize_ignore()
    Sql.delete_ignore("http://www.freeones.com")

if __name__ == '__main__':
    _test()