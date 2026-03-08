from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, CHAR
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import TypeDecorator, SchemaType
from sqlalchemy.dialects import postgresql
import uuid
import json
from datetime import datetime

Base = declarative_base()

class UUIDType(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID())
        else:
            return dialect.type_descriptor(CHAR(36))
    def process_bind_param(self, value, dialect):
        if value is None: return value
        if dialect.name == 'postgresql': return str(value)
        else: return str(value)
    def process_result_value(self, value, dialect):
        if value is None: return value
        # Backward compatibility: tolerate legacy non-UUID identifiers.
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return str(value)

class JSONType(TypeDecorator):
    impl = Text
    cache_ok = True
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.JSONB())
        else:
            return dialect.type_descriptor(Text())
    def process_bind_param(self, value, dialect):
        if value is None: return value
        if dialect.name == 'postgresql': return value
        else: return json.dumps(value)
    def process_result_value(self, value, dialect):
        if value is None: return value
        if dialect.name == 'postgresql': return value
        else: return json.loads(value)

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True)
    username = Column(String)
    is_dev = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    card_instances = relationship("CardInstance", back_populates="owner")
    created_packs = relationship("Pack", back_populates="creator")
    transactions_as_buyer = relationship("Transaction", foreign_keys="Transaction.buyer_id", back_populates="buyer")
    transactions_as_seller = relationship("Transaction", foreign_keys="Transaction.seller_id", back_populates="seller")

class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"
    
    video_id = Column(String, primary_key=True)
    title = Column(String)
    thumbnail_url = Column(String)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    channel_title = Column(String)
    channel_id = Column(String)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    card_definitions = relationship("CardDefinition", back_populates="source_video")

class CardDefinition(Base):
    __tablename__ = "card_definitions"
    
    card_def_id = Column(Integer, primary_key=True, autoincrement=True)
    source_video_id = Column(String, ForeignKey("youtube_videos.video_id"))
    card_name = Column(String, nullable=False)
    rarity = Column(String, default="Common")
    power = Column(Integer, default=50)
    attributes = Column(JSONType)  # JSON for flexible stats
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_video = relationship("YouTubeVideo", back_populates="card_definitions")
    instances = relationship("CardInstance", back_populates="definition")

class CardInstance(Base):
    __tablename__ = "card_instances"
    
    instance_id = Column(Integer, primary_key=True, autoincrement=True)
    card_def_id = Column(Integer, ForeignKey("card_definitions.card_def_id"))
    owner_user_id = Column(String, ForeignKey("users.user_id"))
    serial_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    definition = relationship("CardDefinition", back_populates="instances")
    owner = relationship("User", back_populates="card_instances")
    pack_contents = relationship("PackContent", back_populates="card_instance")

class Pack(Base):
    __tablename__ = "packs"
    
    pack_id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(String, ForeignKey("users.user_id"))
    main_hero_instance_id = Column(Integer, ForeignKey("card_instances.instance_id"))
    pack_type = Column(String, default="gold")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", back_populates="created_packs")
    hero_instance = relationship("CardInstance", foreign_keys=[main_hero_instance_id])
    contents = relationship("PackContent", back_populates="pack")
    marketplace_item = relationship("MarketplaceItem", back_populates="pack")

class PackContent(Base):
    __tablename__ = "pack_contents"
    
    pack_id = Column(Integer, ForeignKey("packs.pack_id"), primary_key=True)
    instance_id = Column(Integer, ForeignKey("card_instances.instance_id"), primary_key=True)
    position = Column(Integer)  # 1 for hero, 2-5 for additional cards
    
    # Relationships
    pack = relationship("Pack", back_populates="contents")
    card_instance = relationship("CardInstance", back_populates="pack_contents")

class MarketplaceItem(Base):
    __tablename__ = "marketplace_items"
    
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    pack_id = Column(Integer, ForeignKey("packs.pack_id"))
    price = Column(Float, default=9.99)
    listed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    stock = Column(String, default="unlimited")
    
    # Relationships
    pack = relationship("Pack", back_populates="marketplace_item")
    transactions = relationship("Transaction", back_populates="marketplace_item")

class Transaction(Base):
    __tablename__ = "transactions"
    
    tx_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("marketplace_items.item_id"))
    buyer_id = Column(String, ForeignKey("users.user_id"))
    seller_id = Column(String, ForeignKey("users.user_id"))
    tx_date = Column(DateTime, default=datetime.utcnow)
    price = Column(Float)
    
    # Relationships
    marketplace_item = relationship("MarketplaceItem", back_populates="transactions")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="transactions_as_buyer")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="transactions_as_seller")

from .trade import Trade
from .purchase_sqlalchemy import Purchase
from .drop import Drop
from .audit import AuditLog
from .tma import TmaLinkCode, PendingTmaBattle
