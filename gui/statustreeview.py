import os
import wx
import webbrowser
from urllib.parse import urlparse
import wx.lib.agw.hypertreelist as HTL

import crawler.message as const

TEXT_DEFAULT = wx.Colour(45, 49, 55)
TEXT_MUTED = wx.Colour(105, 112, 122)
TEXT_PRIMARY = wx.Colour(30, 111, 232)
TEXT_SUCCESS = wx.Colour(37, 157, 78)
TEXT_IGNORED = wx.Colour(166, 105, 0)
TEXT_ERROR = wx.Colour(190, 45, 45)
ROW_SEARCHING = wx.Colour(229, 241, 255)
ROW_NORMAL = wx.Colour(255, 255, 255)
HEADER_BACKGROUND = wx.Colour(248, 249, 251)


def _format_size(path):
    if not path:
        return "-"
    try:
        size = os.path.getsize(path)
    except (OSError, TypeError):
        return "-"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


def _file_type(msg):
    data = getattr(msg, "data", {})
    value = data.get("path") or data.get("url") or ""
    try:
        value = urlparse(value).path
    except (TypeError, ValueError):
        pass
    ext = os.path.splitext(value)[1].lstrip(".")
    return ext.upper() if ext else "-"


def _result_status(msg):
    if msg.status == const.STATUS_OK:
        return "Saved"
    if msg.status == const.STATUS_ERROR:
        return "Error"
    detail = getattr(msg, "data", {}).get("message", "").lower()
    if "duplicate" in detail:
        return "Ignored (duplicate)"
    if "too small" in detail:
        return "Ignored (too small)"
    if "unknown file type" in detail:
        return "Ignored (type)"
    return "Ignored"


class StatusTreeView(HTL.HyperTreeList):

    class ItemPopup(wx.Menu):

        """PopupMenu for the TreeCtrl
        """

        def __init__(self, parent, item):
            super().__init__()
            self._text = parent.GetItemText(item)
            self._parent = parent
            self._item = item
            self.Append(100, "Copy", "Copy item to Clipboard")
            self.Append(101, "Open", "Try to open the Item")
            self.AppendSeparator()
            self.Append(102, "Info")
            self._parent.Bind(wx.EVT_MENU, lambda evt: self._on_copy(), id=100)
            self._parent.Bind(wx.EVT_MENU, lambda evt: self._on_open(), id=101)
            self._parent.Bind(wx.EVT_MENU, lambda evt: self.show_info(), id=102)

        def _on_open(self):
            msg = self._parent.GetItemData(self._item)
            if msg.event == const.EVENT_DOWNLOAD_IMAGE and msg.status == const.STATUS_OK:
                webbrowser.open(msg.data["path"])
            else:
                webbrowser.open(self._text)
        
        def _on_copy(self):
            data = wx.TextDataObject()
            data.SetText(self._text)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data)
                wx.TheClipboard.Close()
        
        def show_info(self):
            msg = self._parent.GetItemData(self._item)
            data = getattr(msg, "data", {"message": "", "path": ""})
            message = f'{data.get("message", "")}\n\n{data.get("path", "")}'
            wx.MessageBox(message, "Info", parent=self._parent)

    def __init__(self, parent: wx.Window, _id: int):
        self.children = {}
        super().__init__(
            parent=parent,
            id=_id,
            agwStyle=wx.TR_SINGLE | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_FULL_ROW_HIGHLIGHT
        )
        self.app = wx.GetApp()
        self.SetBackgroundColour(ROW_NORMAL)
        self.SetForegroundColour(TEXT_DEFAULT)

        self.AddColumn("Name / URL", width=520)
        self.AddColumn("Status", width=155)
        self.AddColumn("Size", width=95)
        self.AddColumn("Type", width=70)
        self.SetMainColumn(0)

        header_font = self.GetFont()
        header_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.SetHeaderFont(header_font)
        self.GetHeaderWindow().SetBackgroundColour(HEADER_BACKGROUND)

        self._create_image_list()
        self.clear()
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self._on_right_click)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def _on_size(self, evt):
        width = self.GetClientSize().width
        if width > 0:
            fixed_columns = 155 + 95 + 70 + 24
            self.SetColumnWidth(0, max(340, width - fixed_columns))
        evt.Skip()
    
    def _create_image_list(self):
        self.img_list = wx.ImageList(16, 16)
        self._img_link = self.img_list.Add(self.app.bitmaps["web"])
        self._img_src = self.img_list.Add(self.app.bitmaps["image"])
        self._img_error = self.img_list.Add(self.app.bitmaps["error"])
        self._img_ignored = self.img_list.Add(self.app.bitmaps["ignored"])
        self._img_saved = self.img_list.Add(self.app.bitmaps["saved"])
        self._img_search = self.img_list.Add(self.app.bitmaps["searching"])
        self._img_complete_ok = self.img_list.Add(self.app.bitmaps["complete"])
        self._img_complete_empty = self.img_list.Add(self.app.bitmaps["empty"])
        self.SetImageList(self.img_list)
    
    def _on_right_click(self, evt):
        menu = StatusTreeView.ItemPopup(self, evt.Item)
        self.PopupMenu(menu)
        menu.Destroy()

    def create_root(self, msg: const.Message):
        self.clear()
        root = self.AddRoot(msg.data["url"])
        self.SetItemData(root, msg)
        self.SetItemImage(root, self._img_link, wx.TreeItemIcon_Normal)
        self.SetItemImage(root, self._img_link, wx.TreeItemIcon_Expanded)
        self.SetItemText(root, "Fetching links...", column=1)
        self.SetItemText(root, "-", column=2)
        self.SetItemText(root, "-", column=3)
        self.SetItemTextColour(root, TEXT_PRIMARY)
        root_font = self.GetItemFont(root)
        root_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.SetItemFont(root, root_font)

    def set_root_status(self, message: str):
        root = self.GetRootItem()
        if root:
            self.SetItemText(root, message, column=1)

    def add_to_root(self, msg: const.Message):
        root = self.GetRootItem()
        url_data = msg.data["url_data"]
        index = msg.data["index"]
        child = self.AppendItem(root, url_data.url)
        self.children[index] = {"id": child, "children": {}}
        self.SetItemData(child, msg)
        self.SetItemText(child, "Pending", column=1)
        self.SetItemText(child, "-", column=2)
        self.SetItemText(child, _file_type(msg), column=3)
        if url_data.tag == "a":
            self.SetItemImage(child, self._img_link, wx.TreeItemIcon_Normal)
            self.SetItemImage(child, self._img_link, wx.TreeItemIcon_Expanded)
        else:
            self.SetItemImage(child, self._img_src, wx.TreeItemIcon_Normal)
            self.SetItemImage(child, self._img_src, wx.TreeItemIcon_Expanded)
        self.SetItemTextColour(child, TEXT_DEFAULT)
    
    def add_url(self, msg: const.Message):
        child = self.children[msg.id]
        new_child = self.AppendItem(child["id"], msg.data["url"])
        child_index = child["children"].__len__()
        child["children"][child_index] = {"id": new_child, "children": {}}

        if msg.status == const.STATUS_OK:
            bmp = self._img_saved
        elif msg.status == const.STATUS_ERROR:
            bmp = self._img_error
        else:
            bmp = self._img_ignored

        self.SetItemData(new_child, msg)
        self.SetItemImage(new_child, bmp, wx.TreeItemIcon_Normal)
        self.SetItemImage(new_child, bmp, wx.TreeItemIcon_Expanded)
        self.SetItemText(new_child, _result_status(msg), column=1)
        self.SetItemText(new_child, _format_size(msg.data.get("path", "")), column=2)
        self.SetItemText(new_child, _file_type(msg), column=3)
        self.SetItemTextColour(new_child, TEXT_DEFAULT)
    
    def set_searching(self, index: int):
        child = self.children[index]["id"]
        self.SetItemImage(child, self._img_search, wx.TreeItemIcon_Normal)
        self.SetItemImage(child, self._img_search, wx.TreeItemIcon_Expanded)
        self.SetItemText(child, "Searching...", column=1)
        self.SetItemTextColour(child, TEXT_DEFAULT)
        self.SetItemBackgroundColour(child, ROW_SEARCHING)
    
    def set_message(self, msg: const.Message):
        child = self.children[msg.id]["id"]
        if msg.data["message"] == "Task has completed":
            self.Expand(child)
        else:
            item = self.AppendItem(child, msg.data["message"])
            self.SetItemText(item, "-", column=1)
            self.SetItemText(item, "-", column=2)
            self.SetItemText(item, "-", column=3)
    
    def child_complete(self, msg: const.Message):
        """
        Appends a child item to the associated parent Link
        Args:
            msg: Message object sent from Commander Process

        Returns:

        """
        root_child = self.children[msg.id]["id"]
        children = self.children[msg.id]["children"]
        if children:
            img = self._img_complete_ok
            ok_result = list(filter(lambda child: self.GetItemData(child["id"]).status == const.STATUS_OK,
                                    children.values()))
            if not ok_result:
                error_result = list(filter(
                    lambda child: self.GetItemData(child["id"]).status == const.STATUS_ERROR, children.values()))
                if error_result:
                    img = self._img_error
                else:
                    img = self._img_ignored
            self.SetItemImage(root_child, img, wx.TreeItemIcon_Normal)
            self.SetItemImage(root_child, img, wx.TreeItemIcon_Expanded)
            if img == self._img_complete_ok:
                self.SetItemTextColour(root_child, TEXT_SUCCESS)
            elif img == self._img_error:
                self.SetItemTextColour(root_child, TEXT_ERROR)
            else:
                self.SetItemTextColour(root_child, TEXT_IGNORED)

        else:
            self.SetItemData(root_child, msg)
            self.SetItemImage(root_child, self._img_complete_empty, wx.TreeItemIcon_Normal)
            self.SetItemImage(root_child, self._img_complete_empty, wx.TreeItemIcon_Expanded)
            self.SetItemTextColour(root_child, TEXT_MUTED)
    
    def clear(self):
        self.DeleteAllItems()
        self.children.clear()

    def get_children(self, root: wx.TreeItemId) -> wx.TreeItemId:
        child, cookie = self.GetFirstChild(root)
        while child:
            child, cookie = self.GetFirstChild(root)
            yield child
