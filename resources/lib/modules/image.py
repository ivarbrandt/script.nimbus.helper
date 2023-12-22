#!/usr/bin/python
# coding: utf-8

#################################################################################################

from __future__ import division

import xbmc
import xbmcaddon
import xbmcvfs
import os
from PIL import ImageFilter, Image, ImageOps, ImageEnhance
from .helper import *

#################################################################################################

BLUR_CONTAINER = xbmc.getInfoLabel("Skin.String(BlurContainer)") or 100000
BLUR_RADIUS = xbmc.getInfoLabel("Skin.String(BlurRadius)") or "40"
BLUR_SATURATION = xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.0"
OLD_IMAGE = ""

#################################################################################################


""" create image storage folders
"""
try:
    if not os.path.exists(ADDON_DATA_IMG_PATH):
        os.makedirs(ADDON_DATA_IMG_PATH)
        os.makedirs(ADDON_DATA_IMG_TEMP_PATH)

except OSError as e:
    # fix for race condition
    if e.errno != os.errno.EEXIST:
        raise
    pass


""" blur image and store result in addon data folder
"""


class ImageBlur:
    def __init__(self, prop="listitem", file=None, radius=None, saturation=None):
        global OLD_IMAGE
        self.image = (
            file
            if file is not None
            else xbmc.getInfoLabel("Control.GetLabel(%s)" % BLUR_CONTAINER)
        )
        self.radius = int(radius) if radius is not None else int(BLUR_RADIUS)
        self.saturation = (
            float(saturation) if saturation is not None else float(BLUR_SATURATION)
        )

        if self.image:
            if self.image != OLD_IMAGE:
                OLD_IMAGE = self.image

                self.filepath = self.blur()
                self.avgcolor = self.color()

                winprop(prop + "_blurred", self.filepath)
                winprop(prop + "_color", self.avgcolor)
                winprop(prop + "_color_noalpha", self.avgcolor[2:])

    def __str__(self):
        return self.filepath, self.avgcolor

    def blur(self):
        filename = (
            md5hash(self.image) + str(self.radius) + str(self.saturation) + ".png"
        )
        targetfile = os.path.join(ADDON_DATA_IMG_PATH, filename)

        try:
            if xbmcvfs.exists(targetfile):
                touch_file(targetfile)
            else:
                img = _openimage(self.image, ADDON_DATA_IMG_PATH, filename)
                img.thumbnail((200, 200), Image.ANTIALIAS)
                img = img.convert("RGB")
                img = img.filter(ImageFilter.GaussianBlur(self.radius))

                if self.saturation:
                    converter = ImageEnhance.Color(img)
                    img = converter.enhance(self.saturation)

                img.save(targetfile)

            return targetfile

        except Exception:
            return ""

    """ get average image color
    """

    def color(self):
        imagecolor = "FFF0F0F0"

        try:
            img = Image.open(self.filepath)
            imgResize = img.resize((1, 1), Image.ANTIALIAS)
            col = imgResize.getpixel((0, 0))
            imagecolor = "FF%s%s%s" % (
                format(col[0], "02x"),
                format(col[1], "02x"),
                format(col[2], "02x"),
            )

        except:
            pass

        return imagecolor


""" get cached images or copy to temp if file has not been cached yet
"""


def _openimage(image, targetpath, filename):
    # some paths require unquoting to get a valid cached thumb hash
    cached_image_path = url_unquote(image.replace("image://", ""))
    if cached_image_path.endswith("/"):
        cached_image_path = cached_image_path[:-1]

    cached_files = []
    for path in [
        xbmc.getCacheThumbName(cached_image_path),
        xbmc.getCacheThumbName(image),
    ]:
        cached_files.append(
            os.path.join("special://profile/Thumbnails/", path[0], path[:-4] + ".jpg")
        )
        cached_files.append(
            os.path.join("special://profile/Thumbnails/", path[0], path[:-4] + ".png")
        )
        cached_files.append(
            os.path.join("special://profile/Thumbnails/Video/", path[0], path)
        )

    for i in range(1, 4):
        try:
            """Try to get cached image at first"""
            for cache in cached_files:
                if xbmcvfs.exists(cache):
                    try:
                        img = Image.open(xbmcvfs.translatePath(cache))
                        return img

                    except Exception as error:
                        xbmc.log(
                            "Image error: Could not open cached image --> %s" % error, 2
                        )

            """ Skin images will be tried to be accessed directly. For all other ones
                the source will be copied to the addon_data folder to get access.
            """
            if xbmc.skinHasImage(image):
                if not image.startswith("special://skin"):
                    image = os.path.join("special://skin/media/", image)

                try:  # in case image is packed in textures.xbt
                    img = Image.open(xbmcvfs.translatePath(image))
                    return img

                except Exception:
                    return ""

            else:
                targetfile = os.path.join(targetpath, filename)
                if not xbmcvfs.exists(targetfile):
                    xbmcvfs.copy(image, targetfile)

                img = Image.open(targetfile)
                return img

        except Exception as error:
            xbmc.log(
                "Image error: Could not get image for %s (try %d) -> %s"
                % (image, i, error),
                2,
            )
            xbmc.sleep(500)
            pass

    return ""
