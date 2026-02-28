import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import (
    Boolean,
    Column,
    create_engine,
    DateTime,
    desc,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import exists

from models import User, UserBalances, PackPurchase, CreatorPacks, Card, UserCard, DevPackSupply, CardInstance, CreatorPackLimits, TradeHistory, UserBattleStats, CosmeticCatalog, UserCosmetic, CardCosmetic, BattleLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base for SQLAlchemy declarative models
Base = declarative_base()


class Database:
    _instance = None
    _engine = None
    _Session = None
    _database_url: str = None
    _db_type: str = None

    def __new__(cls, database_url: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            if database_url:
                cls._instance._initialize(database_url)
        return cls._instance

    def _initialize(self, database_url: str):
        if self._engine is not None:
            return  # Already initialized

        self._database_url = database_url
        if database_url.startswith("sqlite"):
            self._db_type = "sqlite"
            db_path = database_url.replace("sqlite:///", "")
            # Ensure the directory exists for SQLite
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self._engine = create_engine(
                database_url, connect_args={"check_same_thread": False}
            )
        else:
            self._db_type = "postgresql"
            self._engine = create_engine(database_url)

        self._Session = sessionmaker(bind=self._engine)
        self._create_tables_if_not_exists()

    def _create_tables_if_not_exists(self):
        """Create database tables if they do not exist."""
        # This will create tables for all models inherited from Base
        Base.metadata.create_all(self._engine)

    def get_session(self) -> Session:
        """Returns a new SQLAlchemy session."""
        if self._Session is None:
            raise Exception("Database not initialized. Call Database(database_url) first.")
        return self._Session()





    def _init_postgresql(self):
        """
        Initializes PostgreSQL-specific database schema and functions.
        This includes creating the `transactions` table.
        """
        try:
            # Enable uuid-ossp for UUID generation
            # This is a PostgreSQL-specific command, so we'll execute it via SQLAlchemy's connection
            with self._engine.connect() as connection:
                connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                connection.commit()

            logger.info("PostgreSQL database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL database: {e}")
            raise # Re-raise the exception after logging

    def _init_sqlite(self):
        """Initializes SQLite-specific database schema."""
        # For now, all SQLite initialization is handled by SQLAlchemy's create_all
        pass

    def get_user(self, user_id: str) -> Optional[User]:
        session = self.get_session()
        try:
            return session.query(User).filter_by(user_id=user_id).first()
        finally:
            session.close()

    def create_user(self, user_id: str, username: str) -> User:
        session = self.get_session()
        try:
            user = User(user_id=user_id, username=username)
            session.add(user)
            session.commit()
            return user
        except IntegrityError:
            session.rollback()
            raise ValueError(f"User with ID {user_id} or username {username} already exists.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user {username}: {e}")
            raise
        finally:
            session.close()

    def update_username(self, user_id: str, new_username: str) -> bool:
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.username = new_username
                session.commit()
                return True
            return False
        except IntegrityError:
            session.rollback()
            raise ValueError(f"Username {new_username} is already taken.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating username for {user_id}: {e}")
            raise
        finally:
            session.close()

    def get_user_balance(self, user_id: str) -> Optional[UserBalances]:
        session = self.get_session()
        try:
            return session.query(UserBalances).filter_by(user_id=user_id).first()
        finally:
            session.close()

    def update_user_balance(self, user_id: str, currency: int = 0, dust: int = 0) -> bool:
        session = self.get_session()
        try:
            balance = session.query(UserBalances).filter_by(user_id=user_id).first()
            if balance:
                balance.currency += currency
                balance.dust += dust
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating balance for user {user_id}: {e}")
            raise
        finally:
            session.close()

    def record_pack_purchase(
        self, user_id: str, pack_id: str, cost: int, currency_type: str, cards_pulled: List[str]
    ) -> bool:
        session = self.get_session()
        try:
            purchase = PackPurchase(
                user_id=user_id,
                pack_id=pack_id,
                cost=cost,
                currency_type=currency_type,
                cards_pulled=json.dumps(cards_pulled),
            )
            session.add(purchase)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording pack purchase for user {user_id}: {e}")
            raise
        finally:
            session.close()

    def get_all_cards(self) -> List[Card]:
        session = self.get_session()
        try:
            return session.query(Card).all()
        finally:
            session.close()

    def get_card_by_id(self, card_id: str) -> Optional[Card]:
        session = self.get_session()
        try:
            return session.query(Card).filter_by(card_id=card_id).first()
        finally:
            session.close()

    def add_card_to_collection(
        self, user_id: str, card_id: str, quantity: int = 1, acquired_from: str = "pack"
    ) -> bool:
        session = self.get_session()
        try:
            user_card = (
                session.query(UserCard)
                .filter_by(user_id=user_id, card_id=card_id)
                .first()
            )
            if user_card:
                user_card.quantity += quantity
            else:
                user_card = UserCard(
                    user_id=user_id,
                    card_id=card_id,
                    quantity=quantity,
                    acquired_from=acquired_from,
                )
                session.add(user_card)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error adding card {card_id} to user {user_id}'s collection: {e}"
            )
            raise
        finally:
            session.close()

    def remove_card_from_collection(self, user_id: str, card_id: str, quantity: int = 1) -> bool:
        session = self.get_session()
        try:
            user_card = (
                session.query(UserCard)
                .filter_by(user_id=user_id, card_id=card_id)
                .first()
            )
            if user_card and user_card.quantity >= quantity:
                user_card.quantity -= quantity
                if user_card.quantity == 0:
                    session.delete(user_card)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error removing card {card_id} from user {user_id}'s collection: {e}"
            )
            raise
        finally:
            session.close()

    def get_user_cards(self, user_id: str) -> List[Dict]:
        session = self.get_session()
        try:
            user_cards = (
                session.query(UserCard, Card)
                .join(Card, UserCard.card_id == Card.card_id)
                .filter(UserCard.user_id == user_id)
                .all()
            )
            return [
                {
                    "card_id": uc.card_id,
                    "quantity": uc.quantity,
                    "acquired_from": uc.acquired_from,
                    "acquired_at": uc.acquired_at.isoformat(),
                    "is_favorite": uc.is_favorite,
                    "card_name": c.card_name,
                    "card_set": c.card_set,
                    "card_type": c.card_type,
                    "rarity": c.rarity,
                    "metadata": c.metadata,
                }
                for uc, c in user_cards
            ]
        finally:
            session.close()

    def get_user_card_count(self, user_id: str, card_id: str) -> int:
        session = self.get_session()
        try:
            user_card = (
                session.query(UserCard)
                .filter_by(user_id=user_id, card_id=card_id)
                .first()
            )
            return user_card.quantity if user_card else 0
        finally:
            session.close()

    def update_card_favorite_status(self, user_id: str, card_id: str, is_favorite: bool) -> bool:
        session = self.get_session()
        try:
            user_card = (
                session.query(UserCard)
                .filter_by(user_id=user_id, card_id=card_id)
                .first()
            )
            if user_card:
                user_card.is_favorite = is_favorite
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error updating favorite status for card {card_id} for user {user_id}: {e}"
            )
            raise
        finally:
            session.close()

    def get_all_creator_packs(self) -> List[CreatorPacks]:
        session = self.get_session()
        try:
            return session.query(CreatorPacks).all()
        finally:
            session.close()

    def get_creator_pack_by_id(self, pack_id: str) -> Optional[CreatorPacks]:
        session = self.get_session()
        try:
            return session.query(CreatorPacks).filter_by(pack_id=pack_id).first()
        finally:
            session.close()

    def get_dev_pack_supply(self, pack_id: str) -> Optional[DevPackSupply]:
        session = self.get_session()
        try:
            return session.query(DevPackSupply).filter_by(pack_id=pack_id).first()
        finally:
            session.close()

    def update_dev_pack_supply(self, pack_id: str, quantity_change: int) -> bool:
        session = self.get_session()
        try:
            supply = session.query(DevPackSupply).filter_by(pack_id=pack_id).first()
            if supply:
                supply.quantity += quantity_change
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating dev pack supply for {pack_id}: {e}")
            raise
        finally:
            session.close()

    def get_creator_pack_limit(self, pack_id: str) -> Optional[CreatorPackLimits]:
        session = self.get_session()
        try:
            return session.query(CreatorPackLimits).filter_by(pack_id=pack_id).first()
        finally:
            session.close()

    def update_creator_pack_limit(self, pack_id: str, new_limit: int) -> bool:
        session = self.get_session()
        try:
            limit = session.query(CreatorPackLimits).filter_by(pack_id=pack_id).first()
            if limit:
                limit.max_supply = new_limit
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating creator pack limit for {pack_id}: {e}")
            raise
        finally:
            session.close()

    def get_card_instance(self, instance_id: str) -> Optional[CardInstance]:
        session = self.get_session()
        try:
            return session.query(CardInstance).filter_by(instance_id=instance_id).first()
        finally:
            session.close()

    def create_card_instance(
        self,
        card_id: str,
        owner_id: str,
        metadata: Dict,
        is_for_sale: bool = False,
        sale_price: Optional[int] = None,
    ) -> CardInstance:
        session = self.get_session()
        try:
            instance = CardInstance(
                card_id=card_id,
                owner_id=owner_id,
                metadata=json.dumps(metadata),
                is_for_sale=is_for_sale,
                sale_price=sale_price,
            )
            session.add(instance)
            session.commit()
            return instance
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating card instance for card {card_id}: {e}")
            raise
        finally:
            session.close()

    def update_card_instance_sale_status(
        self, instance_id: str, is_for_sale: bool, sale_price: Optional[int] = None
    ) -> bool:
        session = self.get_session()
        try:
            instance = session.query(CardInstance).filter_by(instance_id=instance_id).first()
            if instance:
                instance.is_for_sale = is_for_sale
                instance.sale_price = sale_price
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating sale status for card instance {instance_id}: {e}")
            raise
        finally:
            session.close()

    def transfer_card_instance(
        self, instance_id: str, new_owner_id: str, transfer_price: Optional[int] = None
    ) -> bool:
        session = self.get_session()
        try:
            instance = session.query(CardInstance).filter_by(instance_id=instance_id).first()
            if instance:
                original_owner_id = instance.owner_id
                instance.owner_id = new_owner_id
                instance.is_for_sale = False
                instance.sale_price = None

                trade = TradeHistory(
                    instance_id=instance_id,
                    old_owner_id=original_owner_id,
                    new_owner_id=new_owner_id,
                    trade_price=transfer_price,
                )
                session.add(trade)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error transferring card instance {instance_id} to {new_owner_id}: {e}"
            )
            raise
        finally:
            session.close()

    def get_user_card_instances(self, user_id: str) -> List[CardInstance]:
        session = self.get_session()
        try:
            return session.query(CardInstance).filter_by(owner_id=user_id).all()
        finally:
            session.close()

    def get_market_listings(self) -> List[CardInstance]:
        session = self.get_session()
        try:
            return session.query(CardInstance).filter_by(is_for_sale=True).all()
        finally:
            session.close()

    def unlock_cosmetic_for_user(self, user_id: str, cosmetic_id: str) -> bool:
        session = self.get_session()
        try:
            # Check if cosmetic already unlocked
            exists_query = session.query(exists().where(
                UserCosmetic.user_id == user_id and UserCosmetic.cosmetic_id == cosmetic_id
            )).scalar()

            if not exists_query:
                user_cosmetic = UserCosmetic(user_id=user_id, cosmetic_id=cosmetic_id)
                session.add(user_cosmetic)
                session.commit()
                return True
            return False # Cosmetic already unlocked
        except Exception as e:
            session.rollback()
            logger.error(f"Error unlocking cosmetic {cosmetic_id} for user {user_id}: {e}")
            return False
        finally:
            session.close()

    def get_user_cosmetics(self, user_id: str) -> List[CosmeticCatalog]:
        session = self.get_session()
        try:
            cosmetics = session.query(CosmeticCatalog).join(
                UserCosmetic, CosmeticCatalog.cosmetic_id == UserCosmetic.cosmetic_id
            ).filter(UserCosmetic.user_id == user_id).all()
            return cosmetics
        finally:
            session.close()

    def apply_cosmetic_to_card(self, user_id: str, card_instance_id: str, cosmetic_id: str) -> bool:
        session = self.get_session()
        try:
            # Ensure user owns the card instance and the cosmetic
            card_instance = session.query(CardInstance).filter_by(
                instance_id=card_instance_id, owner_id=user_id
            ).first()
            user_cosmetic = session.query(UserCosmetic).filter_by(
                user_id=user_id, cosmetic_id=cosmetic_id
            ).first()

            if not card_instance or not user_cosmetic:
                logger.warning(f"User {user_id} does not own card instance {card_instance_id} or cosmetic {cosmetic_id}.")
                return False

            # Apply cosmetic
            card_cosmetic = CardCosmetic(
                instance_id=card_instance_id,
                cosmetic_id=cosmetic_id,
                applied_at=datetime.utcnow()
            )
            session.add(card_cosmetic)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error applying cosmetic {cosmetic_id} to card instance {card_instance_id}: {e}")
            return False
        finally:
            session.close()

    def get_card_cosmetics(self, card_instance_id: str) -> List[CosmeticCatalog]:
        session = self.get_session()
        try:
            cosmetics = session.query(CosmeticCatalog).join(
                CardCosmetic, CosmeticCatalog.cosmetic_id == CardCosmetic.cosmetic_id
            ).filter(CardCosmetic.instance_id == card_instance_id).all()
            return cosmetics
        finally:
            session.close()

    def get_available_cosmetics(self) -> List[CosmeticCatalog]:
        session = self.get_session()
        try:
            return session.query(CosmeticCatalog).all()
        finally:
            session.close()

    def get_user_battle_stats(self, user_id: str) -> Optional[UserBattleStats]:
        session = self.get_session()
        try:
            return session.query(UserBattleStats).filter_by(user_id=user_id).first()
        finally:
            session.close()

    def update_user_battle_stats(
        self, user_id: str, wins: int = 0, losses: int = 0, draws: int = 0
    ) -> bool:
        session = self.get_session()
        try:
            stats = session.query(UserBattleStats).filter_by(user_id=user_id).first()
            if stats:
                stats.wins += wins
                stats.losses += losses
                stats.draws += draws
            else:
                stats = UserBattleStats(user_id=user_id, wins=wins, losses=losses, draws=draws)
                session.add(stats)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating battle stats for user {user_id}: {e}")
            raise
        finally:
            session.close()

    def get_all_battle_logs(self) -> List[BattleLog]:
        session = self.get_session()
        try:
            return session.query(BattleLog).order_by(desc(BattleLog.completed_at)).all()
        finally:
            session.close()

    def get_battle_logs_for_user(self, user_id: str) -> List[BattleLog]:
        session = self.get_session()
        try:
            return (
                session.query(BattleLog)
                .filter(
                    (BattleLog.player_a_id == user_id) | (BattleLog.player_b_id == user_id)
                )
                .order_by(desc(BattleLog.completed_at))
                .all()
            )
        finally:
            session.close()

    def record_match(self, match_data: Dict) -> bool:
            """Record a completed match"""
            try:
                session = self.get_session()

                new_match = BattleLog(
                    match_id=match_data['match_id'],
                    player_a_id=match_data['player_a_id'],
                    player_b_id=match_data['player_b_id'],
                    winner_id=match_data['winner_id'],
                    final_score_a=match_data['final_score_a'],
                    final_score_b=match_data['final_score_b'],
                    completed_at=datetime.utcnow(),
                    match_type=match_data.get('match_type', 'casual')
                )
                session.add(new_match)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                print(f"Error recording match: {e}")
                return False
            finally:
                session.close()

    def get_match_history(self, player_id: str, limit: int = 10) -> List[Dict]:
        """Retrieves match history for a given player."""
        session = self.get_session()
        try:
            matches = (
                session.query(BattleLog)
                .filter(
                    (BattleLog.player_a_id == player_id) | (BattleLog.player_b_id == player_id)
                )
                .order_by(desc(BattleLog.completed_at))
                .limit(limit)
                .all()
            )

            history = []
            for match in matches:
                history.append({
                    "match_id": match.match_id,
                    "player_a_id": match.player_a_id,
                    "player_b_id": match.player_b_id,
                    "winner_id": match.winner_id,
                    "final_score_a": match.final_score_a,
                    "final_score_b": match.final_score_b,
                    "completed_at": match.completed_at.isoformat() if match.completed_at else None,
                    "match_type": match.match_type,
                })
            return history
        except Exception as e:
            logger.error(f"Error retrieving match history for player {player_id}: {e}")
            return []
        finally:
            session.close()

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Retrieves top players based on battle statistics."""
        session = self.get_session()
        try:
            leaderboard = (
                session.query(UserBattleStats, User.username)
                .join(User, UserBattleStats.user_id == User.user_id)
                .order_by(
                    desc(UserBattleStats.wins),
                    UserBattleStats.losses,
                    desc(UserBattleStats.draws),
                )
                .limit(limit)
                .all()
            )
            return [
                {
                    "user_id": stats.user_id,
                    "username": username,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "draws": stats.draws,
                    "win_rate": (
                        stats.wins / (stats.wins + stats.losses + stats.draws)
                        if (stats.wins + stats.losses + stats.draws) > 0
                        else 0
                    ),
                }
                for stats, username in leaderboard
            ]
        finally:
            session.close()

    def get_transactions_for_user(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieves transaction history for a user."""
        session = self.get_session()
        try:
            transactions = (
                session.query(Transaction)
                .filter(
                    (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
                )
                .order_by(desc(Transaction.tx_date))
                .limit(limit)
                .all()
            )

            history = []
            for tx in transactions:
                transaction_type = ""
                if tx.buyer_id == user_id:
                    transaction_type = "purchase"
                elif tx.seller_id == user_id:
                    transaction_type = "sale"

                history.append({
                    "transaction_id": tx.tx_id,
                    "user_id": user_id, # Can be buyer_id or seller_id
                    "type": transaction_type,
                    "amount": tx.price,
                    "currency_type": "USD", # Assuming USD as a default, since no currency_type in model
                    "timestamp": tx.tx_date.isoformat() if tx.tx_date else None,
                    "metadata": None, # No direct metadata in Transaction model
                })
            return history
        except Exception as e:
            session.rollback() # Add rollback for consistency
            logger.error(f"Error retrieving transactions for user {user_id}: {e}")
            return []
        finally:
            session.close()

    def record_transaction(
        self,
        user_id: str,
        transaction_type: str, # This parameter will be ignored for now due to model limitations
        amount: int,
        currency_type: str, # This parameter will be ignored for now due to model limitations
        metadata: Optional[Dict] = None, # This parameter will be ignored for now due to model limitations
    ) -> int: # Changed return type to int for tx_id
        """Records a financial transaction."""
        session = self.get_session()
        try:
            new_transaction = Transaction(
                buyer_id=user_id,
                price=float(amount), # Convert amount to float for price
                tx_date=datetime.utcnow()
                # item_id and seller_id are not directly provided by current parameters
            )
            session.add(new_transaction)
            session.commit()
            return new_transaction.tx_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording transaction for user {user_id}: {e}")
            raise
        finally:
            session.close()

    def get_top_card_collectors(self, limit: int = 10) -> List[Dict]:
        """Retrieves top users based on the total number of unique cards collected."""
        session = self.get_session()
        try:
            top_collectors = (
                session.query(
                    User.user_id,
                    User.username,
                    func.sum(UserCard.quantity).label("total_cards_collected"),
                )
                .join(UserCard, User.user_id == UserCard.user_id)
                .group_by(User.user_id, User.username)
                .order_by(desc("total_cards_collected"))
                .limit(limit)
                .all()
            )

            collectors = []
            for user_id, username, total_cards_collected in top_collectors:
                collectors.append(
                    {
                        "user_id": user_id,
                        "username": username,
                        "total_cards_collected": total_cards_collected,
                    }
                )
            return collectors
        except Exception as e:
            logger.error(f"Error retrieving top card collectors: {e}")
            return []
        finally:
            session.close()

    def get_most_traded_cards(self, limit: int = 10) -> List[Dict]:
        """Retrieves cards that have been traded the most."""
        session = self.get_session()
        try:
            most_traded_cards = (
                session.query(
                    Card.card_id,
                    Card.name,
                    func.count(TradeHistory.trade_id).label("trade_count"),
                )
                .join(CardInstance, Card.card_id == CardInstance.card_id)
                .join(TradeHistory, CardInstance.instance_id == TradeHistory.instance_id)
                .group_by(Card.card_id, Card.name)
                .order_by(desc("trade_count"))
                .limit(limit)
                .all()
            )

            traded_cards = []
            for card_id, card_name, trade_count in most_traded_cards:
                traded_cards.append(
                    {"card_id": card_id, "card_name": card_name, "trade_count": trade_count}
                )
            return traded_cards
        except Exception as e:
            logger.error(f"Error retrieving most traded cards: {e}")
            return []
        finally:
            session.close()

    def check_database_integrity(self) -> Dict:
        """
        Performs a basic integrity check on the database, verifying critical tables exist.
        """
        results = {"valid": True, "tables_checked": 0, "errors": []}
        session = self.get_session()
        try:
            if self._db_type == "postgresql":
                critical_tables = ['users', 'cards', 'creator_packs', 'user_cards', 'transactions', 'pack_purchases', 'dev_pack_supply', 'creator_pack_limits', 'card_instances', 'trade_history', 'user_battle_stats', 'cosmetics_catalog', 'user_cosmetics', 'card_cosmetics', 'battle_log']
                for table_name in critical_tables:
                    results["tables_checked"] += 1
                    # Check if table exists in public schema
                    table_exists = session.query(func.count('*')).filter(
                        text(f"information_schema.tables.table_name = '{table_name}' AND information_schema.tables.table_schema = 'public'")
                    ).scalar() > 0

                    if not table_exists:
                        results["valid"] = False
                        results["errors"].append(f"Critical PostgreSQL table missing: {table_name}")
            elif self._db_type == "sqlite":
                critical_tables = ['users', 'cards', 'creator_packs', 'user_cards', 'transactions', 'pack_purchases', 'dev_pack_supply', 'creator_pack_limits', 'card_instances', 'trade_history', 'user_battle_stats', 'cosmetics_catalog', 'user_cosmetics', 'card_cosmetics', 'battle_log']
                for table_name in critical_tables:
                    results["tables_checked"] += 1
                    # Check if table exists in SQLite master table
                    table_exists = session.query(
                        exists().where(
                            text(f"name='{table_name}'")
                        )
                    ).select_from(text("sqlite_master")).filter(text("type='table'")).scalar()

                    if not table_exists:
                        results["valid"] = False
                        results["errors"].append(f"Critical SQLite table missing: {table_name}")
            else:
                results["valid"] = False
                results["errors"].append("Unsupported database type for integrity check.")
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Database integrity check failed with error: {e}")
            logger.error(f"Database integrity check error: {e}")
        finally:
            session.close()
        return results



    def close(self):
        """Closes the database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._Session = None
            Database._instance = None # Reset the singleton instance

def get_db() -> Database:
    """Returns a singleton instance of the Database class."""
    from config import settings
    return Database(settings.DATABASE_URL)

# Example Usage (for testing or direct script execution)
if __name__ == "__main__":
    # Example for SQLite
    db_sqlite = Database("sqlite:///./test.db")
    session_sqlite = db_sqlite.get_session()
    # Test operations...
    session_sqlite.close()
    db_sqlite.close()

    # Example for PostgreSQL (replace with your actual connection string)
    # db_pg = Database("postgresql://user:password@host:port/dbname")
    # session_pg = db_pg.get_session()
    # Test operations...
    # session_pg.close()
    # db_pg.close()


# Alias for backward compatibility
DatabaseManager = Database
