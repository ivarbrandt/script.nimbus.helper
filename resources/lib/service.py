import xbmc, xbmcgui
from threading import Thread
from modules.MDbList import *
from modules.image import *
import json

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


class Service(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.mdblist_api = MDbListAPI
        self.blur = ImageBlur
        self.last_set_imdb_id = None
        # self.last_imdb_id_played = None
        self.window = xbmcgui.Window
        self.get_window_id = xbmcgui.getCurrentWindowId
        self.get_infolabel = xbmc.getInfoLabel
        self.get_visibility = xbmc.getCondVisibility
        self.last_mediatype = ""
        self.last_imdb_id = None

    def run(self):
        image_thread = Thread(target=self.image_monitor)
        trailer_thread = Thread(target=self.trailer_monitor)
        trailer_thread.start()
        image_thread.start()
        while not self.abortRequested():
            self.ratings_monitor()
            self.waitForAbort(0.2)

    def pause_services(self):
        return self.window(self.get_window_id()).getProperty("pause_services") == "true"

    def not_nimbus(self):
        return xbmc.getSkinDir() != "skin.nimbus"

    def container_is_scrolling(self):
        return self.get_visibility("Container.Scrolling")

    def onNotification(self, sender, method, data):
        logger(
            "Notification received - Sender: {}, Method: {}, Data: {}".format(
                sender, method, data
            ),
            1,
        )
        if sender == "xbmc":
            if method in ("GUI.OnScreensaverActivated", "System.OnSleep"):
                self.window(self.get_window_id()).setProperty("pause_services", "true")
                logger("###Nimbus: Device is Asleep, PAUSING All Services", 1)
            elif method in ("GUI.OnScreensaverDeactivated", "System.OnWake"):
                self.window(self.get_window_id()).clearProperty("pause_services")
                logger("###Nimbus: Device is Awake, RESUMING All Services", 1)

    #     if method == "Player.OnStop":
    #         try:
    #             data = json.loads(data)
    #         except json.JSONDecodeError:
    #             logger("Error decoding JSON data: {}".format(data), 1)
    #             return
    #         item = data.get("item", {})
    #         mediatype = item.get("type", "")
    #         title = item.get("title", "").lower()
    #         logger("Extracted mediatype: '{}'".format(mediatype), 1)
    #         logger("Extracted title: '{}'".format(title), 1)
    #         if "trailer" in title and mediatype == "video":
    #             mediatype = "trailer"
    #         logger("Player stopped - MediaType: '{}'".format(mediatype), 1)
    #         if mediatype in ["movie", "episode"]:
    #             logger("Condition met for refreshing widgets - MediaType: '{}'".format(mediatype), 1)
    #             self.refresh_video_widgets(mediatype)
    #         else:
    #             logger("Condition not met - Skipping widget refresh for MediaType: '{}'".format(mediatype), 1)

    # def refresh_video_widgets(self, media_type):
    #     logger("Refreshing widgets - MediaType: {}".format(media_type), 1)
    #     timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    #     set_property = self.window(self.get_window_id()).setProperty
    #     set_property("widgetreload", timestr)
    #     logger("Set property 'widgetreload' to {}".format(timestr), 1)
    #     if media_type:
    #         set_property("widgetreload-%ss" % media_type, timestr)
    #         logger("Set property 'widgetreload-%ss' to {}".format(media_type, timestr), 1)
    #         if "episode" in media_type:
    #             set_property("widgetreload-tvshows", timestr)
    #             logger("Set property 'widgetreload-tvshows' to {}".format(timestr), 1)

    def ratings_monitor(self):
        while not self.abortRequested():
            if self.pause_services():
                self.waitForAbort(2)
                continue
            if self.not_nimbus():
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
            if self.container_is_scrolling():
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

    def trailer_monitor(self):
        while not self.abortRequested():
            if self.pause_services():
                self.waitForAbort(2)
                continue
            if self.not_nimbus():
                self.waitForAbort(15)
                continue
            trailer_setting = self.get_infolabel("Skin.String(trailerSetting)")
            if trailer_setting != "2":
                self.waitForAbort(2)
                continue
            if self.get_visibility(
                "Skin.HasSetting(TrailerPlaying)"
            ) or self.get_visibility("Player.HasMedia"):
                self.waitForAbort(2)
                continue
            if not self.get_visibility(
                "Window.IsVisible(home) | Window.IsVisible(11121) | Control.IsVisible(54) | Control.IsVisible(55)"
            ):
                self.waitForAbort(1)
                continue
            if self.container_is_scrolling():
                self.waitForAbort(0.2)
                continue
            current_dbtype = self.get_infolabel("ListItem.DBType")
            if current_dbtype in ["season", "episode"]:
                self.waitForAbort(0.5)
                continue
            current_imdb_id = self.get_infolabel("ListItem.IMDBNumber")
            if not current_imdb_id or not current_imdb_id.startswith("tt"):
                self.last_imdb_id = None
                self.waitForAbort(0.2)
                continue
            container_updating = self.get_visibility(f"Container.IsUpdating")
            wait_interval = self.get_infolabel("Skin.String(waitInterval)")
            wait_times = {
                "0": 3,
                "1": 5,
                "2": 7,
                "3": 9,
                "4": 11,
                "5": 13,
                "6": 15,
                "7": 20,
                "8": 25,
                "9": 30,
            }
            wait_time = wait_times.get(wait_interval, 5)
            if not container_updating:
                self.last_imdb_id = current_imdb_id
                wait_start_time = time.time()
                interrupted = False
                while time.time() - wait_start_time < wait_time:
                    controls_visible = self.get_visibility(
                        "ControlGroup(9000).HasFocus | Control.HasFocus(6130) | Control.HasFocus(6131) | Control.HasFocus(5199) | Control.HasFocus(531)"
                    )
                    if (
                        self.get_infolabel("ListItem.IMDBNumber") != current_imdb_id
                        or controls_visible
                    ):
                        interrupted = True
                        break
                    self.waitForAbort(0.2)
                if not interrupted:
                    play_trailer()
            self.waitForAbort(2)

    def image_monitor(self):
        while not self.abortRequested():
            if self.pause_services():
                self.waitForAbort(2)
                continue
            if self.not_nimbus():
                self.waitForAbort(15)
                continue
            if self.get_visibility("Skin.HasSetting(Enable.BackgroundBlur)"):
                radius = self.get_infolabel("Skin.String(BlurRadius)") or "40"
                saturation = self.get_infolabel("Skin.String(BlurSaturation)") or "2.0"
                self.blur(radius=radius, saturation=saturation)
                self.waitForAbort(0.2)
            else:
                self.waitForAbort(3)


if __name__ == "__main__":
    service = Service()
    service.run()
