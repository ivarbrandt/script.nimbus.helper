import xbmcvfs
from typing import Dict, Any

SETTINGS_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/"
)
RATINGS_DATABASE_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/script.nimbus.helper/ratings_cache.db"
)
RATINGS_IMAGE_PATH = "special://home/addons/skin.nimbus/resources/rating_images/"
PROFILE_PATH = xbmcvfs.translatePath(
    "special://userdata/addon_data/script.nimbus.helper/current_profile.json"
)

TMDB_API_KEY = "66a9a671e472b4dc34549c067deff536"

API_URLS = {
    "mdblist": "https://mdblist.com/api/",
    "tmdb": "https://api.themoviedb.org/3",
}

EMPTY_RATINGS: Dict[str, str] = {
    "digital_release_flag": "",
    "digital_release_date": "",
    "metascore": "",
    "metascoreImage": "",
    "traktRating": "",
    "traktImage": "",
    "letterboxdRating": "",
    "letterboxdImage": "",
    "mdblistRating": "",
    "mdblistImage": "",
    "tomatoMeter": "",
    "tomatoImage": "",
    "tomatoUserMeter": "",
    "tomatoUserImage": "",
    "imdbRating": "",
    "imdbImage": "",
    "popularRating": "",
    "popularImage": "",
    "tmdbRating": "",
    "tmdbImage": "",
    "first_in_collection": "",
    "collection_follow_up": "",
    "belongs_to_collection": "",
}

CACHE_DURATION_DAYS = 3
DEFAULT_DIGITAL_RELEASE_WINDOW = 7
VIDEO_ID_PATTERN = r"v=([a-zA-Z0-9_-]+)"
