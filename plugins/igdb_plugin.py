"""
Retro Games Plugin — IGDB (Internet Game Database by Twitch)
Free API for game metadata and cover art.
Requires Twitch Developer credentials: https://dev.twitch.tv/console

IGDB is a great fallback / alternative to Screenscraper with
a larger database and faster API.
"""

import urllib.request, urllib.parse, json, os, time
from .base import BasePlugin

IGDB_BASE = "https://api.igdb.com/v4"
IGDB_COVERS = "https://images.igdb.com/igdb/image/upload/t_cover_big"

GENRES = {
    2: "Shooter", 4: "Fighting", 5: "Beat 'em up", 7: "Music",
    8: "Platformer", 9: "Puzzle", 10: "Racing", 11: "RPG",
    12: "Simulator", 13: "Sport", 14: "Strategy", 15: "Action-Adventure",
    16: "Action", 24: "Adventure", 25: "Indie", 26: "Arcade",
    31: "Shooter", 32: "Shooter"
}

PLATFORMS = {
    "NES": 18, "SNES": 19, "Nintendo 64": 4,
    "Game Boy": 33, "Game Boy Advance": 24,
    "Mega Drive / Genesis": 29, "Master System": 35,
    "PlayStation": 7, "PlayStation 2": 8,
    "Arcade": 52, "Atari 2600": 59,
    "DOS": 13, "Amiga": 16,
    "PC Engine / TurboGrafx-16": 86,
}


class IGDBPlugin(BasePlugin):
    name = "Retro Games (IGDB)"
    description = "Game database by Twitch — free API"
    icon = "🎮"
    media_type = "game"

    def __init__(self):
        self.client_id = os.environ.get("IGDB_CLIENT_ID", "")
        self.client_secret = os.environ.get("IGDB_CLIENT_SECRET", "")
        self._token = None
        self._token_expiry = 0

    def configure(self, config: dict):
        if "client_id" in config:
            self.client_id = config["client_id"]
        if "client_secret" in config:
            self.client_secret = config["client_secret"]
        self._token = None

    def config_fields(self):
        return [
            {"key": "client_id",     "label": "Client ID",     "type": "text",     "hint": "Free at dev.twitch.tv"},
            {"key": "client_secret", "label": "Client Secret", "type": "password", "hint": ""},
        ]

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_genres(self) -> list:
        return list(GENRES.values())

    def get_platforms(self) -> list:
        return list(PLATFORMS.keys())

    def _get_token(self) -> str:
        """Get OAuth2 token from Twitch."""
        if self._token and time.time() < self._token_expiry:
            return self._token
        url = "https://id.twitch.tv/oauth2/token"
        params = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }).encode()
        req = urllib.request.Request(url, data=params, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            self._token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
            return self._token

    def _post(self, endpoint: str, body: str) -> list:
        """POST to IGDB API."""
        token = self._get_token()
        url = f"{IGDB_BASE}/{endpoint}"
        req = urllib.request.Request(
            url,
            data=body.encode(),
            method="POST",
            headers={
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain",
                "User-Agent": "RetroRewindBuilder/1.0",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f"IGDB request failed: {e}")
            return []

    def search(self, query: str, year=None) -> list:
        if not self.is_configured():
            return self._demo_results(query)
        year_filter = f" & first_release_date >= {self._year_ts(year)} & first_release_date <= {self._year_end_ts(year)}" if year else ""
        body = f'search "{query}"; fields name,first_release_date,genres,cover.image_id,summary,rating,platforms.name; where cover != null{year_filter}; limit 10;'
        results = self._post("games", body)
        return [self.normalize(r) for r in results if r.get("cover")]

    def bulk_fetch(self, year_from: int, year_to: int, genre: str = '',
                   limit: int = 50, min_rating: float = 0,
                   platform: str = '', **kwargs) -> list:
        if not self.is_configured():
            return self._demo_bulk(year_from, year_to, limit, platform)

        ts_from = self._year_ts(str(year_from))
        ts_to = self._year_end_ts(str(year_to))

        genre_filter = ""
        if genre:
            for gid, gname in GENRES.items():
                if gname.lower() == genre.lower():
                    genre_filter = f" & genres = ({gid})"
                    break

        platform_filter = ""
        if platform and platform in PLATFORMS:
            platform_filter = f" & platforms = ({PLATFORMS[platform]})"

        rating_filter = f" & rating >= {min_rating * 10}" if min_rating > 0 else ""

        results = []
        offset = 0
        batch = 50

        while len(results) < limit:
            fetch = min(batch, limit - len(results))
            body = (
                f"fields name,first_release_date,genres,cover.image_id,summary,rating,platforms.name;"
                f" where first_release_date >= {ts_from}"
                f" & first_release_date <= {ts_to}"
                f" & cover != null"
                f"{genre_filter}{platform_filter}{rating_filter};"
                f" sort rating desc; limit {fetch}; offset {offset};"
            )
            items = self._post("games", body)
            if not items:
                break
            for item in items:
                if item.get("cover"):
                    results.append(self.normalize(item))
            offset += fetch
            time.sleep(0.2)

        return results

    def normalize(self, raw: dict) -> dict:
        cover = raw.get("cover", {})
        image_id = cover.get("image_id", "") if isinstance(cover, dict) else ""
        cover_url = f"{IGDB_COVERS}/{image_id}.jpg" if image_id else ""

        genre_ids = raw.get("genres", [])
        genres = []
        for g in genre_ids:
            gid = g if isinstance(g, int) else g.get("id")
            if gid in GENRES:
                genres.append(GENRES[gid])

        ts = raw.get("first_release_date", 0)
        year = str(1970 + ts // (365 * 24 * 3600)) if ts else ""

        platforms = raw.get("platforms", [])
        platform_names = []
        for p in platforms:
            if isinstance(p, dict):
                platform_names.append(p.get("name", ""))
            elif isinstance(p, int):
                for pname, pid in PLATFORMS.items():
                    if pid == p:
                        platform_names.append(pname)

        rating = raw.get("rating", 50)
        if rating:
            rating = round(rating / 10, 1)

        return {
            "id": f"igdb_{raw.get('id', '')}",
            "source_id": raw.get("id"),
            "title": raw.get("name", "Unknown"),
            "year": year,
            "genre": genres[0] if genres else "Action",
            "genres": genres,
            "cover_url": cover_url,
            "rating": rating or 5.0,
            "description": raw.get("summary", ""),
            "type": "game",
            "platform": platform_names[0] if platform_names else "",
            "plugin": "igdb",
        }

    def _year_ts(self, year: str) -> int:
        import datetime
        try:
            return int(datetime.datetime(int(year), 1, 1).timestamp())
        except:
            return 0

    def _year_end_ts(self, year: str) -> int:
        import datetime
        try:
            return int(datetime.datetime(int(year), 12, 31).timestamp())
        except:
            return 0

    def _demo_results(self, query: str) -> list:
        return [{
            "id": "igdb_demo_1",
            "title": f"{query} (Demo - Add IGDB credentials)",
            "year": "1993",
            "genre": "Action",
            "genres": ["Action"],
            "cover_url": "https://placehold.co/256x512/16213e/0f3460?text=DEMO",
            "rating": 8.0,
            "description": "Add your IGDB client ID and secret in Settings.",
            "type": "game",
            "platform": "SNES",
            "plugin": "igdb",
        }]

    def _demo_bulk(self, year_from, year_to, limit, platform='') -> list:
        import random
        games = [
            "Aero the Acrobat", "Alien 3", "Batman Returns", "Battletoads",
            "Bomberman", "Bubsy", "Chester Cheetah", "Cool Spot",
            "Ecco the Dolphin", "Flashback", "Golden Axe", "Herzog Zwei",
            "Hook", "James Pond", "Joe & Mac", "Kid Chameleon",
            "Landstalker", "Lemmings", "Lions King", "Mickey Mania",
        ]
        results = []
        for i, title in enumerate(games[:limit]):
            year = str(random.randint(year_from, min(year_to, year_from + 5)))
            results.append({
                "id": f"igdb_demo_{i}",
                "title": f"{title} (Demo)",
                "year": year,
                "genre": random.choice(list(GENRES.values())),
                "genres": [random.choice(list(GENRES.values()))],
                "cover_url": f"https://placehold.co/256x512/16213e/53d8fb?text={urllib.parse.quote(title[:8])}",
                "rating": round(random.uniform(5.5, 9.0), 1),
                "description": "Add IGDB credentials for real results.",
                "type": "game",
                "platform": platform or "SNES",
                "plugin": "igdb",
            })
        return results
