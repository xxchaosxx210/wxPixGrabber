from dataclasses import dataclass


@dataclass
class UrlData:
    """
    url: the URL link of the source
    method: GET or POST method
    action: if POST FORM request then action will contain the URL
    data: contains POST data to send
    tag: can be either A or IMG
    """
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
