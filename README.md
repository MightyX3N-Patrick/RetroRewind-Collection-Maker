# Retro Rewind Builder

Retro Rewind Builder is a companion tool designed to streamline the creation and management of custom movie and game collections for the **Retro Rewind Video Store Simulator**. It provides a web-based interface to search for metadata, download high-quality covers, and export them directly to the Movie Workshop.

## 🚀 Requirement

To use this tool effectively, you **must** have the following installed:

1.  **Movie Workshop (GitHub)**: [Download from GitHub](https://github.com/BaconCake/retro-rewind-movie-workshop)
2.  **Movie Workshop (Nexus Mods)**: [Download from Nexus Mods](https://www.nexusmods.com/retrorewindvideostoresimulator/mods/82?tab=description)

The Builder acts as the bridge between online databases and these mods, automating the JSON formatting and image placement required for the game to recognize your custom content.

## ✨ Features

* **Multi-Source Search**: Integrated plugins for:
    * **TMDB**: Movies and TV Shows.
    * **IGDB**: Video Game metadata. (dont know if it works)
    * **SteamGridDB**: High-quality game poster art.
    * **Screenscraper**: Retro game metadata and box art.  (dont know if it works)
* **Bulk Fetching**: Quickly populate your library by searching specific year ranges and genres.
* **Auto-Export**: Automatically formats and moves covers/metadata into the local `RRWorkshop` folders.
* **Modern Web UI**: Dark-themed, responsive interface for managing your collection.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MightyX3N-Patrick/RetroRewind-Collection-Maker.git
    cd retro-rewind-builder
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```

4.  **Access the tool:**
    Open your web browser and navigate to `http://127.0.0.1:5000`.

## ⚙️ Configuration

Once the app is running, click the **Settings (⚙️)** icon to input your API keys for the various metadata providers:

* **TMDB**: Get an API key from [TheMovieDB](https://www.themoviedb.org/documentation/api).
* **SteamGridDB**: Get an API key from your [SteamGridDB profile](https://www.steamgriddb.com/profile/preferences/api).

The tool will look for your **Movie Workshop** folder on your Desktop by default.

## 📂 Project Structure

* `app.py`: The Flask backend handling logic and API routing.
* `plugins/`: Specialized modules for different metadata providers.
* `templates/`: The HTML frontend.
* `cache/`: Local storage for your settings and current collection.
* `covers/`: Local storage for downloaded cover images.

## 🤝 Contributing

Feel free to open issues or submit pull requests if you want to add more plugins or improve the UI!
