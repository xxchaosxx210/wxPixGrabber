__description__ = """
Creates images and thumbnails for the dummysite
"""

from PIL import Image
import os
import random
import PIL.ImageColor as ic

IMAGE_MAX = 148

IMAGE_PATH = f".{os.path.sep}images{os.path.sep}test_"
THUMBNAIL_PATH = f".{os.path.sep}thumbs{os.path.sep}test_"
EXT = ".jpg"

for index, color in enumerate(ic.colormap):
    # create the image
    img = Image.new(mode="RGB", size=(300, 300), color=ic.colormap.get(color))
    img.save(IMAGE_PATH + str(index) + EXT)
    img.close()

    # create the thumbnail
    img = Image.new(mode="RGB", size=(128, 128), color=ic.colormap.get(color))
    img.save(THUMBNAIL_PATH + str(index) + EXT)
    img.close()
