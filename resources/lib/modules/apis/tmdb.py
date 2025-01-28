import xbmc
import requests
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
from .base import BaseAPIClient
from ..config import API_URLS


class TMDbClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(API_URLS["tmdb"])
        self.api_key = api_key

    def search_by_info(self, title: str, year_or_premiered: Optional[str] = None, 
                      media_type: str = "movie") -> Tuple[Optional[str], Optional[str]]:
        """Search TMDb by title and year."""
        clean_title = title.lower().strip()
        year = self._extract_year(year_or_premiered)

        if year:
            exact_matches = self._search_tmdb(clean_title, media_type, year)
            if exact_matches:
                return self._get_best_match(exact_matches, clean_title, year)

        fuzzy_matches = self._search_tmdb(clean_title, media_type)
        if fuzzy_matches:
            return self._get_best_match(fuzzy_matches, clean_title, year)
        return None, None

    def _extract_year(self, year_or_premiered: Optional[str]) -> Optional[int]:
        """Extract year from various date formats."""
        if not year_or_premiered:
            return None
            
        if str(year_or_premiered).isdigit():
            return int(year_or_premiered)
            
        try:
            return datetime.strptime(year_or_premiered, "%Y-%m-%d").year
        except (ValueError, TypeError):
            return None

    def _search_tmdb(self, title: str, media_type: str, year: Optional[int] = None) -> List[Dict]:
        """Search TMDb API."""
        params = {
            "api_key": self.api_key,
            "query": title,
            "language": "en-US",
            "page": 1
        }
        if year:
            params["year"] = year
            
        try:
            response = self.session.get(f"{self.base_url}/search/{media_type}", params=params)
            if response.status_code == 200:
                return response.json().get("results", [])
        except requests.RequestException as e:
            xbmc.log(f"TMDb Request Error: {str(e)}", xbmc.LOGERROR)
        return []
    
    def _get_best_match(self, results: List[Dict], title: str, year: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
        """Find best match from results using SequenceMatcher."""
        best_score = 0
        best_match = None
        for result in results:
            tmdb_id = str(result.get("id"))
            if not tmdb_id:
                continue
            result_title = result.get("name" if "name" in result else "title", "").lower().strip()
            score = SequenceMatcher(None, title, result_title).ratio()
            if year:
                try:
                    result_date = result.get("first_air_date" if "first_air_date" in result else "release_date", "")
                    result_year = int(result_date[:4]) if result_date else None
                    if result_year and result_year == year:
                        score += 0.3
                except (ValueError, TypeError):
                    pass
            if score > best_score:
                best_score = score
                best_match = result
        if best_match and best_score > 0.6:
            tmdb_id = str(best_match.get("id"))
            media_type = "tv" if "first_air_date" in best_match else "movie"
            imdb_id = self._get_external_ids(tmdb_id, media_type)
            return imdb_id, tmdb_id
        return None, None
    
    def _get_external_ids(self, tmdb_id: str, media_type: str) -> Optional[str]:
        """Get external IDs (including IMDb ID) for a TMDb item."""
        params = {"api_key": self.api_key}
        try:
            response = self.session.get(
                f"{self.base_url}/{media_type}/{tmdb_id}/external_ids", 
                params=params
            )
            if response.status_code == 200:
                return response.json().get("imdb_id")
        except requests.RequestException as e:
            xbmc.log(f"TMDb Request Error: {str(e)}", xbmc.LOGERROR)
        return None