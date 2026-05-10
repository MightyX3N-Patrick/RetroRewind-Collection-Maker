"""
SteamGridDB Plugin — game poster/cover art
API key: https://www.steamgriddb.com/profile/preferences/api
"""
import urllib.request, urllib.parse, json, os, time
from .base import BasePlugin

BASE = "https://www.steamgriddb.com/api/v2"

GENRES = ["Action","Adventure","RPG","Shooter","Platformer","Fighting",
          "Sports","Racing","Puzzle","Strategy","Simulation","Horror","Indie"]


class SteamGridDBPlugin(BasePlugin):
    name        = "SteamGridDB"
    description = "Game poster art from SteamGridDB"
    icon        = "🖼"
    media_type  = "game"

    def __init__(self):
        self.api_key = os.environ.get("STEAMGRIDDB_KEY", "")

    def configure(self, config: dict):
        if "api_key" in config and config["api_key"]:
            self.api_key = config["api_key"]

    def config_fields(self):
        return [{"key": "api_key", "label": "API Key", "type": "password",
                 "hint": "steamgriddb.com/profile/preferences/api"}]

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_genres(self) -> list:
        return GENRES

    def _get(self, path: str, params: dict = {}) -> dict:
        url = f"{BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "RetroRewindBuilder/1.0",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def _best_cover(self, game_id: int) -> str:
        """Get best portrait cover for a game. Returns URL or empty string."""
        # Try grids with portrait dimensions first
        for style in ["alternate", "blurred", ""]:
            try:
                params = {"dimensions": "600x900,342x482,660x930", "limit": 1}
                if style:
                    params["styles"] = style
                data = self._get(f"/grids/game/{game_id}", params)
                grids = data.get("data", [])
                if grids and isinstance(grids[0], dict):
                    return grids[0].get("url", "")
            except:
                pass
        # Fall back to any grid
        try:
            data = self._get(f"/grids/game/{game_id}", {"limit": 5})
            grids = data.get("data", [])
            # Filter to portrait ones
            for g in grids:
                if not isinstance(g, dict):
                    continue
                w = g.get("width", 0)
                h = g.get("height", 0)
                if h > w:  # portrait
                    return g.get("url", "")
            # Any will do
            for g in grids:
                if isinstance(g, dict) and g.get("url"):
                    return g["url"]
        except Exception as e:
            print(f"SteamGridDB cover error for {game_id}: {e}")
        return ""

    def search(self, query: str, year=None) -> list:
        if not self.is_configured():
            return self._demo(query)
        try:
            data = self._get("/search/autocomplete/" + urllib.parse.quote(query))
            games = data.get("data", [])[:10]
            results = []
            for game in games:
                if not isinstance(game, dict):
                    continue
                gid = game.get("id")
                cover = self._best_cover(gid) if gid else ""
                results.append(self._normalize(game, cover))
            return [r for r in results if r]
        except Exception as e:
            print(f"SteamGridDB search error: {e}")
            return self._demo(query)

    def bulk_fetch(self, year_from: int, year_to: int, genre: str = '',
                   limit: int = 50, min_rating: float = 0, **kwargs) -> list:
        if not self.is_configured():
            return self._demo_bulk(year_from, year_to, limit)

        from plugins.screenscraper_plugin import GAME_CATALOG
        import random

        candidates = []
        for plat, games in GAME_CATALOG.items():
            for title, year in games:
                if year_from <= year <= year_to:
                    candidates.append((title, year))
        random.shuffle(candidates)

        results = []
        for title, year in candidates:
            if len(results) >= limit:
                break
            try:
                data = self._get("/search/autocomplete/" + urllib.parse.quote(title))
                games = data.get("data", [])
                if not games or not isinstance(games[0], dict):
                    continue
                game = games[0]
                gid = game.get("id")
                cover = self._best_cover(gid) if gid else ""
                item = self._normalize(game, cover)
                if item:
                    item["year"] = str(year)
                    results.append(item)
                time.sleep(0.25)
            except Exception as e:
                print(f"SteamGridDB bulk error: {e}")
        return results

    def _normalize(self, game: dict, cover_url: str) -> dict:
        if not isinstance(game, dict):
            return None
        gid = game.get("id", "")
        return {
            "id":        f"sgdb_{gid}",
            "title":     game.get("name", "Unknown"),
            "year":      str(game.get("release_date", "") or "")[:4],
            "genre":     "Action",
            "genres":    ["Action"],
            "cover_url": cover_url,
            "rating":    7.0,
            "type":      "game",
            "plugin":    "steamgriddb",
        }

    def _demo(self, q):
        return [{"id":"sgdb_demo","title":f"{q} — add SteamGridDB API key",
                 "year":"1993","genre":"Action","genres":["Action"],
                 "cover_url":"https://placehold.co/256x512/0a0a1a/60a5fa?text=NO+KEY",
                 "rating":7.0,"type":"game","plugin":"steamgriddb"}]

    def _demo_bulk(self, yf, yt, limit):
        from plugins.screenscraper_plugin import GAME_CATALOG
        import random, urllib.parse
        results = []
        for plat, games in GAME_CATALOG.items():
            for title, year in games:
                if yf <= year <= yt:
                    results.append({
                        "id": f"sgdb_demo_{len(results)}",
                        "title": f"{title} (Demo — add API key)",
                        "year": str(year), "genre": "Action", "genres": ["Action"],
                        "cover_url": f"https://placehold.co/256x512/0a0a1a/60a5fa?text={urllib.parse.quote(title[:10])}",
                        "rating": 7.5, "type": "game", "plugin": "steamgriddb",
                    })
                    if len(results) >= limit:
                        return results
        return results
