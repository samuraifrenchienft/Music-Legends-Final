# spotify_integration.py
# DEPRECATED — Spotify integration has been removed from this bot.
# This file is kept as a stub so legacy imports don't crash.
# The bot uses YouTube for all music data.

class SpotifyIntegration:
    """Stub — Spotify integration is disabled."""

    def search_artists(self, query, limit=5):
        return []

    def search_tracks(self, artist_name, artist_id=None, limit=10):
        return []

    def get_artist(self, artist_id):
        return None

    def generate_card_stats(self, artist):
        return {"impact": 50, "skill": 50, "longevity": 50, "culture": 50, "hype": 50}

    def determine_rarity(self, artist):
        return "common"

    def validate_spotify_url(self, url):
        return False

    def extract_id_from_url(self, url):
        return None


# Global instance (kept for backward compatibility with any stale imports)
spotify_integration = SpotifyIntegration()
