import xbmc, xbmcgui, xbmcvfs
import datetime as dt
import sqlite3 as database
import time
import requests
import json
import re

# logger = xbmc.log

settings_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/"
)
ratings_database_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/ratings_cache.db"
)
IMAGE_PATH = "special://home/addons/skin.nimbus/resources/rating_images/"


def make_session(url="https://"):
    session = requests.Session()
    session.mount(url, requests.adapters.HTTPAdapter(pool_maxsize=100))
    return session


api_url = "https://mdblist.com/api/?apikey=%s&i=%s"
session = make_session("https://www.mdblist.com/")


class MDbListAPI:
    last_checked_imdb_id = None

    def __init__(self):
        self.connect_database()

    def connect_database(self):
        if not xbmcvfs.exists(settings_path):
            xbmcvfs.mkdir(settings_path)
        self.dbcon = database.connect(ratings_database_path, timeout=60)
        self.dbcon.execute(
            """
        CREATE TABLE IF NOT EXISTS ratings (
            imdb_id TEXT PRIMARY KEY,
            ratings TEXT,
            last_updated TIMESTAMP
        );
        """
        )
        self.dbcur = self.dbcon.cursor()

    def datetime_workaround(self, data, str_format):
        try:
            datetime_object = dt.datetime.strptime(data, str_format)
        except:
            datetime_object = dt.datetime(*(time.strptime(data, str_format)[0:6]))
        return datetime_object

    def insert_or_update_ratings(self, imdb_id, ratings):
        ratings_data = json.dumps(ratings)
        self.dbcur.execute(
            """
            INSERT OR REPLACE INTO ratings (imdb_id, ratings, last_updated)
            VALUES (?, ?, ?)
            """,
            (imdb_id, ratings_data, dt.datetime.now()),
        )
        self.dbcon.commit()

    def delete_all_ratings(self):
        self.dbcur.execute("DELETE FROM ratings")
        self.dbcon.commit()
        dialog = xbmcgui.Dialog()
        dialog.ok("Nimbus", "All ratings have been cleared from the database.")

    def get_cached_info(self, imdb_id):
        self.dbcur.execute(
            "SELECT imdb_id, ratings, last_updated FROM ratings WHERE imdb_id=?",
            (imdb_id,),
        )
        entry = self.dbcur.fetchone()
        if entry:
            _, ratings_data, last_updated = entry
            ratings = json.loads(ratings_data)
            last_updated_date = self.datetime_workaround(
                last_updated, "%Y-%m-%d %H:%M:%S.%f"
            )
            if dt.datetime.now() - last_updated_date < dt.timedelta(days=7):
                return ratings
        return None

    def fetch_info(self, meta, api_key):
        imdb_id = meta.get("imdb_id")
        if not imdb_id or not api_key:
            return {}
        cached_info = self.get_cached_info(imdb_id)
        if cached_info:
            return cached_info
        data = self.get_result(imdb_id, api_key)
        self.insert_or_update_ratings(imdb_id, data)
        return data

    def get_result(self, imdb_id, api_key):
        url = api_url % (api_key, imdb_id)
        response = requests.get(url)
        if response.status_code != 200:
            return {}
        json_data = response.json()
        ratings = json_data.get("ratings", [])
        data = {}
        for rating in ratings:
            source = rating.get("source")
            value = rating.get("value")
            popular = rating.get("popular")
            if source == "imdb":
                if value is not None:
                    data["imdbRating"] = str(value)
                    data["imdbImage"] = IMAGE_PATH + "imdb.png"
                    if popular is not None:
                        data["popularRating"] = "#" + str(popular)
                        if popular <= 10:
                            data["popularImage"] = IMAGE_PATH + "purpleflame.png"
                        elif 10 < popular <= 33:
                            data["popularImage"] = IMAGE_PATH + "pinkflame.png"
                        elif 33 < popular <= 66:
                            data["popularImage"] = IMAGE_PATH + "redflame.png"
                        elif 66 < popular <= 100:
                            data["popularImage"] = IMAGE_PATH + "blueflame.png"
                        else:
                            data["popularRating"] = ""
                            data["popularImage"] = ""
                    else:
                        data["popularRating"] = ""
                        data["popularImage"] = ""
                else:
                    data["imdbRating"] = ""
                    data["imdbImage"] = ""
                    data["popularRating"] = ""
                    data["popularImage"] = ""
            elif source == "metacritic":
                if value is not None:
                    data["metascore"] = str(value)
                    data["metascoreImage"] = IMAGE_PATH + "metacritic.png"
                else:
                    data["metascore"] = ""
                    data["metascoreImage"] = ""
            elif source == "tomatoes":
                if value is not None:
                    data["tomatoMeter"] = str(value)
                    if value > 74:
                        data["tomatoImage"] = IMAGE_PATH + "rtcertified.png"
                    elif value > 59:
                        data["tomatoImage"] = IMAGE_PATH + "rtfresh.png"
                    else:
                        data["tomatoImage"] = IMAGE_PATH + "rtrotten.png"
                else:
                    data["tomatoMeter"] = ""
                    data["tomatoImage"] = ""
            elif source == "tomatoesaudience":
                if value is not None:
                    data["tomatoUserMeter"] = str(value)
                    if value > 59:
                        data["tomatoUserImage"] = IMAGE_PATH + "popcorn.png"
                    else:
                        data["tomatoUserImage"] = IMAGE_PATH + "popcorn_spilt.png"
                else:
                    data["tomatoUserMeter"] = ""
                    data["tomatoUserImage"] = ""
            elif source == "tmdb":
                if value is not None:
                    data["tmdbRating"] = str(value / 10.0)
                    data["tmdbImage"] = IMAGE_PATH + "tmdb.png"
                else:
                    data["tmdbRating"] = ""
                    data["tmdbImage"] = ""
            trailer = json_data.get("trailer", "")
            if not trailer:
                trailer = ""
            data["trailer"] = trailer
        return data


def play_trailer_in_window(play_url):
    list_item = xbmcgui.ListItem(path=play_url)
    xbmc.Player().play(play_url, list_item, windowed=True)


def play_trailer():
    if xbmc.getCondVisibility("!String.IsEmpty(Skin.String(mdblist_api_key))"):
        if not xbmc.getCondVisibility(
            "String.IsEmpty(Window.Property(nimbus.trailer_ready))"
        ):
            trailer_url = xbmc.getInfoLabel("Window.Property(nimbus.trailer)")
            if trailer_url:
                match = re.search(r"v=([a-zA-Z0-9_-]+)", trailer_url)
                if match:
                    video_id = match.group(1)
                    xbmc.executebuiltin("Skin.SetBool(TrailerPlaying)")
                    play_url = (
                        "plugin://plugin.video.youtube/play/?video_id=" + video_id
                    )
                    play_trailer_in_window(play_url)


# def autoplay_trailer():
#     xbmc.log("Autoplay Trailer Triggered", xbmc.LOGINFO)
#     xbmc.executebuiltin("Skin.SetBool(WaitInProgress)")
#     wait_interval = xbmc.getInfoLabel("Skin.String(waitInterval)")
#     window_id = xbmcgui.getCurrentWindowId()
#     window = xbmcgui.Window(window_id)
#     previous_focus_id = window.getFocusId()
#     previous_control_id = xbmc.getInfoLabel(f"Container({previous_focus_id}).CurrentItem")
#     wait_times = {'0': 3, '1': 5, '2': 7, '3': 9, '4': 11, '5': 13, '6': 15, '7': 20, '8': 25, '9': 30}
#     wait_time = wait_times.get(wait_interval, 5)
#     wait_start_time = time.time()
#     while time.time() - wait_start_time < wait_time:
#         current_focus_id = window.getFocusId()
#         current_control_id = xbmc.getInfoLabel(f"Container({current_focus_id}).CurrentItem")
#         if current_control_id != previous_control_id or previous_focus_id != current_focus_id:
#             xbmc.log("Wait has been interrupted. Exiting loop.", xbmc.LOGINFO)
#             xbmc.executebuiltin("Skin.Reset(WaitInProgress)")
#             return
#         xbmc.sleep(500)
#     play_trailer()
#     xbmc.executebuiltin("Skin.Reset(WaitInProgress)")


def set_api_key():
    keyboard = xbmc.Keyboard("", "Enter MDbList API Key")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        xbmc.executebuiltin(f"Skin.SetString(mdblist_api_key,{keyboard.getText()})")
