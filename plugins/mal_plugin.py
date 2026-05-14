"""
AniDB Plugin — powered by Jikan (MyAnimeList public API)
No API key required. https://jikan.moe / https://docs.api.jikan.moe

Jikan mirrors MyAnimeList data and returns everything (cover, genres,
rating, year) in a single call — no sequential enrichment needed.
"""
import urllib.request, urllib.parse, json, time, random
from typing import Optional
from .base import BasePlugin

JIKAN_BASE = "https://api.jikan.moe/v4"

# MAL genre id → RetroRewind genre name
MAL_GENRE_MAP = {
    1:  "Action",
    2:  "Adventure",
    4:  "Comedy",
    8:  "Drama",
    10: "Fantasy",
    14: "Horror",
    7:  "Mystery",
    22: "Romance",
    24: "Science Fiction",
    30: "Sports",
    36: "Thriller",
    38: "Music",
    23: "Animation",
    40: "Drama",
}

GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Drama",
    "Fantasy", "Horror", "Music", "Mystery", "Romance",
    "Science Fiction", "Sports", "Thriller",
]

RATE_SLEEP = 0.4


class MALPlugin(BasePlugin):
    name        = "MyAnimeList"
    description = "Anime series & films from MyAnimeList (no API key needed)"
    icon        = "🍥"
    media_type  = "movie"

    def __init__(self):
        pass

    def configure(self, config: dict):
        pass

    def is_configured(self) -> bool:
        return True

    def config_fields(self) -> list:
        return []

    def get_genres(self) -> list:
        return GENRES

    def _get(self, path: str, params: dict = {}) -> dict:
        url = f"{JIKAN_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "User-Agent": "RetroRewindBuilder/1.0",
            "Accept":     "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def search(self, query: str, year: Optional[str] = None) -> list:
        try:
            params = {"q": query, "limit": 10, "sfw": "false"}
            if year:
                params["start_date"] = f"{year}-01-01"
                params["end_date"]   = f"{year}-12-31"
            data = self._get("/anime", params)
            return [self.normalize(r) for r in data.get("data", [])
                    if r.get("images")]
        except Exception as e:
            print(f"AniDB/Jikan search error: {e}")
            return []

    def bulk_fetch(self, year_from: int, year_to: int, genre: str = "",
                   limit: int = 50, min_rating: float = 0, **kwargs) -> list:
        genre_id = None
        if genre:
            genre_id = next(
                (gid for gid, gname in MAL_GENRE_MAP.items()
                 if gname.lower() == genre.lower()), None
            )

        results, page = [], 1
        while len(results) < limit:
            try:
                params = {
                    "start_date": f"{year_from}-01-01",
                    "end_date":   f"{year_to}-12-31",
                    "order_by":   "score",
                    "sort":       "desc",
                    "limit":      25,
                    "page":       page,
                    "sfw":        "false",
                }
                if genre_id:
                    params["genres"] = genre_id
                if min_rating > 0:
                    params["min_score"] = min_rating

                data = self._get("/anime", params)
                items = data.get("data", [])
                pagination = data.get("pagination", {})

                if not items:
                    break

                for item in items:
                    if item.get("images"):
                        norm = self.normalize(item)
                        if norm["rating"] >= min_rating:
                            results.append(norm)
                    if len(results) >= limit:
                        break

                if not pagination.get("has_next_page", False):
                    break

                page += 1
                time.sleep(RATE_SLEEP)

            except Exception as e:
                print(f"AniDB/Jikan bulk error: {e}")
                break

        return results

    def normalize(self, raw: dict) -> dict:
        genres = []
        for g in raw.get("genres", []) + raw.get("themes", []):
            mapped = MAL_GENRE_MAP.get(g.get("mal_id"))
            if mapped and mapped not in genres:
                genres.append(mapped)
        if not genres:
            genres = ["Animation"]
        primary = genres[0]

        images = raw.get("images", {})
        cover_url = (
            images.get("jpg", {}).get("large_image_url") or
            images.get("jpg", {}).get("image_url") or
            images.get("webp", {}).get("large_image_url") or
            ""
        )

        year = ""
        aired = raw.get("aired", {})
        if aired.get("from"):
            year = str(aired["from"])[:4]
        elif raw.get("year"):
            year = str(raw["year"])

        try:
            rating = round(float(raw.get("score") or 0), 1)
        except (ValueError, TypeError):
            rating = 0.0

        mal_type = (raw.get("type") or "").lower()
        media_type = "movie" if mal_type == "movie" else "tv"

        return {
            "id":        f"mal_{raw.get('mal_id', '')}",
            "title":     raw.get("title_english") or raw.get("title") or "Unknown",
            "year":      year,
            "genre":     primary,
            "genres":    genres,
            "cover_url": cover_url,
            "rating":    rating,
            "type":      media_type,
            "plugin":    "mal",
        }
