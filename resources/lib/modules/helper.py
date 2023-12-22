import xbmc, xbmcgui, xbmcvfs, xbmcaddon
import json
import os
import hashlib
import urllib.request as urllib

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_DATA_PATH = os.path.join(
    xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID)
)
ADDON_DATA_IMG_PATH = os.path.join(
    xbmcvfs.translatePath("special://profile/addon_data/%s/image_cache" % ADDON_ID)
)
ADDON_DATA_IMG_TEMP_PATH = os.path.join(
    xbmcvfs.translatePath("special://profile/addon_data/%s/image_cache/temp" % ADDON_ID)
)


def md5hash(value):
    value = str(value).encode()
    return hashlib.md5(value).hexdigest()


def touch_file(filepath):
    os.utime(filepath, None)


def url_unquote(string):
    return urllib.unquote(string)


def winprop(key, value=None, clear=False, window_id=10000):
    window = xbmcgui.Window(window_id)

    if clear:
        window.clearProperty(key.replace(".json", "").replace(".bool", ""))

    elif value is not None:
        if key.endswith(".json"):
            key = key.replace(".json", "")
            value = json.dumps(value)

        elif key.endswith(".bool"):
            key = key.replace(".bool", "")
            value = "true" if value else "false"

        window.setProperty(key, value)

    else:
        result = window.getProperty(key.replace(".json", "").replace(".bool", ""))

        if result:
            if key.endswith(".json"):
                result = json.loads(result)
            elif key.endswith(".bool"):
                result = result in ("true", "1")

        return result


def clear_image_cache(params=None, path=ADDON_DATA_IMG_PATH, delete=False):
    if not delete:
        dialog = xbmcgui.Dialog()
        if dialog.yesno("Nimbus", "Are you sure you want to clear the image cache?"):
            delete = True

    if delete:
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:
                clear_image_cache(params, full_path, True)
