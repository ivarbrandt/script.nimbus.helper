#!/usr/bin/python
# coding: utf-8

#################################################################################################

from __future__ import division

import xbmc
import xbmcaddon
import xbmcvfs
import os
from PIL import ImageFilter, Image, ImageOps, ImageEnhance, ImageStat
import math
import colorsys
from .helper import *

#################################################################################################

BLUR_CONTAINER = xbmc.getInfoLabel("Skin.String(BlurContainer)") or 100000
BLUR_RADIUS = xbmc.getInfoLabel("Skin.String(BlurRadius)") or "30"
BLUR_SATURATION = xbmc.getInfoLabel("Skin.String(BlurSaturation)") or "1.5"
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
                winprop(prop + "_color_noalpha", self.avgcolor[2:])
                winprop(prop + "_color", self.avgcolor)

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
                img.thumbnail((200, 200), Image.LANCZOS)
                img = img.convert("RGB")

                # Analyze image contrast and brightness
                contrast_level, brightness_level = self.analyze_image(img)

                # Adaptive brightness reduction for very bright images
                if brightness_level > 0.7:
                    reducer = ImageEnhance.Brightness(img)
                    reduction_factor = 1 - (brightness_level - 0.7) * 0.5
                    img = reducer.enhance(reduction_factor)

                # Initial color enhancement (adaptive and balanced)
                enhancer = ImageEnhance.Color(img)
                color_enhance_factor = 1.2 + (0.08 * (1 - contrast_level))
                img = enhancer.enhance(color_enhance_factor)

                # Multi-pass adaptive blur
                for i in range(3):
                    blur_radius = self.radius * (i + 1) / 3
                    img = img.filter(ImageFilter.GaussianBlur(blur_radius))

                    # Apply subtle edge preservation for high-contrast images
                    if contrast_level > 0.5:
                        edge_preserve = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
                        img = Image.blend(img, edge_preserve, 0.15 * contrast_level)

                # Adjust contrast (adaptive)
                contrast = ImageEnhance.Contrast(img)
                contrast_factor = 1.04 + (0.04 * (1 - contrast_level))
                img = contrast.enhance(contrast_factor)

                # Final saturation adjustment (adaptive and balanced)
                if self.saturation:
                    converter = ImageEnhance.Color(img)
                    saturation_factor = self.saturation * (
                        1.05 + (0.15 * (1 - contrast_level))
                    )
                    img = converter.enhance(saturation_factor)

                with open(targetfile, "wb") as f:
                    img.save(f, "PNG")

            return targetfile

        except Exception:
            return ""

    def analyze_image(self, img):
        stat = ImageStat.Stat(img)
        r, g, b = stat.mean
        rm, gm, bm = stat.stddev

        # Calculate contrast level
        contrast_level = (
            math.sqrt(0.241 * (rm**2) + 0.691 * (gm**2) + 0.068 * (bm**2)) / 100
        )
        contrast_level = min(contrast_level, 1.0)

        # Calculate brightness level
        brightness_level = (r + g + b) / (3 * 255)

        return contrast_level, brightness_level

    """ get average image color
    """

    def color(self):
        default_color = "FFF0F0F0"
        min_brightness = 0.7  # Adjust this value to set the minimum brightness

        try:
            with Image.open(self.filepath) as img:
                img_resize = img.resize((1, 1), Image.LANCZOS)
                col = img_resize.getpixel((0, 0))

            # Convert RGB to HSV
            h, s, v = colorsys.rgb_to_hsv(col[0] / 255, col[1] / 255, col[2] / 255)

            # Adjust brightness if it's too low
            if v < min_brightness:
                v = min_brightness

            # Convert back to RGB
            r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]

            imagecolor = f"FF{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            print(f"Error processing image: {e}")
            imagecolor = default_color

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
            for cache in cached_files:
                if xbmcvfs.exists(cache):
                    try:
                        with Image.open(xbmcvfs.translatePath(cache)) as img:
                            return img.copy()  # Return a copy of the image
                    except Exception as error:
                        xbmc.log(
                            "Image error: Could not open cached image --> %s" % error, 2
                        )

            if xbmc.skinHasImage(image):
                if not image.startswith("special://skin"):
                    image = os.path.join("special://skin/media/", image)

                try:
                    with Image.open(xbmcvfs.translatePath(image)) as img:
                        return img.copy()  # Return a copy of the image
                except Exception:
                    return ""

            else:
                targetfile = os.path.join(targetpath, filename)
                if not xbmcvfs.exists(targetfile):
                    xbmcvfs.copy(image, targetfile)

                with Image.open(targetfile) as img:
                    return img.copy()  # Return a copy of the image

        except Exception as error:
            xbmc.log(
                "Image error: Could not get image for %s (try %d) -> %s"
                % (image, i, error),
                2,
            )
            xbmc.sleep(500)
            pass

    return ""
