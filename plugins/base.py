"""Base plugin interface for Retro Rewind Builder plugins."""

from abc import ABC, abstractmethod
from typing import Optional


class BasePlugin(ABC):
    """
    All plugins must implement this interface.
    Plugins provide search and bulk_fetch capabilities,
    returning normalized VHS cover items.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this plugin fetches."""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Emoji or icon for the plugin."""
        pass

    @property
    def media_type(self) -> str:
        """'movie', 'game', or 'both'"""
        return "movie"

    def info(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "media_type": self.media_type,
            "configured": self.is_configured(),
            "genres": self.get_genres(),
            "has_platforms": bool(hasattr(self, "get_platforms") and self.get_platforms()),
            "config_fields": self.config_fields(),
        }

    def config_fields(self) -> list:
        """Return list of {key, label, type} for settings UI. Override in subclass."""
        return []

    def configure(self, config: dict):
        """Store API keys or other config. Override in subclass."""
        pass

    def is_configured(self) -> bool:
        """Return True if plugin is ready to use (has API key etc)."""
        return True

    @abstractmethod
    def search(self, query: str, year: Optional[str] = None) -> list:
        """Search for a specific title. Returns list of normalized items."""
        pass

    @abstractmethod
    def bulk_fetch(self, year_from: int, year_to: int, genre: str = '',
                   limit: int = 50, min_rating: float = 0, **kwargs) -> list:
        """Bulk fetch items by year range. Returns list of normalized items."""
        pass

    def get_genres(self) -> list:
        """Return list of genre strings this plugin supports."""
        return []

    def normalize(self, raw: dict) -> dict:
        """
        Normalize a raw API result into our standard item format:
        {
            id, title, year, genre, cover_url,
            rating, description, type, plugin
        }
        """
        raise NotImplementedError
