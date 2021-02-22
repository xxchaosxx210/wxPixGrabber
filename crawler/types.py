from dataclasses import dataclass

@dataclass
class UrlData:
    url: str
    method: str = "GET"
    action: str = ""
    data: dict = None
    tag: str = ""


class Blacklist:

    """
    thread safe container class for storing global links
    this is to check there arent duplicate links
    saves a lot of time and less scraping
    """

    def __init__(self):
        self.items = []

    def clear(self):
        self.items.clear()
    
    def add(self, item):
        self.items.append(item.__dict__)
    
    def exists(self, item):
        try:
            index = self.items.index(item.__dict__)
        except ValueError:
            index = -1
        return index >= 0


@dataclass
class Message:
    """
    for message handling sending to and from threads
    thread - thread name
    type   - the type of message
    id     - the thread index
    status - the types status
    data   - extra data. Depends on message type
    """
    type: str
    thread: str
    id: int = 0
    status: str = ""
    data: dict = None


# @dataclass
# class Stats:
#     saved: int = 0
#     errors: int = 0
#     ignored: int = 0