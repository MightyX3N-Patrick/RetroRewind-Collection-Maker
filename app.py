from flask import Flask, render_template, request, jsonify, send_file
import os, json, urllib.request, urllib.parse, time
from pathlib import Path
from plugins.tmdb_plugin import TMDBPlugin
from plugins.screenscraper_plugin import ScrapperPlugin
from plugins.igdb_plugin import IGDBPlugin
from plugins.steamgriddb_plugin import SteamGridDBPlugin

app = Flask(__name__)
BASE_DIR = Path(__file__).parent

# Where to find the Movie Workshop
WORKSHOP_CONFIG_PATHS = [
    Path(r"C:\Users") / os.environ.get("USERNAME","") / "Desktop" / "RRWorkshop" / "config.json",
    Path(r"C:\Users") / os.environ.get("USERNAME","") / "Desktop" / "RR_Movie_Workshop" / "config.json",
]

CACHE_DIR = BASE_DIR / "cache"
COVERS_DIR = BASE_DIR / "covers"
SETTINGS_FILE = CACHE_DIR / "settings.json"
COLLECTION_FILE = CACHE_DIR / "collection.json"

for d in [CACHE_DIR, COVERS_DIR]:
    d.mkdir(exist_ok=True)

# ── PLUGINS ────────────────────────────────────────────────────────────────

def load_settings():
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text())
    except: pass
    return {}

def save_settings(data):
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))

def load_collection():
    try:
        if COLLECTION_FILE.exists():
            return json.loads(COLLECTION_FILE.read_text())
    except: pass
    return []

def save_collection(items):
    COLLECTION_FILE.write_text(json.dumps(items, indent=2))

def find_workshop():
    """Find the Movie Workshop folder — just needs the exe or shipped_slots.json."""
    def valid(p: Path) -> bool:
        return (p / "RR_Movie_Workshop.exe").exists() or (p / "shipped_slots.json").exists()

    # Check manually saved path first
    settings = load_settings()
    if settings.get("workshop_dir"):
        p = Path(settings["workshop_dir"])
        if valid(p):
            return p

    # Search common locations
    username = os.environ.get("USERNAME", os.environ.get("USER", ""))
    search_bases = [
        Path.home() / "Desktop",
        Path.home() / "Downloads",
        Path.home() / "Documents",
        Path(f"C:/Users/{username}/Desktop") if username else None,
        Path(f"C:/Users/{username}/Downloads") if username else None,
    ]
    names = ["RRWorkshop", "RR_Movie_Workshop", "RR Movie Workshop",
             "RR_VHS_Tool", "RetroRewind Movie Workshop"]

    for base in search_bases:
        if base is None or not base.exists():
            continue
        for name in names:
            p = base / name
            if valid(p):
                return p
        # Also check one level deep (e.g. Desktop/tools/RRWorkshop)
        try:
            for sub in base.iterdir():
                if sub.is_dir() and valid(sub):
                    return sub
        except:
            pass
    return None

# ── GENRE MAPPING ──────────────────────────────────────────────────────────

GENRE_MAP = {
    "Action": "Action", "Adventure": "Action", "Thriller": "Action", "War": "Action",
    "Comedy": "Comedy", "Music": "Comedy",
    "Drama": "Drama", "Documentary": "Drama", "History": "Drama",
    "Horror": "Horror",
    "Science Fiction": "Sci-Fi", "Sci-Fi": "Sci-Fi",
    "Fantasy": "Fantasy",
    "Animation": "Kid", "Family": "Kid",
    "Mystery": "Police", "Crime": "Police",
    "Romance": "Romance",
    "Western": "Western",
    "RPG": "Action", "Shooter": "Action", "Fighting": "Action",
    "Platformer": "Kid", "Puzzle": "Kid",
    "Sports": "Comedy", "Strategy": "Drama",
}

GENRE_CODE = {
    "Action": "Act", "Adult": "Adu", "Comedy": "Com", "Drama": "Dra",
    "Horror": "Hor", "Sci-Fi": "Sci", "Fantasy": "Fan", "Kid": "Kid",
    "Police": "Pol", "Romance": "Rom", "Western": "Wst", "Xmas": "Xma",
}

GENRE_BYTE = {
    "Action": 1, "Adult": 16, "Comedy": 3, "Drama": 4, "Horror": 5,
    "Sci-Fi": 6, "Fantasy": 7, "Kid": 12, "Police": 14,
    "Romance": 10, "Western": 17, "Xmas": 18,
}

# Available T_Sub textures (from shipped_slots)
SUB_SLOTS = [f"T_Sub_{i:02d}" for i in range(1, 100)]

# All Workshop slots: 13 genres x 999 = 12987 total
GENRE_CODES_ALL = ["Act","Adu","Adv","Com","Dra","Fan","Hor","Kid","Pol","Rom","Sci","Wst","Xma"]
ALL_SLOTS = [f"T_Bkg_{g}_{i:03d}" for g in GENRE_CODES_ALL for i in range(1, 1000)]

def get_available_slots(workshop_dir: Path) -> list:
    return ALL_SLOTS

def get_used_slots(workshop_dir: Path) -> dict:
    """Get already-used slots from custom_slots.json"""
    f = workshop_dir / "custom_slots.json"
    if f.exists():
        data = json.loads(f.read_text())
        used = {}
        for genre, entries in data.items():
            for e in entries:
                used[e["bkg_tex"]] = True
        return used
    return {}

def sku_for(genre: str, idx: int, rating: float) -> int:
    PREFIX = {
        "Action": 2, "Comedy": 3, "Drama": 4, "Horror": 5, "Sci-Fi": 6,
        "Fantasy": 10, "Kid": 7, "Police": 1, "Romance": 9,
        "Western": 11, "Adult": 8, "Xmas": 12,
    }
    p = PREFIX.get(genre, 2)
    r = float(rating or 5)
    last2 = 0 if r>=9 else 93 if r>=8 else 70 if r>=7 else 40 if r>=6 else 30 if r>=5 else 13
    return p * 10_000_000 + (idx+1) * 10_000 + last2

# ── PLUGINS ───────────────────────────────────────────────────────────────

PLUGINS = {
    'tmdb': TMDBPlugin(),
    'screenscraper': ScrapperPlugin(),
    'igdb': IGDBPlugin(),
    'steamgriddb': SteamGridDBPlugin(),
}

def apply_saved_settings():
    s = load_settings()
    for pid, config in s.get('plugins', {}).items():
        if pid in PLUGINS:
            PLUGINS[pid].configure(config)

apply_saved_settings()

# ── ROUTES ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    workshop = find_workshop()
    return render_template("index.html",
        workshop_found=workshop is not None,
        workshop_dir=str(workshop) if workshop else ""
    )

@app.route("/api/status")
def status():
    s = load_settings()
    workshop = find_workshop()
    return jsonify({
        "tmdb_configured": bool(s.get("tmdb_key")),
        "workshop_found": workshop is not None,
        "workshop_dir": str(workshop) if workshop else "",
    })

@app.route("/api/settings", methods=["GET"])
def get_settings_raw():
    return jsonify(load_settings())

@app.route("/api/settings", methods=["POST"])
def post_settings():
    data = request.json
    s = load_settings()
    s.update(data)
    save_settings(s)
    return jsonify({"ok": True})

@app.route("/api/plugins")
def get_plugins():
    return jsonify({k: v.info() for k, v in PLUGINS.items()})

@app.route("/api/search")
def search():
    plugin_id = request.args.get("plugin", "tmdb")
    q    = request.args.get("q", "")
    year = request.args.get("year", "")
    if plugin_id not in PLUGINS:
        return jsonify([])
    return jsonify(PLUGINS[plugin_id].search(q, year=year or None))

@app.route("/api/bulk")
def bulk():
    plugin_id  = request.args.get("plugin", "tmdb")
    year_from  = int(request.args.get("year_from", 1985))
    year_to    = int(request.args.get("year_to", 1995))
    genre      = request.args.get("genre", "")
    platform   = request.args.get("platform", "")
    limit      = max(1, int(request.args.get("limit", 50) or 50))
    min_rating = float(request.args.get("min_rating", 0))
    if plugin_id not in PLUGINS:
        return jsonify({"error": "Unknown plugin"})
    results = PLUGINS[plugin_id].bulk_fetch(
        year_from=year_from, year_to=year_to,
        genre=genre, platform=platform,
        limit=limit, min_rating=min_rating
    )
    return jsonify(results)

@app.route("/api/genres")
def genres():
    plugin_id = request.args.get("plugin", "tmdb")
    if plugin_id in PLUGINS:
        return jsonify(PLUGINS[plugin_id].get_genres())
    return jsonify([])

@app.route("/api/platforms")
def platforms():
    plugin_id = request.args.get("plugin", "screenscraper")
    if plugin_id in PLUGINS and hasattr(PLUGINS[plugin_id], "get_platforms"):
        return jsonify(PLUGINS[plugin_id].get_platforms())
    return jsonify([])

@app.route("/api/plugin_config", methods=["POST"])
def plugin_config():
    data = request.json
    pid = data.get("plugin")
    config = data.get("config", {})
    if pid not in PLUGINS:
        return jsonify({"error": "Unknown plugin"}), 400
    PLUGINS[pid].configure(config)
    s = load_settings()
    s.setdefault("plugins", {})[pid] = config
    save_settings(s)
    return jsonify({"ok": True, "configured": PLUGINS[pid].is_configured()})

@app.route("/api/collection", methods=["GET"])
def get_collection():
    return jsonify(load_collection())

@app.route("/api/collection/add", methods=["POST"])
def add_item():
    item = request.json.get("item")
    col = load_collection()
    if item and item["id"] not in [i["id"] for i in col]:
        col.append(item)
        save_collection(col)
    return jsonify({"count": len(col), "items": col})

@app.route("/api/collection/add_bulk", methods=["POST"])
def add_bulk():
    new_items = request.json.get("items",[])
    col = load_collection()
    existing = {i["id"] for i in col}
    added = 0
    for item in new_items:
        if item["id"] not in existing:
            col.append(item); existing.add(item["id"]); added += 1
    save_collection(col)
    return jsonify({"added": added, "count": len(col), "items": col})

@app.route("/api/collection/remove", methods=["POST"])
def remove_item():
    item_id = request.json.get("id")
    col = [i for i in load_collection() if i["id"] != item_id]
    save_collection(col)
    return jsonify({"count": len(col), "items": col})

@app.route("/api/collection/clear", methods=["POST"])
def clear_col():
    save_collection([])
    return jsonify({"count": 0, "items": []})

@app.route("/api/export_to_workshop", methods=["POST"])
def export_to_workshop():
    """
    Export collection to Movie Workshop data files.
    Writes custom_slots.json and replacements.json into the Workshop folder,
    and downloads cover images to the covers/ folder.
    Then the user just clicks 'Ship to Store' in Movie Workshop.
    """
    workshop = find_workshop()
    if not workshop:
        return jsonify({"error": "Movie Workshop not found. Set the path in Settings."}), 400

    items = load_collection()
    if not items:
        return jsonify({"error": "Collection is empty"}), 400

    overwrite = request.json.get("overwrite", False) if request.json else False

    # Group items by genre
    by_genre = {}
    for item in items:
        g = GENRE_MAP.get(item.get("genre",""), "Drama")
        by_genre.setdefault(g, []).append(item)

    # Build slot map: gcode -> [slots]
    slots_by_genre = {}
    for slot in get_available_slots(workshop):
        parts = slot.split("_")
        if len(parts) >= 4:
            slots_by_genre.setdefault(parts[2], list(slots_by_genre.get(parts[2], [])) or []).append(slot)

    # Rebuild slots_by_genre properly
    slots_by_genre = {}
    for slot in get_available_slots(workshop):
        parts = slot.split("_")
        if len(parts) >= 4:
            gcode = parts[2]
            if gcode not in slots_by_genre:
                slots_by_genre[gcode] = []
            slots_by_genre[gcode].append(slot)

    cs_file = workshop / "custom_slots.json"

    if overwrite:
        # Start completely fresh
        new_custom   = {}
        replacements = {}
        for fname in ["base_slot_edits.json"]:
            try: (workshop / fname).write_text("{}")
            except: pass
    else:
        # Preserve existing
        new_custom = {}
        if cs_file.exists():
            try: new_custom = json.loads(cs_file.read_text())
            except: pass
        replacements = {}
        try: replacements = json.loads((workshop / "replacements.json").read_text())
        except: pass

    sub_idx = 1

    errors = []
    written = 0
    for genre, genre_items in by_genre.items():
        gcode = GENRE_CODE.get(genre, genre[:3])
        available_slots = slots_by_genre.get(gcode, [])

        # Find next unused slot
        used_in_genre = {e["bkg_tex"] for e in new_custom.get(genre, [])}
        free_slots = [s for s in available_slots if s not in used_in_genre]

        if genre not in new_custom:
            new_custom[genre] = []

        for item in genre_items:
            if not free_slots:
                errors.append(f"No free slots for {genre} — skipping '{item['title']}'")
                continue

            slot = free_slots.pop(0)
            sub_tex = f"T_Sub_{sub_idx:02d}" if sub_idx <= 86 else "T_Sub_01"
            sub_idx += 1

            # Download cover image
            cover_url = item.get("cover_url","")
            cover_path = ""
            if cover_url and "placehold" not in cover_url:
                try:
                    ext = cover_url.split(".")[-1].split("?")[0].lower()
                    if ext not in ("jpg","jpeg","png","webp"): ext = "jpg"
                    # Name file after movie title — easy to verify what was downloaded
                    safe_title = "".join(ch for ch in item.get("title","unknown") if ch.isalnum() or ch in " -_").strip().replace(" ","_")[:60]
                    dest = COVERS_DIR / f"{safe_title}.{ext}"
                    req = urllib.request.Request(cover_url, headers={"User-Agent":"RRBuilder/1.0"})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        dest.write_bytes(r.read())
                    cover_path = str(dest)
                except Exception as e:
                    errors.append(f"Cover download failed for {item['title']}: {e}")

            entry = {
                "bkg_tex": slot,
                "sub_tex": sub_tex,
                "pn_name": item.get("title","Unknown"),
                "ls": 1,
                "lsc": 4,
                "sku": sku_for(genre, len(new_custom[genre]), item.get("rating", 5.0)),
                "ntu": False,
                "last_edited_at": "2026-01-01T00:00:00",
            }
            new_custom[genre].append(entry)
            written += 1

            if cover_path:
                replacements[slot] = {
                    "path": cover_path,
                    "offset_x": 18,
                    "offset_y": -197,
                    "zoom": 0.778,
                }

    # Write files
    cs_file.write_text(json.dumps(new_custom, indent=4))
    (workshop / "replacements.json").write_text(json.dumps(replacements, indent=4))

    # Update edited_slots.json
    edited = list(replacements.keys())
    (workshop / "edited_slots.json").write_text(json.dumps(edited, indent=4))

    total = sum(len(v) for v in new_custom.values())
    skipped_count = len([e for e in errors if "No free slots" in e])
    msg = f"Exported {written} / {len(items)} movies to Workshop ({total} / 12987 slots used)."
    if skipped_count:
        msg += f" {skipped_count} skipped (no slots)."
    return jsonify({
        "ok": True,
        "message": msg,
        "warnings": errors,
        "total_in_workshop": total,
        "workshop_dir": str(workshop),
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
