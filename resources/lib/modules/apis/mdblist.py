import xbmc
import requests
import datetime as dt
import time
from datetime import datetime
from typing import Dict, Any
from .base import BaseAPIClient
from ..databases import RatingsDatabase
from ..config import API_URLS, RATINGS_IMAGE_PATH


class MDbListClient(BaseAPIClient):
    def __init__(self, api_key: str, database: RatingsDatabase):
        super().__init__(API_URLS["mdblist"])
        self.api_key = api_key
        self.database = database

    def datetime_workaround(self, data, str_format):
        try:
            datetime_object = dt.datetime.strptime(data, str_format)
        except:
            datetime_object = dt.datetime(*(time.strptime(data, str_format)[0:6]))
        return datetime_object

    def get_ratings_from_api(
        self, id_with_type: str, media_type: str = "movie"
    ) -> Dict[str, Any]:
        # """Fetch ratings with database check first."""
        # # Check database cache first
        # cached_data = self.database.get_cached_ratings(id_with_type)
        # if cached_data:
        #     return cached_data

        # Only hit API if no cache
        try:
            if isinstance(id_with_type, str) and id_with_type.isdigit():
                url = f"{self.base_url}?apikey={self.api_key}&tm={id_with_type}&m={'show' if media_type == 'tv' else 'movie'}"
            else:
                url = f"{self.base_url}?apikey={self.api_key}&i={id_with_type}"

            response = self.session.get(url)
            if response.status_code == 200:
                result = self._process_response(response.json())
                if result:
                    self.database.update_ratings(id_with_type, result)
                return result
        except requests.RequestException:
            pass
        return {}

    def _process_response(self, json_data: Dict) -> Dict[str, Any]:
        """Process API response data."""
        try:
            data = {
                "imdbid": json_data.get("imdbid"),
                "tmdbid": json_data.get("tmdbid"),
            }

            # Process digital release info
            released_digital = json_data.get("released_digital")
            try:
                recent_days = int(
                    xbmc.getInfoLabel("Skin.String(nimbus_digital_release_window)")
                    or "7"
                )
                expired_days = int(
                    xbmc.getInfoLabel("Skin.String(nimbus_digital_expired_window)")
                    or "21"
                )
            except ValueError:
                recent_days = 7
                expired_days = 21

            if released_digital:
                try:
                    release_date = self.datetime_workaround(
                        released_digital, "%Y-%m-%d"
                    )
                    current_date = dt.datetime.now()
                    data["digital_release_date"] = release_date.strftime("%m/%d/%Y")
                    if release_date <= current_date:
                        days_since_release = (current_date - release_date).days
                        if days_since_release > expired_days:
                            data["digital_release_flag"] = "expired"
                        elif days_since_release <= recent_days:
                            data["digital_release_flag"] = "recently"
                        else:
                            data["digital_release_flag"] = "true"
                    else:
                        data["digital_release_flag"] = "false"
                except (ValueError, TypeError):
                    data["digital_release_flag"] = ""
                    data["digital_release_date"] = ""
            else:
                data["digital_release_flag"] = ""
                data["digital_release_date"] = ""

            # Process MDbList score
            score_average = json_data.get("score_average")
            if score_average is not None and score_average != 0:
                data["mdblistRating"] = str(score_average)
                data["mdblistImage"] = RATINGS_IMAGE_PATH + "mdblist.png"
            else:
                data["mdblistRating"] = ""
                data["mdblistImage"] = ""

            # Check for certified fresh status
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

            # Process individual ratings
            for rating in json_data.get("ratings", []):
                source = rating.get("source")
                value = rating.get("value")
                popular = rating.get("popular")

                if source == "imdb":
                    if value is not None and value != 0:
                        data["imdbRating"] = str(value)
                        data["imdbImage"] = RATINGS_IMAGE_PATH + "imdb.png"
                        if popular is not None:
                            data["popularRating"] = "#" + str(popular)
                            if popular <= 10:
                                data["popularImage"] = (
                                    RATINGS_IMAGE_PATH + "purpleflame.png"
                                )
                            elif 10 < popular <= 33:
                                data["popularImage"] = (
                                    RATINGS_IMAGE_PATH + "pinkflame.png"
                                )
                            elif 33 < popular <= 66:
                                data["popularImage"] = (
                                    RATINGS_IMAGE_PATH + "redflame.png"
                                )
                            elif 66 < popular <= 100:
                                data["popularImage"] = (
                                    RATINGS_IMAGE_PATH + "blueflame.png"
                                )
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
                    if value is not None and value != 0:
                        data["metascore"] = str(value)
                        data["metascoreImage"] = RATINGS_IMAGE_PATH + "metacritic.png"
                    else:
                        data["metascore"] = ""
                        data["metascoreImage"] = ""

                elif source == "trakt":
                    if value is not None and value != 0:
                        trakt_value = 10.0 if value == 100 else value / 10.0
                        data["traktRating"] = str(trakt_value)
                        data["traktImage"] = RATINGS_IMAGE_PATH + "trakt.png"
                    else:
                        data["traktRating"] = ""
                        data["traktImage"] = ""

                elif source == "letterboxd":
                    if value is not None and value != 0:
                        letterboxd_value = float(value) * 2
                        data["letterboxdRating"] = str(letterboxd_value)
                        data["letterboxdImage"] = RATINGS_IMAGE_PATH + "letterboxd.png"
                    else:
                        data["letterboxdRating"] = ""
                        data["letterboxdImage"] = ""

                elif source == "tomatoes":
                    if value is not None and value != 0:
                        data["tomatoMeter"] = str(value)
                        if is_certified_fresh == "true":
                            data["tomatoImage"] = RATINGS_IMAGE_PATH + "rtcertified.png"
                        elif value > 59:
                            data["tomatoImage"] = RATINGS_IMAGE_PATH + "rtfresh.png"
                        else:
                            data["tomatoImage"] = RATINGS_IMAGE_PATH + "rtrotten.png"
                    else:
                        data["tomatoMeter"] = ""
                        data["tomatoImage"] = ""

                elif source == "tomatoesaudience":
                    if value is not None and value != 0:
                        data["tomatoUserMeter"] = str(value)
                        if value > 59:
                            data["tomatoUserImage"] = RATINGS_IMAGE_PATH + "popcorn.png"
                        else:
                            data["tomatoUserImage"] = (
                                RATINGS_IMAGE_PATH + "popcorn_spilt.png"
                            )
                    else:
                        data["tomatoUserMeter"] = ""
                        data["tomatoUserImage"] = ""

                elif source == "tmdb":
                    if value is not None and value != 0:
                        data["tmdbRating"] = str(value / 10.0)
                        data["tmdbImage"] = RATINGS_IMAGE_PATH + "tmdb.png"
                    else:
                        data["tmdbRating"] = ""
                        data["tmdbImage"] = ""

            # Process trailer and collection info
            trailer = json_data.get("trailer", "")
            data["trailer"] = trailer if trailer else ""

            # Process collection flags
            keywords = json_data.get("keywords", [])
            data["first_in_collection"] = (
                "true"
                if next(
                    (i for i in keywords if i["name"] == "first-in-collection"), None
                )
                else "false"
            )

            data["collection_follow_up"] = (
                "true"
                if next(
                    (i for i in keywords if i["name"] == "collection-follow-up"), None
                )
                else "false"
            )

            data["belongs_to_collection"] = (
                "true"
                if next(
                    (i for i in keywords if i["name"] == "belongs-to-collection"), None
                )
                else "false"
            )

            return data

        except Exception as e:
            xbmc.log(f"Error processing MDbList response: {str(e)}", xbmc.LOGERROR)
            return {}
