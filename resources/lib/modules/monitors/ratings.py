import xbmc
import xbmcgui
from threading import Thread, Lock
import json
import re
from typing import Optional, Tuple, Dict, Any
from ..config import *
from ..databases import RatingsDatabase
from ..apis import MDbListClient, TMDbClient


class RatingsMonitor:
    """Monitors and manages media ratings."""

    def __init__(self, database: RatingsDatabase, home_window: xbmcgui.Window):
        self.database = database
        self.home_window = home_window
        self.get_infolabel = xbmc.getInfoLabel
        self.get_property = self.home_window.getProperty
        self.set_property = self.home_window.setProperty
        self.clear_property = self.home_window.clearProperty
        self.tmdb_client = TMDbClient(TMDB_API_KEY)

        # State tracking
        self.last_set_id = None
        self.pending_id = None
        self.last_trailer_id = None
        self.current_ratings_thread = None
        self._rating_lock = Lock()

    def process_current_item(self) -> None:
        """Process the current media item."""
        meta = self._get_current_item_meta()
        if not meta:
            # self._clear_ratings_properties()
            return

        media_id = meta.get("id")
        if not media_id:
            return

        self._handle_trailer_update(media_id)

        if media_id != self.last_set_id or media_id != self.pending_id:
            self._process_ratings(media_id, meta)

    def _process_ratings(self, media_id: str, meta: Dict[str, Any]) -> None:
        """Process ratings for the current item."""
        with self._rating_lock:
            # First check window property cache
            cached_ratings = self.home_window.getProperty(
                f"nimbus.cachedRatings.{media_id}"
            )
            if cached_ratings:
                self._set_ratings_from_cache(media_id, cached_ratings)
                return

            # If no window cache, check database cache
            cached_data = self.database.get_cached_ratings(media_id)
            if cached_data:
                # For database cache hits, only update window properties
                # No need to update database since we just got valid data from it
                self.home_window.setProperty(
                    f"nimbus.cachedRatings.{media_id}", json.dumps(cached_data)
                )
                self._update_window_properties(cached_data)
                self.last_set_id = cached_data.get("imdbid") or media_id
                return

            # If no cache found anywhere or cached data is expired, fetch new data
            self._start_new_ratings_thread(media_id, meta)

    def _start_new_ratings_thread(self, media_id: str, meta: Dict[str, Any]) -> None:
        """Start a new thread to fetch ratings."""
        if self.current_ratings_thread and self.current_ratings_thread.is_alive():
            if self.pending_id != media_id:
                self.pending_id = None

        if self.pending_id != media_id:
            self.pending_id = media_id
            self.current_ratings_thread = Thread(
                target=self._fetch_ratings_thread, args=(media_id, meta)
            )
            self.current_ratings_thread.daemon = True
            self.current_ratings_thread.start()

    def _fetch_ratings_thread(self, media_id: str, meta: Dict[str, Any]) -> None:
        """Thread worker to fetch and process ratings with enhanced ID handling."""
        try:
            if media_id != self.pending_id:
                return

            api_key = self.get_infolabel("Skin.String(mdblist_api_key)")
            client = MDbListClient(api_key, self.database)

            imdb_id = meta.get("imdb_id")
            tmdb_id = meta.get("tmdb_id")

            # Always prefer using IMDb ID for fetching ratings if available
            lookup_id = imdb_id if imdb_id else tmdb_id
            if not lookup_id:
                lookup_id = media_id

            result = client.get_ratings_from_api(
                lookup_id, meta.get("media_type", "movie")
            )

            if media_id != self.pending_id:
                return

            if result:
                # Always preserve known IDs
                if imdb_id:
                    result["imdbid"] = imdb_id
                if tmdb_id:
                    result["tmdbid"] = tmdb_id

                self._cache_ratings(media_id, result)
                self._update_window_properties(result)
                self.last_set_id = result.get("imdbid") or media_id
        except Exception as e:
            xbmc.log(f"Error fetching ratings: {str(e)}", xbmc.LOGERROR)

    def _cache_ratings(self, primary_id: str, result: Dict[str, Any]) -> None:
        """Cache ratings in both database and window properties."""
        self.database.update_ratings(primary_id, result)

        imdb_id = result.get("imdbid")
        tmdb_id = result.get("tmdbid")

        if imdb_id:
            self.home_window.setProperty(
                f"nimbus.cachedRatings.{imdb_id}", json.dumps(result)
            )
        if tmdb_id:
            self.home_window.setProperty(
                f"nimbus.cachedRatings.{tmdb_id}", json.dumps(result)
            )

    def _update_window_properties(self, result: Dict[str, Any]) -> None:
        """Update window properties with new ratings data."""
        for key, value in result.items():
            if isinstance(value, (str, int, float)):
                self.home_window.setProperty(f"nimbus.{key}", str(value))

    def _clear_ratings_properties(self) -> None:
        """Clear all ratings properties."""
        for key, value in EMPTY_RATINGS.items():
            self.home_window.setProperty(f"nimbus.{key}", str(value))
        self.last_set_id = None
        self.pending_id = None

    def _get_current_item_meta(self) -> Optional[Dict[str, Any]]:
        """Get metadata for the current item."""
        dbtype = self.get_infolabel("ListItem.DBTYPE").lower()
        path = self.get_infolabel("ListItem.Path")
        if not (
            dbtype in ["movie", "tvshow", "episode", "season"]
            or path.startswith("plugin://plugin.video.mediafusion")
        ):
            return None

        # Try direct ID lookup first
        imdb_id = (
            self.get_infolabel("ListItem.IMDBNumber")
            or self.get_infolabel("ListItem.Property(imdb)")
            or self.get_infolabel("VideoPlayer.IMDBNumber")
        )
        tmdb_id = self.get_infolabel(
            "ListItem.Property(TMDb_ID)"
        ) or self.get_infolabel("ListItem.Property(tmdb)")

        if imdb_id and imdb_id.startswith("tt"):
            return {"id": imdb_id}
        elif tmdb_id:
            return {"id": tmdb_id, "media_type": self._get_media_type()}

        # Fallback to title lookup
        title = self.get_infolabel("ListItem.Label")
        if not title:
            return None

        meta = {
            "title": title,
            "premiered": self.get_infolabel("ListItem.Premiered"),
            "media_type": self._get_media_type(),
        }

        found_imdb_id, found_tmdb_id = self._lookup_imdb_id(meta)
        if not (found_imdb_id or found_tmdb_id):
            return None

        return {
            "id": found_imdb_id if found_imdb_id else found_tmdb_id,
            "media_type": meta["media_type"],
            "imdb_id": found_imdb_id,
            "tmdb_id": found_tmdb_id,
        }

    def _get_media_type(self) -> str:
        """Determine media type from current item."""
        dbtype = self.get_infolabel("ListItem.DBTYPE").lower()
        return "movie" if dbtype == "movie" else "tv"

    def _lookup_imdb_id(
        self, meta: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Lookup IMDb ID and TMDb ID for given metadata."""
        title = meta.get("title")
        if not title:
            return None, None

        premiered = meta.get("premiered")
        media_type = meta.get("media_type", "movie")

        if media_type == "tv":
            title = self._clean_tv_title(title)

        year = self._extract_year(premiered)

        # Check cache first
        cached_imdb_id, cached_tmdb_id = self.database.get_cached_ids(
            title, year, media_type
        )
        if cached_imdb_id:
            return cached_imdb_id, cached_tmdb_id

        # Try TMDb lookup
        found_imdb_id, found_tmdb_id = self.tmdb_client.search_by_info(
            title, premiered, media_type
        )

        if found_imdb_id or found_tmdb_id:
            self.database.cache_ids(
                title, year, media_type, found_imdb_id, found_tmdb_id
            )

        return found_imdb_id, found_tmdb_id

    def _clean_tv_title(self, title: str) -> str:
        """Clean TV show title by removing season information."""
        return re.sub(r"\s+season\s+\d+.*$", "", title, flags=re.IGNORECASE).strip()

    def _extract_year(self, premiered: Optional[str]) -> Optional[str]:
        """Extract year from premiered date."""
        if not premiered:
            return None

        if "/" in premiered:
            parts = premiered.split("/")
            return parts[2] if len(parts) == 3 and parts[2].isdigit() else None

        return premiered[:4] if premiered else None

    def _set_ratings_from_cache(self, media_id: str, cached_ratings: str) -> None:
        """Set ratings from cached data."""
        try:
            result = json.loads(cached_ratings)
            self._update_window_properties(result)
            self.last_set_id = media_id
        except json.JSONDecodeError:
            self._clear_ratings_properties()

    def _handle_trailer_update(self, media_id: str) -> None:
        """Handle trailer updates for the current item."""
        if media_id == self.last_set_id and media_id != self.last_trailer_id:
            self.current_trailer_ready_status = self.get_property(
                "nimbus.trailer_ready"
            )
            if self.current_trailer_ready_status != "true":
                self.set_property("nimbus.trailer_ready", "true")
                trailer_url = self.get_infolabel(
                    "Window(Home).Property(nimbus.trailer)"
                )
                if trailer_url:
                    match = re.search(VIDEO_ID_PATTERN, trailer_url)
                    if match:
                        video_id = match.group(1)
                        play_url = (
                            f"plugin://plugin.video.youtube/play/?video_id={video_id}"
                        )
                        xbmc.executebuiltin(
                            f"Skin.SetString(TrailerPlaybackURL,{play_url})"
                        )
                        self.last_trailer_id = media_id
        else:
            self.clear_property("nimbus.trailer_ready")
