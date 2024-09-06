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
        is_certified_fresh = (
            "true"
            if next(
                (
                    i
                    for i in json_data.get("keywords", [])
                    if i["name"] == "certified-fresh"
                ),
                None,
            )
            else "false"
        )
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
                    if is_certified_fresh == "true":
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
            data["first_in_collection"] = (
                "true"
                if next(
                    (
                        i
                        for i in json_data.get("keywords", [])
                        if i["name"] == "first-in-collection"
                    ),
                    None,
                )
                else "false"
            )
            data["collection_follow_up"] = (
                "true"
                if next(
                    (
                        i
                        for i in json_data.get("keywords", [])
                        if i["name"] == "collection-follow-up"
                    ),
                    None,
                )
                else "false"
            )
            data["belongs_to_collection"] = (
                "true"
                if next(
                    (
                        i
                        for i in json_data.get("keywords", [])
                        if i["name"] == "belongs-to-collection"
                    ),
                    None,
                )
                else "false"
            )
        return data


def play_trailer():
    if not xbmc.getCondVisibility(
        "String.IsEmpty(Window(Home).Property(nimbus.trailer_ready))"
    ):
        is_episode = xbmc.getCondVisibility("String.IsEqual(ListItem.DBType,episode)")
        is_season = xbmc.getCondVisibility("String.IsEqual(ListItem.DBType,season)")
        if xbmc.getCondVisibility("Control.IsVisible(500) | Control.IsVisible(501)"):
            xbmc.executebuiltin(
                "Notification(Trailer Playback, Trailer playback is not available in this view, 3000)"
            )
        elif not (is_episode or is_season):
            trailer_source = xbmc.getInfoLabel("Skin.String(TrailerSource)")
            play_url = None
            if trailer_source == "0":
                play_url = xbmc.getInfoLabel("ListItem.Trailer")
            elif trailer_source == "1":
                play_url = xbmc.getInfoLabel("Skin.String(TrailerPlaybackURL)")
            if play_url:
                xbmc.executebuiltin("Skin.SetString(TrailerPlaying, true)")
                if xbmc.getCondVisibility(
                    "Control.IsVisible(50) | Control.IsVisible(51)"
                ):
                    xbmc.executebuiltin(f"PlayMedia({play_url},0,noresume)")
                else:
                    xbmc.executebuiltin(f"PlayMedia({play_url},1,noresume)")


def check_api_key(api_key):
    api_url = "https://mdblist.com/api/"
    params = {
        "apikey": api_key,
        "i": "tt0111161",
    }
    try:
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return ("valid", "ratings" in data and len(data["ratings"]) > 0)
    except requests.RequestException:
        return ("error", None)


def validate_api_key(api_key, silent=True):
    if not api_key:
        xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        return
    xbmc.executebuiltin("Skin.SetString(checking_api_key,true)")
    try:
        status, is_valid = check_api_key(api_key)
        if status == "valid" and is_valid:
            xbmc.executebuiltin("Skin.SetString(valid_api_key,true)")
            if not silent:
                xbmcgui.Dialog().notification(
                    "Success",
                    "Features activated",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
        elif status == "valid" and not is_valid:
            xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        else:
            if not silent:
                xbmcgui.Dialog().notification(
                    "Connection Error",
                    "Unable to reach MDbList",
                    xbmcgui.NOTIFICATION_INFO,
                    3000,
                )
    finally:
        xbmc.executebuiltin("Skin.Reset(checking_api_key)")


def set_api_key():
    current_key = xbmc.getInfoLabel("Skin.String(mdblist_api_key)")
    keyboard = xbmc.Keyboard(current_key, "Enter MDbList API Key")
    keyboard.doModal()
    if keyboard.isConfirmed():
        new_key = keyboard.getText()
        if not new_key:
            xbmc.executebuiltin("Skin.Reset(mdblist_api_key)")
            xbmc.executebuiltin("Skin.Reset(valid_api_key)")
        else:
            xbmc.executebuiltin(f'Skin.SetString(mdblist_api_key,"{new_key}")')
            validate_api_key(new_key, silent=False)


def check_api_key_on_load():
    api_key = xbmc.getInfoLabel("Skin.String(mdblist_api_key)")
    validate_api_key(api_key, silent=True)
