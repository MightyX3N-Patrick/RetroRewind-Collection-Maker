"""
Retro Movies Plugin — TMDB
Supports movies and TV series, country/language filter.
"""
import urllib.request, urllib.parse, json, os, time
from .base import BasePlugin

TMDB_BASE  = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p/w500"

MOVIE_GENRES = {
    28:"Action",12:"Adventure",16:"Animation",35:"Comedy",80:"Crime",
    99:"Documentary",18:"Drama",10751:"Family",14:"Fantasy",36:"History",
    27:"Horror",10402:"Music",9648:"Mystery",10749:"Romance",878:"Sci-Fi",
    10770:"TV Movie",53:"Thriller",10752:"War",37:"Western"
}
TV_GENRES = {
    10759:"Action & Adventure",16:"Animation",35:"Comedy",80:"Crime",
    99:"Documentary",18:"Drama",10751:"Family",10762:"Kids",9648:"Mystery",
    10765:"Sci-Fi & Fantasy",37:"Western"
}

# (value, label, ui_language, original_language)
COUNTRIES = [
    ("",   "Any",          "en-US", ""),
    ("US", "USA",          "en-US", "en"),
    ("GB", "UK",           "en-GB", "en"),
    ("FR", "France",       "fr-FR", "fr"),
    ("DE", "Germany",      "de-DE", "de"),
    ("IT", "Italy",        "it-IT", "it"),
    ("ES", "Spain",        "es-ES", "es"),
    ("JP", "Japan",        "ja-JP", "ja"),
    ("KR", "South Korea",  "ko-KR", "ko"),
    ("IN", "India",        "hi-IN", "hi"),
    ("AU", "Australia",    "en-AU", "en"),
    ("CA", "Canada",       "en-CA", "en"),
    ("MX", "Mexico",       "es-MX", "es"),
    ("BR", "Brazil",       "pt-BR", "pt"),
    ("SE", "Sweden",       "sv-SE", "sv"),
    ("DK", "Denmark",      "da-DK", "da"),
    ("NO", "Norway",       "nb-NO", "no"),
    ("FI", "Finland",      "fi-FI", "fi"),
    ("NL", "Netherlands",  "nl-NL", "nl"),
    ("RU", "Russia",       "ru-RU", "ru"),
    ("HK", "Hong Kong",    "zh-HK", "zh"),
    ("CN", "China",        "zh-CN", "zh"),
    ("TW", "Taiwan",       "zh-TW", "zh"),
    ("AR", "Argentina",    "es-AR", "es"),
    ("PL", "Poland",       "pl-PL", "pl"),
    ("PT", "Portugal",     "pt-PT", "pt"),
]

def _lang_for(country_code):
    for row in COUNTRIES:
        if row[0] == country_code:
            return row[2], row[3]  # ui_language, original_language
    return "en-US", ""


class TMDBPlugin(BasePlugin):
    name        = "Retro Movies"
    description = "Movies & TV from The Movie Database"
    icon        = "🎬"
    media_type  = "movie"

    def __init__(self):
        self.api_key = os.environ.get("TMDB_API_KEY", "")
        self.media   = "movie"
        self.country = ""

    def configure(self, config: dict):
        if "api_key" in config: self.api_key = config["api_key"]
        if "media"   in config: self.media   = config.get("media", "movie")
        if "country" in config: self.country = config.get("country", "")

    def config_fields(self):
        return [
            {"key": "api_key", "label": "API Key", "type": "password",
             "hint": "themoviedb.org"},
            {"key": "media",   "label": "Type",    "type": "select",
             "options": [{"value":"movie","label":"Movies"},
                         {"value":"tv",   "label":"TV Series"}]},
            {"key": "country", "label": "Country", "type": "select",
             "options": [{"value": r[0], "label": r[1]} for r in COUNTRIES]},
        ]

    def is_configured(self): return bool(self.api_key)

    def get_genres(self):
        return list((TV_GENRES if self.media == "tv" else MOVIE_GENRES).values())

    def _get(self, endpoint, params):
        params["api_key"] = self.api_key
        url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "RetroRewindBuilder/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"TMDB error: {e}")
            return {}

    def search(self, query: str, year=None) -> list:
        if not self.is_configured():
            return self._demo(query)
        lang, _ = _lang_for(self.country)
        endpoint = "/search/tv" if self.media == "tv" else "/search/movie"
        params = {"query": query, "include_adult": "false", "language": lang}
        if year:
            params["year" if self.media == "movie" else "first_air_date_year"] = year
        data = self._get(endpoint, params)
        return [self.normalize(r) for r in data.get("results", [])[:10]
                if r.get("poster_path")]

    def bulk_fetch(self, year_from: int, year_to: int, genre: str = '',
                   limit: int = 50, min_rating: float = 0, **kwargs) -> list:
        if not self.is_configured():
            return self._demo_bulk(year_from, year_to, limit)

        lang, orig_lang = _lang_for(self.country)
        gmap = TV_GENRES if self.media == "tv" else MOVIE_GENRES
        genre_id = next((gid for gid, gn in gmap.items() if gn.lower()==genre.lower()), None)

        is_tv = self.media == "tv"
        endpoint = "/discover/tv" if is_tv else "/discover/movie"
        date_gte = "first_air_date.gte" if is_tv else "primary_release_date.gte"
        date_lte = "first_air_date.lte" if is_tv else "primary_release_date.lte"

        results, page = [], 1
        while len(results) < limit:
            params = {
                "sort_by": "vote_count.desc",
                date_gte: f"{year_from}-01-01",
                date_lte: f"{year_to}-12-31",
                "vote_average.gte": min_rating,
                "vote_count.gte": 20,
                "include_adult": "false",
                "language": lang,
                "include_image_language": f"{lang.split('-')[0]},en,null",
                "page": page,
            }
            if genre_id: params["with_genres"] = genre_id
            if orig_lang: params["with_original_language"] = orig_lang

            data = self._get(endpoint, params)
            items = data.get("results", [])
            total_pages = data.get("total_pages", 1)
            if not items or page > total_pages:
                break
            for item in items:
                if item.get("poster_path"):
                    results.append(self.normalize(item))
                if len(results) >= limit:
                    break
            page += 1
            time.sleep(0.1)

        return results

    def normalize(self, raw: dict) -> dict:
        is_tv  = self.media == "tv"
        gmap   = TV_GENRES if is_tv else MOVIE_GENRES
        genres = [gmap[g] for g in raw.get("genre_ids", []) if g in gmap]
        date   = raw.get("first_air_date" if is_tv else "release_date", "") or ""
        # Use localised title if available, fall back to original
        title  = (raw.get("name" if is_tv else "title")
                  or raw.get("original_name" if is_tv else "original_title", "Unknown"))
        poster = raw.get("poster_path", "")
        return {
            "id":        f"tmdb_{raw.get('id','')}",
            "title":     title,
            "year":      date[:4],
            "genre":     genres[0] if genres else "Drama",
            "genres":    genres,
            "cover_url": f"{TMDB_IMAGE}{poster}" if poster else "",
            "rating":    round(raw.get("vote_average", 5.0), 1),
            "type":      "tv" if is_tv else "movie",
            "plugin":    "tmdb",
        }

    def _demo(self, q):
        return [{"id":"tmdb_demo","title":f"{q} — add TMDB API key","year":"1990",
                 "genre":"Action","genres":["Action"],
                 "cover_url":"https://placehold.co/256x512/1a1a2e/e94560?text=DEMO",
                 "rating":7.5,"type":"movie","plugin":"tmdb"}]

    def _demo_bulk(self, yf, yt, limit):
        import random
        titles = ["Terminator 2","Jurassic Park","Silence of the Lambs","Home Alone",
                  "Goodfellas","Die Hard","Total Recall","Forrest Gump","Pulp Fiction"]
        return [{"id":f"tmdb_demo_{i}","title":f"{t} (Demo)","year":str(random.randint(yf,yt)),
                 "genre":random.choice(["Action","Drama","Comedy"]),"genres":["Action"],
                 "cover_url":f"https://placehold.co/256x512/1a1a2e/e94560?text={urllib.parse.quote(t[:10])}",
                 "rating":round(random.uniform(5,9),1),"type":"movie","plugin":"tmdb"}
                for i,t in enumerate(titles[:limit])]
