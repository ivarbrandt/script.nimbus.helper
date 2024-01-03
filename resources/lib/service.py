import xbmc, xbmcgui
from threading import Thread
from modules.MDbList import *
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


class TrailerService(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.last_imdb_id = None
        self.get_infolabel = xbmc.getInfoLabel
        self.get_visibility = xbmc.getCondVisibility
        self.window = xbmcgui.Window
        self.get_window_id = xbmcgui.getCurrentWindowId

    def trailer_monitor(self):
        # xbmc.log(
        #     "Trailer Monitor Service Started", xbmc.LOGINFO
        # )
        while not self.abortRequested():
            trailer_setting = self.get_infolabel("Skin.String(trailerSetting)")
            if trailer_setting != "2":
                # xbmc.log("Autotrailers not enabled", xbmc.LOGINFO)
                self.waitForAbort(2)
                continue
            if self.get_visibility(
                "Skin.HasSetting(TrailerPlaying)"
            ) or self.get_visibility("Player.HasMedia"):
                # xbmc.log("Media is currently playing", xbmc.LOGINFO)
                self.waitForAbort(2)
                continue
            if not self.get_visibility(
                "Window.IsVisible(home) | Window.IsVisible(11121) | Control.IsVisible(54) | Control.IsVisible(55)"
            ):
                # xbmc.log("Autotrailers not allowed in this window", xbmc.LOGINFO)
                self.waitForAbort(1)
                continue
            if self.get_visibility("Container.Scrolling"):
                # xbmc.log("Container is currently scrolling", xbmc.LOGINFO)
                self.waitForAbort(0.2)
                continue
            current_dbtype = self.get_infolabel("ListItem.DBType")
            if current_dbtype in ["season", "episode"]:
                # xbmc.log(
                #     "Autotrailers are not allowed for seasons or episodes", xbmc.LOGINFO
                # )
                self.waitForAbort(0.5)
                continue
            current_imdb_id = self.get_infolabel("ListItem.IMDBNumber")
            if not current_imdb_id or not current_imdb_id.startswith("tt"):
                # xbmc.log("Invalid IMDB ID", xbmc.LOGINFO)
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
                # xbmc.log(
                #     f"Preparing to wait for {wait_time} seconds before playing trailer",
                #     xbmc.LOGINFO,
                # )
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
                        # xbmc.log(
                        #     "IMDb ID changed, interrupting trailer playback.",
                        #     xbmc.LOGINFO,
                        # )
                        interrupted = True
                        break
                    self.waitForAbort(0.2)
                if not interrupted:
                    play_trailer()
                    # xbmc.log(
                    #     "Trailer played as wait was not interrupted.", xbmc.LOGINFO
                    # )
                # else:
                #     xbmc.log(
                #         "Wait was interrupted or a trailer is already playing; not playing trailer.",
                #         xbmc.LOGINFO,
                #     )

            self.waitForAbort(2)  # Wait a bit before next loop iteration

    # def trailer_monitor(self):
    #     xbmc.log("Trailer Monitor Service Started", xbmc.LOGINFO)  # Using xbmc.LOGINFO for clarity
    #     while not self.abortRequested():
    #         trailer_setting = self.get_infolabel("Skin.String(trailerSetting)")
    #         current_imdb_id = self.get_infolabel("ListItem.IMDBNumber")
    #         container_updating = self.get_visibility(f"Container.IsUpdating")
    #         trailer_ready = self.get_visibility("Skin.HasSetting(nimbus.trailer_ready)")
    #         wait_interval = self.get_infolabel("Skin.String(waitInterval)")

    #         # Define a mapping of waitInterval values to wait times
    #         wait_times = {'0': 3, '1': 5, '2': 7, '3': 9, '4': 11, '5': 13, '6': 15, '7': 20, '8': 25, '9': 30}
    #         wait_time = wait_times.get(wait_interval, 3)
    #         if (trailer_setting == '2' and
    #             not self.get_visibility("Skin.HasSetting(TrailerPlaying)") and not container_updating and
    #             current_imdb_id and
    #             self.last_imdb_id_played != current_imdb_id):

    #             xbmc.log(f"Attempting to play trailer after waiting for {wait_time} seconds", xbmc.LOGINFO)
    #             # Loop for the wait time, checking for changes in focus
    #             wait_start_time = time.time()  # Capture the start time of the wait
    #             while time.time() - wait_start_time < wait_time:
    #                 # Check if focus has changed
    #                 if not trailer_ready:
    #                     # Break out of the wait loop if focus changes or trailer_ready is reset
    #                     break
    #                 self.waitForAbort(0.5)  # Check every 0.5 seconds
    #             self.waitForAbort(wait_time)
    #             play_trailer()  # Ensure this function is defined and correctly implemented
    #             self.waitForAbort(1)  # Wait a brief moment before updating last_imdb_id_played
    #             self.last_imdb_id_played = current_imdb_id

    #         self.waitForAbort(2)


class RatingsService(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.mdblist_api = MDbListAPI
        self.last_set_imdb_id = None
        # self.last_imdb_id_played = None
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
            # if self.get_visibility("Skin.HasSetting(TrailerPlaying)"):
            #     self.waitForAbort(3)
            #     while xbmc.Player().isPlaying():
            #         if self.waitForAbort(0.5):
            #             break
            #     xbmc.executebuiltin("Skin.ToggleSetting(TrailerPlaying)")
            #     self.waitForAbort(0.2)
            #     continue
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
trailer_thread = Thread(target=TrailerService().trailer_monitor)
ratings_thread.start()
image_thread.start()
trailer_thread.start()
logger("###Nimbus: Services Finished", 1)
