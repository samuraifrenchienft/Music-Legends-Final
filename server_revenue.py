# server_revenue.py
"""
Server-Based Revenue Sharing System
10% base + NFT boosts (max 30%)
"""
from .config import settings
import sqlite3
from typing import Dict, Optional
from datetime import datetime

class ServerRevenueManager:
    """Manages server-based revenue sharing"""

    # Revenue share rates
    BASE_SHARE = 0.10  # 10% base
    NFT_BOOST = 0.10   # +10% per NFT
    MAX_SHARE = 0.30   # 30% cap
    MAX_NFTS = 2       # Max 2 NFTs counted

    # Payout thresholds
    MIN_PAYOUT_CENTS = 2500  # $25.00 minimum weekly payout
    PAYOUT_FREQUENCY_DAYS = 7  # Weekly payouts

    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self._database_url = settings.DATABASE_URL
        self.init_revenue_tables()

    def _get_connection(self):
        """Get database connection - PostgreSQL if DATABASE_URL set, else SQLite."""
        if self._database_url:
            import psycopg2
            from database import _PgConnectionWrapper
            url = self._database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return _PgConnectionWrapper(psycopg2.connect(url))
        else:
            return sqlite3.connect(self.db_path)
    
    def init_revenue_tables(self):
        """Initialize revenue tracking tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Server owner registration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_owners (
                    server_id INTEGER PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL,
                    owner_discord_tag TEXT,
                    stripe_connect_account_id TEXT,
                    stripe_connect_status TEXT DEFAULT 'not_connected',
                    nft_count INTEGER DEFAULT 0,
                    revenue_share_percentage REAL DEFAULT 0.10,
                    total_earned_cents INTEGER DEFAULT 0,
                    pending_payout_cents INTEGER DEFAULT 0,
                    last_payout_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # NFT holdings for server owners
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_nft_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    nft_collection TEXT NOT NULL,
                    nft_token_id TEXT NOT NULL,
                    wallet_address TEXT NOT NULL,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verification_status TEXT DEFAULT 'verified',
                    FOREIGN KEY (server_id) REFERENCES server_owners(server_id),
                    UNIQUE(nft_collection, nft_token_id)
                )
            """)
            
            # Revenue transactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_revenue_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    server_id INTEGER NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    purchase_type TEXT NOT NULL,
                    total_amount_cents INTEGER NOT NULL,
                    server_share_cents INTEGER NOT NULL,
                    platform_share_cents INTEGER NOT NULL,
                    revenue_share_percentage REAL NOT NULL,
                    nft_boost_applied INTEGER DEFAULT 0,
                    stripe_payment_intent_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payout_status TEXT DEFAULT 'pending',
                    payout_date TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES server_owners(server_id)
                )
            """)
            
            # Payout history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_payouts (
                    payout_id TEXT PRIMARY KEY,
                    server_id INTEGER NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    stripe_transfer_id TEXT,
                    payout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed',
                    transaction_ids TEXT,
                    FOREIGN KEY (server_id) REFERENCES server_owners(server_id)
                )
            """)
            
            conn.commit()
    
    def register_server_owner(self, server_id: int, owner_user_id: int, owner_discord_tag: str) -> Dict:
        """Register a server owner for revenue sharing"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO server_owners 
                (server_id, owner_user_id, owner_discord_tag, revenue_share_percentage, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (server_id, owner_user_id, owner_discord_tag, self.BASE_SHARE))
            
            conn.commit()
            
            return {
                'success': True,
                'server_id': server_id,
                'base_share': self.BASE_SHARE,
                'message': 'Server registered for 10% revenue share'
            }
    
    def calculate_revenue_share(self, server_id: int) -> Dict:
        """Calculate revenue share percentage based on NFT holdings"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get NFT count
            cursor.execute("""
                SELECT COUNT(*) FROM server_nft_holdings
                WHERE server_id = ? AND verification_status = 'verified'
            """, (server_id,))
            
            nft_count = cursor.fetchone()[0]
            
            # Cap at MAX_NFTS
            counted_nfts = min(nft_count, self.MAX_NFTS)
            
            # Calculate share: base + (NFT_BOOST * counted_nfts)
            revenue_share = self.BASE_SHARE + (self.NFT_BOOST * counted_nfts)
            revenue_share = min(revenue_share, self.MAX_SHARE)  # Cap at 30%
            
            # Update server owner record
            cursor.execute("""
                UPDATE server_owners
                SET nft_count = ?, revenue_share_percentage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE server_id = ?
            """, (nft_count, revenue_share, server_id))
            
            conn.commit()
            
            return {
                'server_id': server_id,
                'nft_count': nft_count,
                'counted_nfts': counted_nfts,
                'revenue_share_percentage': revenue_share,
                'revenue_share_display': f"{revenue_share * 100:.0f}%"
            }
    
    def record_purchase_revenue(self, server_id: int, purchase_type: str, 
                               total_amount_cents: int, payment_intent_id: str) -> Dict:
        """Record revenue from a purchase and calculate splits"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get server owner info
            cursor.execute("""
                SELECT owner_user_id, revenue_share_percentage, nft_count
                FROM server_owners
                WHERE server_id = ?
            """, (server_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': 'Server not registered'}
            
            owner_user_id, revenue_share, nft_count = result
            
            # Calculate splits
            server_share_cents = int(total_amount_cents * revenue_share)
            platform_share_cents = total_amount_cents - server_share_cents
            
            # Generate transaction ID
            transaction_id = f"rev_{server_id}_{int(datetime.now().timestamp())}"
            
            # Record transaction
            cursor.execute("""
                INSERT INTO server_revenue_transactions
                (transaction_id, server_id, owner_user_id, purchase_type, 
                 total_amount_cents, server_share_cents, platform_share_cents,
                 revenue_share_percentage, nft_boost_applied, stripe_payment_intent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (transaction_id, server_id, owner_user_id, purchase_type,
                  total_amount_cents, server_share_cents, platform_share_cents,
                  revenue_share, nft_count, payment_intent_id))
            
            # Update server owner totals
            cursor.execute("""
                UPDATE server_owners
                SET total_earned_cents = total_earned_cents + ?,
                    pending_payout_cents = pending_payout_cents + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE server_id = ?
            """, (server_share_cents, server_share_cents, server_id))
            
            conn.commit()
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'total_amount': total_amount_cents / 100,
                'server_share': server_share_cents / 100,
                'platform_share': platform_share_cents / 100,
                'revenue_share_percentage': revenue_share
            }
    
    def get_server_revenue_status(self, server_id: int) -> Optional[Dict]:
        """Get revenue status for a server"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT owner_user_id, owner_discord_tag, stripe_connect_status,
                       nft_count, revenue_share_percentage, total_earned_cents,
                       pending_payout_cents, last_payout_date
                FROM server_owners
                WHERE server_id = ?
            """, (server_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            (owner_user_id, owner_discord_tag, stripe_status, nft_count, 
             revenue_share, total_earned, pending_payout, last_payout) = result
            
            # Get transaction count
            cursor.execute("""
                SELECT COUNT(*) FROM server_revenue_transactions
                WHERE server_id = ?
            """, (server_id,))
            
            transaction_count = cursor.fetchone()[0]
            
            # Check if eligible for payout
            eligible_for_payout = pending_payout >= self.MIN_PAYOUT_CENTS
            
            return {
                'server_id': server_id,
                'owner_user_id': owner_user_id,
                'owner_discord_tag': owner_discord_tag,
                'stripe_connected': stripe_status == 'connected',
                'nft_count': nft_count,
                'revenue_share_percentage': revenue_share,
                'revenue_share_display': f"{revenue_share * 100:.0f}%",
                'total_earned': total_earned / 100,
                'pending_payout': pending_payout / 100,
                'total_transactions': transaction_count,
                'last_payout_date': last_payout,
                'eligible_for_payout': eligible_for_payout,
                'min_payout_threshold': self.MIN_PAYOUT_CENTS / 100
            }
    
    def get_servers_ready_for_payout(self) -> list:
        """Get all servers with pending payout >= $25"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT server_id, owner_user_id, pending_payout_cents
                FROM server_owners
                WHERE pending_payout_cents >= ?
                AND stripe_connect_status = 'connected'
            """, (self.MIN_PAYOUT_CENTS,))
            
            return [
                {
                    'server_id': row[0],
                    'owner_user_id': row[1],
                    'pending_payout': row[2] / 100
                }
                for row in cursor.fetchall()
            ]

# Global instance
server_revenue = ServerRevenueManager()
