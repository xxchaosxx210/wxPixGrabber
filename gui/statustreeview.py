import wx
import webbrowser

import crawler.message as const


class StatusTreeView(wx.TreeCtrl):

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
            webbrowser.open(self._text)
        
        def _on_copy(self):
            data = wx.TextDataObject()
            data.SetText(self._text)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(data)
                wx.TheClipboard.Close()
        
        def show_info(self):
            msg = self._parent.GetItemData(self._item)
            data = getattr(msg, "data", {"message": ""})
            wx.MessageBox(data.get("message", ""), "Info", parent=self._parent)

    def __init__(self, parent: wx.Window, _id: int):
        self.children = {}
        super().__init__(parent=parent, id=_id, style=wx.TR_SINGLE|wx.TR_NO_BUTTONS)
        self.app = wx.GetApp()
        self._create_image_list()
        self.clear()
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self._on_right_click, self)
    
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

    def add_to_root(self, msg: const.Message):
        root = self.GetRootItem()
        url_data = msg.data["url_data"]
        index = msg.data["index"]
        child = self.AppendItem(root, url_data.url)
        self.children[index] = {"id": child, "children": {}}
        self.SetItemData(child, msg)
        if url_data.tag == "a":
            self.SetItemImage(child, self._img_link, wx.TreeItemIcon_Normal)
            self.SetItemImage(child, self._img_link, wx.TreeItemIcon_Expanded)
        else:
            self.SetItemImage(child, self._img_src, wx.TreeItemIcon_Normal)
            self.SetItemImage(child, self._img_src, wx.TreeItemIcon_Expanded)
    
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
    
    def set_searching(self, index: int):
        child = self.children[index]["id"]
        self.SetItemImage(child, self._img_search, wx.TreeItemIcon_Normal)
        self.SetItemImage(child, self._img_search, wx.TreeItemIcon_Expanded)
    
    def set_message(self, msg: const.Message):
        child = self.children[msg.id]["id"]
        if msg.data["message"] == "Task has completed":
            self.Expand(child)
        else:
            self.AppendItem(child, msg.data["message"])
    
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

        else:
            self.SetItemData(root_child, msg)
            self.SetItemImage(root_child, self._img_complete_empty, wx.TreeItemIcon_Normal)
            self.SetItemImage(root_child, self._img_complete_empty, wx.TreeItemIcon_Expanded)
    
    def clear(self):
        self.DeleteAllItems()
        self.children.clear()

    def get_fetched_list(self, root: wx.TreeItemId):
        data = []
        child, cookie = self.GetFirstChild(root)
        while child:
            data.append(self.GetItemData(child))
            child, cookie = self.GetNextChild(child, cookie)
        return data
