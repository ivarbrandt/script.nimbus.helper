import xbmc, xbmcgui
from threading import Thread
from modules.MDbList import MDbListAPI
from modules.image import *
import json
import xbmcaddon

logger = xbmc.log
empty_ratings = {
    "metascore": "",
    "tomatoMeter": "",
    "tomatoUserMeter": "",
    "tomatoImage": "",
    "imdbRating": "",
    "popularRating": "",
    "tmdbRating": "",
}


class RatingsService(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.mdblist_api = MDbListAPI
        self.last_set_imdb_id = None
        self.window = xbmcgui.Window
        self.get_window_id = xbmcgui.getCurrentWindowId
        self.get_infolabel = xbmc.getInfoLabel
        self.get_visibility = xbmc.getCondVisibility

    def onNotification(self, sender, method, data):
        if sender == "xbmc":
            if method in ("GUI.OnScreensaverActivated", "System.OnSleep"):
                self.window(self.get_window_id()).setProperty("pause_services", "true")
                logger("###Nimbus: Device is Asleep, PAUSING Ratings Service", 1)
            elif method in ("GUI.OnScreensaverDeactivated", "System.OnWake"):
                self.window(self.get_window_id()).clearProperty("pause_services")
                logger("###Nimbus: Device is Awake, RESUMING Ratings Service", 1)

    def listitem_monitor(self):
        while not self.abortRequested():
            if (
                self.window(self.get_window_id()).getProperty("pause_services")
                == "true"
            ):
                self.waitForAbort(2)
                continue
            if xbmc.getSkinDir() != "skin.nimbus":
                self.waitForAbort(15)
                continue
            api_key = self.get_infolabel("Skin.String(mdblist_api_key)")
            if not api_key:
                self.waitForAbort(10)
                continue
            if not self.get_visibility(
                "Window.IsVisible(videos) | Window.IsVisible(home) | Window.IsVisible(11121)"
            ):
                self.waitForAbort(2)
                continue
            if self.get_visibility("Container.Scrolling"):
                self.waitForAbort(0.2)
                continue
            if self.get_visibility("Skin.HasSetting(TrailerPlaying)"):
                self.waitForAbort(3)
                while xbmc.Player().isPlaying():
                    if self.waitForAbort(0.5):
                        break
                xbmc.executebuiltin("Skin.ToggleSetting(TrailerPlaying)")
                self.waitForAbort(0.2)
                continue
            imdb_id = self.get_infolabel("ListItem.IMDBNumber")
            set_property = self.window(self.get_window_id()).setProperty
            get_property = self.window(self.get_window_id()).getProperty
            clear_property = self.window(self.get_window_id()).clearProperty
            cached_ratings = get_property(f"nimbus.cachedRatings.{imdb_id}")
            if not imdb_id or not imdb_id.startswith("tt"):
                clear_property("nimbus.trailer_ready")
                for k, v in empty_ratings.items():
                    set_property("nimbus.%s" % k, v)
                self.last_set_imdb_id = None
                self.waitForAbort(0.2)
                continue
            current_trailer_ready_status = get_property("nimbus.trailer_ready")
            if imdb_id == self.last_set_imdb_id:
                if current_trailer_ready_status != "true":
                    set_property("nimbus.trailer_ready", "true")
                    self.waitForAbort(0.2)
                    continue
            else:
                clear_property("nimbus.trailer_ready")
            if cached_ratings:
                result = json.loads(cached_ratings)
                for k, v in result.items():
                    set_property("nimbus.%s" % k, v)
                self.last_set_imdb_id = imdb_id
                self.waitForAbort(0.2)
                continue
            Thread(target=self.set_ratings, args=(api_key, imdb_id)).start()
            self.waitForAbort(0.2)

    def set_ratings(self, api_key, imdb_id):
        set_property = self.window(self.get_window_id()).setProperty
        result = self.mdblist_api().fetch_info({"imdb_id": imdb_id}, api_key)
        if result:
            set_property(f"nimbus.cachedRatings.{imdb_id}", json.dumps(result))
            for k, v in result.items():
                set_property("nimbus.%s" % k, v)


class ImageService(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.blur = ImageBlur
        self.get_visibility = xbmc.getCondVisibility
        self.get_infolabel = xbmc.getInfoLabel

    def image_monitor(self):
        while not self.abortRequested():
            if self.get_visibility("Skin.HasSetting(Enable.BackgroundBlur)"):
                radius = self.get_infolabel("Skin.String(BlurRadius)") or "40"
                saturation = self.get_infolabel("Skin.String(BlurSaturation)") or "2.0"
                self.blur(radius=radius, saturation=saturation)
                self.waitForAbort(0.2)
            else:
                self.waitForAbort(2)


logger("###Nimbus: Services Started", 1)
ratings_thread = Thread(target=RatingsService().listitem_monitor)
image_thread = Thread(target=ImageService().image_monitor)
ratings_thread.start()
image_thread.start()
logger("###Nimbus: Services Finished", 1)
