__description__ = "checks mime type and returns true"
__version__ = "0.1"

import os

TYPES_BITMAP = ('image/bmp', "image/x-windows-bmp")
TYPE_GIF = "image/gif"
TYPE_HTML = "text/html"
TYPE_ICON = "image/x-icon"
TYPES_JPEG = ("image/jpeg", "image/pjpeg")
TYPE_OCTET_STREAM = "application/octet-stream"
TYPE_PNG = "image/png"
TYPE_TGA = "image/tga"
TYPES_TIFF = ("image/tiff", "image/x-tiff")

extensions = {".jpg": TYPES_JPEG[0], ".jpeg": TYPES_JPEG[0], ".bmp": TYPES_BITMAP[0], ".gif": TYPE_GIF,
              ".html": TYPE_HTML, ".ico": TYPE_ICON, ".bin": TYPE_OCTET_STREAM, ".a": TYPE_OCTET_STREAM,
              ".png": TYPE_PNG, ".tga": TYPE_TGA, ".tiff": TYPES_TIFF[0], ".tif": TYPES_TIFF[0]}

def guess_mime_from_ext(extension):
    """get the content-type from the file extension

    Args:
        extension (str): File extension to find the mime type with

    Returns:
        [str]: The mime type associated with the extension. Or unknown if none found
    """
    return extensions.get(extension, "unknown")

def is_jpeg(mime_type):
    return mime_type in TYPES_JPEG

def is_gif(mime_type):
    return mime_type == TYPE_GIF

def is_html(mime_type):
    return TYPE_HTML in mime_type

def is_icon(mime_type):
    return mime_type == TYPE_ICON

def is_bitmap(mime_type):
    return mime_type in TYPES_BITMAP

def is_octet_stream(mime_type):
    return mime_type == TYPE_OCTET_STREAM

def is_png(mime_type):
    return mime_type == TYPE_PNG

def is_tiff(mime_type):
    return mime_type in TYPES_TIFF

def is_tga(mime_type):
    return mime_type == TYPE_TGA

def is_valid_content_type(url, content_type, valid_types):
    """Checks the MIME type to make sure it matches with a valid type either HTML or Image
    if an application/octet-stream is encountered the extension is used from the Url instead

    Args:
        url (str): The Source of the MIME type
        content_type (str): MIME type
        valid_types (dict): key, value pair of extension without the dot and boolean whether its valid.
                            example: {'jpg': True}, will only include jpg mime types and ignore other image formats

    Returns:
        [str]: returns the ext if a match is found or empty string if no match found
    """

    # check file attachement first and get its type
    if is_octet_stream(content_type):
        # file attachemnt use the extension from the url
        try:
            content_type = guess_mime_from_ext(os.path.splitext(url)[1])
        except IndexError:
            return ""
    ext = ""
    # HTML
    if is_html(content_type):
        ext = ".html"
    # JPEG
    elif is_jpeg(content_type):
        if valid_types.get("jpg", False):
            ext = ".jpg"
    # PNG
    elif is_png(content_type):
        if valid_types.get("png", False):
            ext = ".png"
    # BITMAP
    elif is_bitmap(content_type):
        if valid_types.get("bmp", False):
            ext = ".bmp"
    # GIF
    elif is_gif(content_type):
        if valid_types.get("gif", False):
            ext = ".gif"
    # ICON
    elif is_icon(content_type):
        if valid_types.get("ico", False):
            ext = ".ico"
    # TIFF
    elif is_tiff(content_type):
        if valid_types.get("tiff", False):
            ext = ".tiff"
    # TGA 
    elif is_tga(content_type):
        if valid_types.get("tga", False):
            ext = ".tga"
    return ext