# Retro Rewind Builder

Retro Rewind Builder is a companion tool for creating and managing custom movie and game collections for the **Retro Rewind Video Store Simulator**. It provides a web-based interface to search metadata, download covers, and export them directly to the Movie Workshop.

## 🚀 Requirements

You **must** have one of these installed:

1. **Movie Workshop (GitHub)**: [Download from GitHub](https://github.com/BaconCake/retro-rewind-movie-workshop)
2. **Movie Workshop (Nexus Mods)**: [Download from Nexus Mods](https://www.nexusmods.com/retrorewindvideostoresimulator/mods/82?tab=description)

## ✨ Features

* **Multi-Source Search**: Plugins for:
  * **TMDB** — Movies and TV shows (requires free API key)
  * **IGDB** — Video game metadata (requires free Twitch API key)
  * **SteamGridDB** — High-quality game poster art (requires free API key)
  * **Screenscraper** — Retro game metadata and box art
  * **MyAnimeList** — Anime series and films (no API key needed)
* **Bulk Fetching**: Populate your library by year range and genre.
* **Auto-Export**: Formats and moves covers/metadata into your RRWorkshop folder.
* **Plugin System**: Drop any `*_plugin.py` into the `plugins/` folder and it loads automatically — no code changes needed. Plugins can also inject sidebar sections, modals, JavaScript, and custom API routes.
* **Modern Web UI**: Dark-themed interface for managing your collection.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MightyX3N-Patrick/RetroRewind-Collection-Maker.git
   cd RetroRewind-Collection-Maker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open in browser:** `http://127.0.0.1:5000`

## ⚙️ Configuration

Click the **Settings (⚙️)** icon to enter API keys:

* **TMDB** — [themoviedb.org](https://www.themoviedb.org/documentation/api)
* **SteamGridDB** — [steamgriddb.com](https://www.steamgriddb.com/profile/preferences/api)
* **IGDB** — Free Twitch Developer credentials at [dev.twitch.tv](https://dev.twitch.tv/console)
* **MyAnimeList** — No key needed, works out of the box

The tool searches for your Movie Workshop folder automatically (Desktop, Downloads, Documents). You can also set the path manually in Settings.

## 🔌 Writing a Plugin

Drop a file named `anything_plugin.py` into `plugins/`. It will be loaded automatically on next startup.

A plugin must subclass `BasePlugin` and implement `search()` and `bulk_fetch()`. It can optionally implement these UI hooks:

| Hook | What it does |
|---|---|
| `sidebar_html()` | Injects HTML into the sidebar |
| `head_html()` | Injects into `<head>` (CSS etc.) |
| `body_html()` | Injects into `<body>` (modals, panels) |
| `js_html()` | Injects JavaScript |
| `routes(app)` | Registers extra Flask routes |

See `plugins/base.py` for the full interface and docstrings.

## 📂 Project Structure

* `app.py` — Flask backend
* `plugins/` — Metadata provider plugins (auto-discovered)
* `templates/` — HTML frontend
* `cache/` — Settings and collection data
* `covers/` — Downloaded cover images

## 🤝 Contributing

Open issues or PRs to add plugins or improve the UI!
