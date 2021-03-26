import http.server
import json
import base64

import crawler.message as const
from crawler.message import Message

import os
from urllib.request import urljoin
import mimetypes
import re
from multiprocessing import Queue

MIME_TEXT = mimetypes.types_map.get(".html", "text/html")
MIME_JPG = mimetypes.types_map.get(".jpg", "image/jpg")

TEST_INDEX = "http://localhost:5000/"
TEST_URL = "/setup_test"
IMAGE_URL_RELATIVE = "/the_image"
THUMB_URL_RELATIVE = "/the_thumb"
IMAGE_URL_FULL = urljoin(TEST_INDEX, IMAGE_URL_RELATIVE)
THUMB_URL_FULL = urljoin(TEST_INDEX, THUMB_URL_RELATIVE)

IMAGE_RELATIVE_PATTERN = re.compile("^/the_image/test_[0-9]+\.jpg$")
THUMB_RELATIVE_PATTERN = re.compile("^/the_thumb/test_[0-9]+\.jpg$")

_TEST_SITE_PATH = os.path.join(os.getcwd(), f"crawler{os.path.sep}dummysite")
_TEST_SITE_IMAGES = os.path.join(_TEST_SITE_PATH, "images")
_TEST_SITE_THUMBS = os.path.join(_TEST_SITE_PATH, "thumbs")


def _create_document(todo: dict) -> str:
    html = f'''<html><head><title>{todo["title"]}</title></head><body>'''
    for link in iter(todo.get("links")):
        html += f'''<a href="{link["href"]}"><img src="{link["src"]}"></img></a>'''
    html += "</body></html>"
    return html


def _decode_base64(_base64: bytes) -> str:
    b = base64.b64decode(_base64)
    return b.decode("utf-8")


def server_process(host: str, port: int, a_queue: Queue):
    """sets up a background running HTTPServer and handler

    Args:
        host (str): The IP address of the Server localhost by Default
        port (int): Port address for the Server 5000 by Default
        a_queue (Queue): Queue object. A Message object will be sent. Create it from the calling process and setup a Queue loop to recieve the message
                         with a const.EVENT_SERVER_READY flag when a /set-html request has been sent from PixGrabber Browser extension.
                         example...
                         (Message) - thread (int): THREAD_SERVER
                                     event  (int): EVENT_SERVER_READY
                                     id     (int): 0
                                     status (int): STATUS_OK
                                     data   (dict): {url: str, html: str}
    """
    handler = _ServerHandler
    handler.host = host
    handler.port = port
    handler.queue = a_queue
    running = http.server.HTTPServer((_ServerHandler.host, _ServerHandler.port), handler)
    running.serve_forever()


def generate_dummy_html() -> str:
    """
    Generates the test server HTML
    """
    html = """<html><head><title>PixGrabber Dummy Site</title></head><body>"""
    with os.scandir(_TEST_SITE_IMAGES) as it:
        for entry in it:
            if entry.is_file() and entry.path.endswith(".jpg"):
                href = IMAGE_URL_FULL + "/" + entry.name
                src = THUMB_URL_FULL + "/" + entry.name
                html += f'<a href="{href}"><img src="{src}"></img></a>'
    html += "</body></html>"
    return html


class _ServerHandler(http.server.BaseHTTPRequestHandler):
    host = ""
    port = 5000
    queue = None

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", MIME_TEXT)
        self.end_headers()

    def _send_jpg(self, relative_path):
        # sends the requested image
        self.send_response(200)
        self.send_header("Content-Type", MIME_JPG)
        self.end_headers()
        # get the filename nd append to a full path
        path, filename = os.path.split(relative_path)
        if path == "/the_image":
            # full size image
            jpg_path = os.path.join(_TEST_SITE_IMAGES, filename)
        else:
            # thumbnail
            jpg_path = os.path.join(_TEST_SITE_THUMBS, filename)
        with open(jpg_path, "rb") as fp:
            self.wfile.write(fp.read())

    def do_GET(self):
        if self.path == TEST_URL:
            # test document requested
            self.send_response(200)
            self.send_header("Content-Type", MIME_TEXT)
            self.end_headers()
            html = generate_dummy_html()
            self.wfile.write(html.encode("utf-8"))
        elif IMAGE_RELATIVE_PATTERN.search(self.path) or THUMB_RELATIVE_PATTERN.search(self.path):
            # send the requested image
            self._send_jpg(self.path)
        else:
            # No path matches send 404
            self.send_response(404)
            self.send_header("Content-Type", MIME_TEXT)
            self.end_headers()
            self.wfile.write(
                "<html><head><title>PixGrabber Helper</title></head><body><h1>Please use the PixGrabber Chrome "
                "Extension</h1></body></html>".encode("utf-8"))

    def do_POST(self):
        if self.path == "/set-html":
            self._set_headers()
            b = self.rfile.read(int(self.headers["Content-Length"]))
            json_string = _decode_base64(b)
            todo = json.loads(json_string)
            html = _create_document(todo)
            url = f"http://{_ServerHandler.host}:{_ServerHandler.port}/set-html"
            _ServerHandler.queue.put_nowait(Message(
                thread=const.THREAD_SERVER, event=const.EVENT_SERVER_READY,
                status=const.STATUS_OK, data={"html": html,
                                              "url": url}))
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
