# models/artist.py
"""
Artist model — stores artist/channel metadata used for card generation.
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime
from models.base import Model
import uuid


class Artist(Model):
    __tablename__ = "artists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    source = Column(String(50))          # 'youtube', 'lastfm', etc.
    external_ref = Column(String(200))   # YouTube channel ID, Last.fm name, etc.
    image_url = Column(String(500))
    tier = Column(String(20), default="D")
    popularity = Column(Integer, default=0)
    artist_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def create(cls, **kwargs):
        artist = cls(**kwargs)
        artist.save()
        return artist

    @classmethod
    def get_by_id(cls, id):
        return None  # Real lookups require get_db() session

    @classmethod
    def where_in(cls, field, values):
        return []  # Real lookups require get_db() session
