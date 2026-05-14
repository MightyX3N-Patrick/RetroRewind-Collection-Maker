"""Base plugin interface for Retro Rewind Builder plugins."""

from abc import ABC, abstractmethod
from typing import Optional


class BasePlugin(ABC):
    """
    All plugins must implement this interface.

    ── Data provider hooks (required) ────────────────────────────────────────
    search()       Search for a specific title
    bulk_fetch()   Bulk fetch by year range

    ── UI injection hooks (all optional) ─────────────────────────────────────
    sidebar_html() HTML injected into the sidebar panel
    head_html()    HTML injected into <head> (CSS, meta tags)
    body_html()    HTML injected at end of <body> (modals, panels)
    js_html()      JavaScript injected just before </body>
    routes(app)    Register extra Flask routes on the app
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name shown in the UI."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description shown in settings."""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Emoji shown next to the plugin name."""
        pass

    @property
    def media_type(self) -> str:
        """'movie', 'game', or 'both'"""
        return "movie"

    # ── Config ────────────────────────────────────────────────────────────────

    def config_fields(self) -> list:
        """Return list of {key, label, type, hint?} for the settings UI."""
        return []

    def configure(self, config: dict):
        """Apply saved config (API keys etc). Called at startup and on save."""
        pass

    def is_configured(self) -> bool:
        """Return True if the plugin is ready to use."""
        return True

    def info(self) -> dict:
        return {
            "name":          self.name,
            "description":   self.description,
            "icon":          self.icon,
            "media_type":    self.media_type,
            "configured":    self.is_configured(),
            "genres":        self.get_genres(),
            "has_platforms": bool(hasattr(self, "get_platforms") and self.get_platforms()),
            "config_fields": self.config_fields(),
        }

    # ── Data provider ─────────────────────────────────────────────────────────

    @abstractmethod
    def search(self, query: str, year: Optional[str] = None) -> list:
        """Search for a specific title. Return list of normalised items."""
        pass

    @abstractmethod
    def bulk_fetch(self, year_from: int, year_to: int, genre: str = "",
                   limit: int = 50, min_rating: float = 0, **kwargs) -> list:
        """Bulk fetch by year range. Return list of normalised items."""
        pass

    def get_genres(self) -> list:
        """Return genre strings this plugin supports."""
        return []

    def normalize(self, raw: dict) -> dict:
        """
        Convert raw API data to standard item format:
        { id, title, year, genre, genres, cover_url, rating, type, plugin }
        """
        raise NotImplementedError

    # ── UI injection hooks (all optional — return "" to opt out) ──────────────

    def sidebar_html(self) -> str:
        """
        HTML injected into the sidebar.
        Wrap in a <div class="sidebar-section"> for consistent styling.
        Example:
            return '''
            <div class="sidebar-section">
              <div class="sidebar-label">My Plugin</div>
              <button class="btn" onclick="myPluginAction()">Do Thing</button>
            </div>'''
        """
        return ""

    def head_html(self) -> str:
        """
        HTML injected inside <head>.
        Use for <style> blocks or <link> tags.
        Example:
            return '<style>.my-panel { background: #1a1a2e; }</style>'
        """
        return ""

    def body_html(self) -> str:
        """
        HTML injected at the end of <body>, before scripts.
        Use for modals, panels, or hidden containers.
        Example:
            return '<div id="myModal" style="display:none">...</div>'
        """
        return ""

    def js_html(self) -> str:
        """
        JavaScript injected just before </body>.
        Do NOT include <script> tags — just the JS code.
        Example:
            return 'function myPluginAction() { fetch("/api/myplugin/run"); }'
        """
        return ""

    def routes(self, app) -> None:
        """
        Register extra Flask routes on the app instance.
        Called once at startup after all plugins are loaded.
        Example:
            @app.route("/api/myplugin/data")
            def myplugin_data():
                return jsonify({"hello": "world"})
        """
        pass
