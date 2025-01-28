import xbmc, xbmcgui, xbmcvfs
from threading import Thread
from modules.logger import logger

from modules.monitors.ratings import RatingsMonitor
from modules.monitors.image import ImageMonitor, ImageBlur, ImageAnalysisConfig
from modules.databases.ratings import RatingsDatabase
from modules.config import SETTINGS_PATH


class Service(xbmc.Monitor):
    """Main service class that coordinates monitor and rating lookups."""

    def __init__(self):
        super().__init__()
        self._initialize()

    def _initialize(self):
        """Initialize service components."""
        if not xbmcvfs.exists(SETTINGS_PATH):
            xbmcvfs.mkdir(SETTINGS_PATH)

        self.home_window = xbmcgui.Window(10000)
        self.get_infolabel = xbmc.getInfoLabel
        self.get_visibility = xbmc.getCondVisibility
        self.image_monitor = ImageMonitor(ImageBlur, ImageAnalysisConfig())
        self.ratings_monitor = RatingsMonitor(RatingsDatabase(), self.home_window)

    def run(self):
        """Start the service and monitor."""
        self.image_monitor.start()
        while not self.abortRequested():
            if self._should_pause():
                self.waitForAbort(2)
                continue

            self.ratings_monitor.process_current_item()
            self.waitForAbort(0.2)

    def _should_pause(self):
        """Determine if service should pause."""
        if self.home_window.getProperty("pause_services") == "true":
            return True

        if xbmc.getSkinDir() != "skin.nimbus":
            return True

        if not self.get_infolabel("Skin.String(mdblist_api_key)"):
            return True

        if not self.get_visibility(
            "Window.IsVisible(videos) | Window.IsVisible(home) | Window.IsVisible(11121) | Window.IsActive(movieinformation) | [[Window.IsVisible(videoosd) | Window.IsVisible(seekbar)] + Skin.HasSetting(Enable.DetailedOSD) + !Skin.HasSetting(Disable.OSDRatings)]"
        ):
            return True

        return False

    def onNotification(self, sender, method, data):
        """Handle Kodi notifications."""
        # logger(
        #     "Notification received - Sender: {}, Method: {}, Data: {}".format(
        #         sender, method, data
        #     ),
        #     1,
        # )
        if sender == "xbmc":
            if method in ("GUI.OnScreensaverActivated", "System.OnSleep"):
                self.home_window.setProperty("pause_services", "true")
            elif method in ("GUI.OnScreensaverDeactivated", "System.OnWake"):
                self.home_window.clearProperty("pause_services")


if __name__ == "__main__":
    service = Service()
    service.run()
