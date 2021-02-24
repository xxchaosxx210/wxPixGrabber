import http.server

import multiprocessing as mp

import json
import base64

import crawler.constants as const
from crawler.constants import CMessage as Message


def _create_document(todo):
    html = f'''<html><head><title>{todo["title"]}</title></head><body>'''
    for link in iter(todo.get("links")):
        html += f'''<a href="{link["href"]}"><img src="{link["src"]}"></img></a>'''
    html += "</body></html>"
    return html

def _decode_base64(_base64):
    b = base64.b64decode(_base64)
    return b.decode("utf-8")

def server_process(host, port, a_queue):
    handler = ServerHandler
    handler.host = host
    handler.port = port
    handler.queue = a_queue
    running = http.server.HTTPServer((ServerHandler.host, ServerHandler.port), handler)
    running.serve_forever()


class ServerHandler(http.server.BaseHTTPRequestHandler):

    host = ""
    port = 5000
    queue = None
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
    
    def do_GET(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            "<html><head><title>PixGrabber Helper</title></head><body><h1>Please use the PixGrabber Chrome Extension</h1></body></html>".encode("utf-8"))
    
    def do_POST(self):
        if self.path == "/set-html":
            self._set_headers()
            b = self.rfile.read(int(self.headers["Content-Length"]))
            jstring = _decode_base64(b)
            todo = json.loads(jstring)
            html = _create_document(todo)
            url = f"http://{ServerHandler.host}:{ServerHandler.port}/set-html"
            ServerHandler.queue.put_nowait(Message(
                    thread=const.THREAD_SERVER, event=const.EVENT_SERVER_READY,
                    status=const.STATUS_OK, data={"html": html, 
                    "url": url}, id=0))
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
