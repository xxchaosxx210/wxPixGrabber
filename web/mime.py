__description__ = "checks mime type and returns true"
__version__ = "0.1"

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