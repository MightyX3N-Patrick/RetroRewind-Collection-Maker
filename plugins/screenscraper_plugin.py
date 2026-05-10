"""
Retro Games Plugin — Screenscraper.fr

Screenscraper is ROM-hash based — it identifies games by CRC/MD5/SHA1.
It does NOT have a "list all games by year" endpoint.

What actually works:
  - jeuInfos.php   → single game lookup by name or hash
  - jeuRecherche.php → search by name, returns candidates

For bulk year-range fetching, we search a curated list of known titles
per platform and year, then enrich each with Screenscraper data.
If no credentials, demo data is shown.
"""

import urllib.request, urllib.parse, json, os, time, uuid
from .base import BasePlugin

SCREENSCRAPER_BASE = "https://www.screenscraper.fr/api2"

PLATFORMS = {
    "NES": 3,
    "SNES": 4,
    "Mega Drive / Genesis": 1,
    "Game Boy": 9,
    "Game Boy Color": 10,
    "Game Boy Advance": 12,
    "Nintendo 64": 14,
    "PlayStation": 57,
    "PlayStation 2": 58,
    "Arcade": 75,
    "Atari 2600": 26,
    "Master System": 2,
    "Game Gear": 21,
    "TurboGrafx-16": 31,
    "Neo Geo": 142,
    "Amiga": 64,
    "DOS": 135,
    "Commodore 64": 66,
    "Dreamcast": 23,
    "Saturn": 22,
}

GENRES = [
    "Action", "Adventure", "RPG", "Shooter", "Platformer",
    "Fighting", "Sports", "Racing", "Puzzle", "Strategy",
    "Simulation", "Beat 'em up", "Horror"
]

# Curated game list used for bulk fetching (platform → list of (title, year))
GAME_CATALOG = {
    "NES": [
        ("Super Mario Bros.", 1985), ("Super Mario Bros. 2", 1988), ("Super Mario Bros. 3", 1988),
        ("Contra", 1988), ("Castlevania", 1986), ("Castlevania II", 1987), ("Mega Man 2", 1988),
        ("Mega Man 3", 1990), ("Metal Gear", 1987), ("Teenage Mutant Ninja Turtles", 1989),
        ("Duck Tales", 1989), ("Kirby's Adventure", 1993), ("Battletoads", 1991),
        ("Ninja Gaiden", 1988), ("Punch-Out!!", 1987), ("Bionic Commando", 1988),
        ("Chip 'n Dale Rescue Rangers", 1990), ("Darkwing Duck", 1992),
        ("Final Fantasy", 1987), ("Zelda II", 1987), ("Metroid", 1986),
    ],
    "SNES": [
        ("Super Mario World", 1990), ("Super Mario Kart", 1992), ("Super Mario RPG", 1996),
        ("Super Metroid", 1994), ("A Link to the Past", 1991), ("Donkey Kong Country", 1994),
        ("Donkey Kong Country 2", 1995), ("Chrono Trigger", 1995), ("Final Fantasy VI", 1994),
        ("Earthbound", 1994), ("Mega Man X", 1993), ("Mega Man X2", 1994),
        ("Street Fighter II Turbo", 1992), ("Mortal Kombat", 1993), ("Super Castlevania IV", 1991),
        ("Contra III", 1992), ("Kirby Super Star", 1996), ("Yoshi's Island", 1995),
        ("F-Zero", 1990), ("Star Fox", 1993), ("Secret of Mana", 1993), ("ActRaiser", 1990),
        ("Gunstar Heroes", 1993), ("Aladdin", 1993), ("The Lion King", 1994),
    ],
    "Mega Drive / Genesis": [
        ("Sonic the Hedgehog", 1991), ("Sonic the Hedgehog 2", 1992), ("Sonic the Hedgehog 3", 1994),
        ("Sonic & Knuckles", 1994), ("Streets of Rage", 1991), ("Streets of Rage 2", 1992),
        ("Golden Axe", 1989), ("Gunstar Heroes", 1993), ("Comix Zone", 1995),
        ("Earthworm Jim", 1994), ("Earthworm Jim 2", 1995), ("Aladdin", 1993),
        ("The Lion King", 1994), ("Ecco the Dolphin", 1992), ("Phantasy Star IV", 1993),
        ("Shining Force", 1992), ("Mortal Kombat", 1993), ("Vectorman", 1995),
        ("Rocket Knight Adventures", 1993), ("ToeJam & Earl", 1991),
    ],
    "PlayStation": [
        ("Crash Bandicoot", 1996), ("Crash Bandicoot 2", 1997), ("Spyro the Dragon", 1998),
        ("Final Fantasy VII", 1997), ("Final Fantasy VIII", 1999), ("Final Fantasy IX", 2000),
        ("Metal Gear Solid", 1998), ("Resident Evil", 1996), ("Resident Evil 2", 1998),
        ("Castlevania: Symphony of the Night", 1997), ("Tekken 3", 1997), ("Street Fighter Alpha 3", 1998),
        ("Tony Hawk's Pro Skater", 1999), ("Tomb Raider", 1996), ("Gran Turismo", 1997),
        ("Medievil", 1998), ("Ape Escape", 1999), ("Wipeout", 1995),
    ],
    "Nintendo 64": [
        ("Super Mario 64", 1996), ("The Legend of Zelda: Ocarina of Time", 1998),
        ("The Legend of Zelda: Majora's Mask", 2000), ("GoldenEye 007", 1997),
        ("Mario Kart 64", 1996), ("Banjo-Kazooie", 1998), ("Donkey Kong 64", 1999),
        ("Star Fox 64", 1997), ("Conker's Bad Fur Day", 2001), ("Perfect Dark", 2000),
        ("Turok: Dinosaur Hunter", 1997), ("Wave Race 64", 1996),
    ],
    "Game Boy": [
        ("Tetris", 1989), ("Super Mario Land", 1989), ("Kirby's Dream Land", 1992),
        ("Metroid II", 1991), ("Pokemon Red/Blue", 1996), ("Pokemon Gold/Silver", 1999),
        ("Donkey Kong", 1994), ("Zelda: Link's Awakening", 1993),
    ],
    "Arcade": [
        ("Street Fighter II", 1991), ("Mortal Kombat", 1992), ("Metal Slug", 1996),
        ("King of Fighters '94", 1994), ("Samurai Shodown", 1993), ("Pac-Man", 1980),
        ("Galaga", 1981), ("Contra", 1987), ("Double Dragon", 1987), ("Final Fight", 1989),
        ("NBA Jam", 1993), ("Primal Rage", 1994), ("Killer Instinct", 1994),
    ],
    "DOS": [
        ("Doom", 1993), ("Doom II", 1994), ("Quake", 1996), ("Duke Nukem 3D", 1996),
        ("Wolfenstein 3D", 1992), ("Commander Keen", 1990), ("Prince of Persia", 1989),
        ("Lemmings", 1991), ("Worms", 1995), ("Warcraft II", 1995), ("StarCraft", 1998),
        ("Diablo", 1996), ("Baldur's Gate", 1998), ("Full Throttle", 1995),
    ],
}


class ScrapperPlugin(BasePlugin):
    name = "Retro Games"
    description = "Retro game box art from Screenscraper"
    icon = "🕹️"
    media_type = "game"

    def __init__(self):
        self.username = os.environ.get("SCREENSCRAPER_USER", "")
        self.password = os.environ.get("SCREENSCRAPER_PASS", "")


    def configure(self, config: dict):
        for key in ("username", "password"):
            if key in config and config[key]:
                setattr(self, key, config[key])

    def config_fields(self):
        return [
            {"key": "username", "label": "Username", "type": "text",     "hint": "screenscraper.fr"},
            {"key": "password", "label": "Password", "type": "password", "hint": ""},
        ]

    def is_configured(self) -> bool:
        return bool(self.username and self.password)

    def get_genres(self) -> list:
        return GENRES

    def get_platforms(self) -> list:
        return list(PLATFORMS.keys())

    def _build_params(self, extra: dict) -> dict:
        params = {
            "ssid": self.username,
            "sspassword": self.password,
            "softname": "RetroRewindBuilder",
            "output": "json",
        }

        params.update(extra)
        return params

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{SCREENSCRAPER_BASE}/{endpoint}.php?{urllib.parse.urlencode(self._build_params(params))}"
        req = urllib.request.Request(url, headers={"User-Agent": "RetroRewindBuilder/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                if not raw.strip():
                    print(f"Screenscraper empty response on {endpoint} (status {resp.status})")
                    return {"_error": "empty_response"}
                # Log first 300 chars so we can see what's coming back
                preview = raw[:300].decode(errors='replace')
                if not preview.lstrip().startswith('{'):
                    print(f"Screenscraper non-JSON on {endpoint}: {preview}")
                    return {"_error": "non_json", "_body": preview}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')
            print(f"Screenscraper HTTP {e.code} on {endpoint}: {body[:500]}")
            return {"_error": f"HTTP {e.code}"}
        except Exception as e:
            print(f"Screenscraper error on {endpoint}: {e}")
            return {"_error": str(e)}

    def search(self, query: str, year=None) -> list:
        if not self.is_configured():
            return self._demo_results(query)

        data = self._get("jeuRecherche", {"recherche": query})
        if "_error" in data:
            return self._demo_results(query)

        jeux = data.get("response", {}).get("jeux", [])
        if not jeux:
            return []

        results = []
        for j in jeux[:10]:
            n = self.normalize(j)
            if n["title"] != "Unknown":
                results.append(n)
        return results

    def bulk_fetch(self, year_from: int, year_to: int, genre: str = '',
                   limit: int = 50, min_rating: float = 0,
                   platform: str = '', **kwargs) -> list:
        if not self.is_configured():
            return self._demo_bulk(year_from, year_to, limit, platform)

        # Build list of titles to look up from our catalog
        candidates = []
        platforms_to_search = [platform] if platform and platform in GAME_CATALOG else list(GAME_CATALOG.keys())

        for plat in platforms_to_search:
            for title, year in GAME_CATALOG.get(plat, []):
                if year_from <= year <= year_to:
                    candidates.append((title, year, plat))

        if not candidates:
            return []

        results = []
        consecutive_errors = 0
        for title, year, plat in candidates[:limit]:
            data = self._get("jeuRecherche", {"recherche": title, "systemeid": PLATFORMS.get(plat, "")})
            if "_error" in data:
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    print(f"Screenscraper: 3 consecutive errors, aborting bulk fetch")
                    break
                continue
            consecutive_errors = 0
            jeux = data.get("response", {}).get("jeux", [])
            if jeux:
                n = self.normalize(jeux[0])
                n["platform"] = plat
                if n["rating"] >= min_rating:
                    if not genre or genre.lower() in n.get("genre", "").lower():
                        results.append(n)
            time.sleep(0.4)
            if len(results) >= limit:
                break

        return results

    def normalize(self, raw: dict) -> dict:
        # Title — prefer US/world, fall back to first
        names = raw.get("noms", [])
        title = ""
        for n in names:
            if isinstance(n, dict) and n.get("region") in ("us", "wor", "ss"):
                title = n.get("text", "")
                if title:
                    break
        if not title and names:
            first = names[0]
            title = first.get("text", "") if isinstance(first, dict) else ""

        # Year
        dates = raw.get("dates", [])
        year = ""
        for d in dates:
            if isinstance(d, dict) and d.get("region") in ("us", "wor", "ss"):
                year = str(d.get("text", ""))[:4]
                if year:
                    break
        if not year and dates:
            year = str(dates[0].get("text", ""))[:4] if isinstance(dates[0], dict) else ""

        # Cover — box-2D front only
        cover_url = ""
        for media in raw.get("medias", []):
            if not isinstance(media, dict):
                continue
            if media.get("type") == "box-2D":
                cover_url = media.get("url", "")
                if cover_url:
                    break

        # Genre
        genre = "Action"
        genres_raw = raw.get("genres", [])
        if isinstance(genres_raw, list) and genres_raw:
            g = genres_raw[0]
            if isinstance(g, dict):
                for n in g.get("noms", []):
                    if isinstance(n, dict) and n.get("langue") in ("en", ""):
                        genre = n.get("text", genre)
                        break

        # Rating
        note = raw.get("note", {})
        rating = 5.0
        if isinstance(note, dict):
            try:
                rating = float(str(note.get("text", "5")).replace(",", "."))
            except (ValueError, TypeError):
                pass

        # Platform
        system = raw.get("systeme", {})
        platform_name = ""
        if isinstance(system, dict):
            platform_name = system.get("text", "")
            if not platform_name:
                for n in system.get("noms", []):
                    if isinstance(n, dict):
                        platform_name = n.get("text", "")
                        break

        # Description
        description = ""
        for s in raw.get("synopsis", []):
            if isinstance(s, dict) and s.get("langue") in ("en", ""):
                description = s.get("text", "")
                if description:
                    break

        return {
            "id": f"ss_{raw.get('id', uuid.uuid4().hex[:8])}",
            "source_id": raw.get("id"),
            "title": title or "Unknown",
            "year": year,
            "genre": genre,
            "genres": [genre],
            "cover_url": cover_url,
            "rating": min(10.0, max(0.0, rating)),
            "description": description,
            "type": "game",
            "platform": platform_name,
            "plugin": "screenscraper",
        }

    def _demo_results(self, query: str) -> list:
        return [{
            "id": "ss_demo_1",
            "title": f"{query} — add Screenscraper credentials in ⚙ Settings",
            "year": "1992", "genre": "Action", "genres": ["Action"],
            "cover_url": "https://placehold.co/256x512/0f3460/e94560?text=NO+CREDS",
            "rating": 7.0, "description": "Add your Screenscraper username/password in Settings.",
            "type": "game", "platform": "SNES", "plugin": "screenscraper",
        }]

    def _demo_bulk(self, year_from: int, year_to: int, limit: int, platform: str = '') -> list:
        import random
        results = []
        platforms_to_use = [platform] if platform and platform in GAME_CATALOG else list(GAME_CATALOG.keys())
        i = 0
        for plat in platforms_to_use:
            for title, year in GAME_CATALOG.get(plat, []):
                if year_from <= year <= year_to:
                    results.append({
                        "id": f"ss_demo_{i}",
                        "title": f"{title} (Demo — add credentials)",
                        "year": str(year), "genre": random.choice(GENRES),
                        "genres": [random.choice(GENRES)],
                        "cover_url": f"https://placehold.co/256x512/0f3460/53d8fb?text={urllib.parse.quote(title[:12])}",
                        "rating": round(random.uniform(7.0, 9.5), 1),
                        "description": "Add Screenscraper credentials in ⚙ Settings for real box art.",
                        "type": "game", "platform": plat, "plugin": "screenscraper",
                    })
                    i += 1
                    if len(results) >= limit:
                        return results
        # Pad if needed
        while len(results) < min(limit, 8):
            results.append({
                "id": f"ss_demo_gen_{i}",
                "title": f"Demo Game {i+1} ({year_from}–{year_to})",
                "year": str(year_from + i % max(1, year_to - year_from)),
                "genre": GENRES[i % len(GENRES)], "genres": [GENRES[i % len(GENRES)]],
                "cover_url": f"https://placehold.co/256x512/0f3460/53d8fb?text=Game+{i+1}",
                "rating": 7.0, "description": "Demo result.",
                "type": "game", "platform": platform or "SNES", "plugin": "screenscraper",
            })
            i += 1
        return results
