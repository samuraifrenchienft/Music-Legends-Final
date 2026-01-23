# nft_entitlement.py
"""
NFT Entitlement System - Snapshot-Based Revenue Boost
NFTs are ENTITLEMENT TOKENS ONLY - no gameplay impact
"""
import sqlite3
import secrets
import hashlib
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import aiohttp
import os
from eth_account.messages import encode_defunct
from eth_account import Account

class NFTEntitlementManager:
    """
    Manages NFT-based revenue entitlements via snapshot verification
    NO real-time blockchain calls during purchases
    """
    
    # Accepted NFT collections
    ACCEPTED_COLLECTIONS = {
        'music_legends': {
            'name': 'Music Legends NFT',
            'contract_address': os.getenv('MUSIC_LEGENDS_NFT_CONTRACT', '0x0000000000000000000000000000000000000000'),
            'chain': 'ethereum'
        },
        'samurai_frenchie': {
            'name': 'Samurai Frenchie NFT',
            'contract_address': os.getenv('SAMURAI_FRENCHIE_NFT_CONTRACT', '0x0000000000000000000000000000000000000000'),
            'chain': 'ethereum'
        }
    }
    
    # Entitlement rules
    BASE_REVENUE_SHARE = 0.10  # 10%
    NFT_BOOST = 0.10           # +10% per NFT
    MAX_NFTS_COUNTED = 2       # Max 2 NFTs
    MAX_REVENUE_SHARE = 0.30   # 30% cap
    
    # Snapshot cadence
    SNAPSHOT_INTERVAL_HOURS = 24
    VERIFICATION_STALE_DAYS = 7
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY')
        self.init_entitlement_tables()
    
    def init_entitlement_tables(self):
        """Initialize entitlement tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Wallet linking (one-time)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_links (
                    discord_user_id INTEGER PRIMARY KEY,
                    wallet_address TEXT NOT NULL UNIQUE,
                    signature TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # NFT snapshot cache (updated every 24h)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nft_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id INTEGER NOT NULL,
                    wallet_address TEXT NOT NULL,
                    collection_key TEXT NOT NULL,
                    nft_count INTEGER DEFAULT 0,
                    snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verification_method TEXT,
                    FOREIGN KEY (discord_user_id) REFERENCES wallet_links(discord_user_id)
                )
            """)
            
            # Cached entitlement records (used during purchases)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entitlement_cache (
                    discord_user_id INTEGER PRIMARY KEY,
                    wallet_address TEXT NOT NULL,
                    eligible_nfts INTEGER DEFAULT 0,
                    revenue_share_percent REAL DEFAULT 0.10,
                    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verification_status TEXT DEFAULT 'active',
                    freeze_reason TEXT,
                    FOREIGN KEY (discord_user_id) REFERENCES wallet_links(discord_user_id)
                )
            """)
            
            # Snapshot refresh log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshot_refresh_log (
                    refresh_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    refresh_type TEXT NOT NULL,
                    discord_user_id INTEGER,
                    success BOOLEAN,
                    nfts_found INTEGER,
                    error_message TEXT,
                    refresh_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def generate_nonce(self) -> str:
        """Generate a unique nonce for wallet signature"""
        return secrets.token_hex(32)
    
    def create_signature_message(self, discord_user_id: int, nonce: str) -> str:
        """Create message for wallet signature"""
        return f"Music Legends - Link Wallet\n\nDiscord ID: {discord_user_id}\nNonce: {nonce}\n\nThis signature proves wallet ownership."
    
    def verify_wallet_signature(self, wallet_address: str, signature: str, message: str) -> bool:
        """Verify wallet signature"""
        try:
            # Encode message
            message_hash = encode_defunct(text=message)
            
            # Recover address from signature
            recovered_address = Account.recover_message(message_hash, signature=signature)
            
            # Compare addresses (case-insensitive)
            return recovered_address.lower() == wallet_address.lower()
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False
    
    def link_wallet(self, discord_user_id: int, wallet_address: str, signature: str, nonce: str) -> Dict:
        """Link wallet to Discord account with signature verification"""
        
        # Create expected message
        message = self.create_signature_message(discord_user_id, nonce)
        
        # Verify signature
        if not self.verify_wallet_signature(wallet_address, signature, message):
            return {
                'success': False,
                'error': 'Invalid signature - wallet ownership could not be verified'
            }
        
        # Store wallet link
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO wallet_links
                    (discord_user_id, wallet_address, signature, nonce, verified_at, status)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'active')
                """, (discord_user_id, wallet_address.lower(), signature, nonce))
                
                # Initialize entitlement cache with base 10%
                cursor.execute("""
                    INSERT OR REPLACE INTO entitlement_cache
                    (discord_user_id, wallet_address, eligible_nfts, revenue_share_percent, last_verified)
                    VALUES (?, ?, 0, ?, CURRENT_TIMESTAMP)
                """, (discord_user_id, wallet_address.lower(), self.BASE_REVENUE_SHARE))
                
                conn.commit()
                
                return {
                    'success': True,
                    'wallet_address': wallet_address.lower(),
                    'message': 'Wallet linked successfully - NFT snapshot will run within 24 hours'
                }
                
            except sqlite3.IntegrityError:
                return {
                    'success': False,
                    'error': 'This wallet is already linked to another Discord account'
                }
    
    async def snapshot_nft_ownership(self, discord_user_id: int) -> Dict:
        """
        Take snapshot of NFT ownership (runs every 24h or on-demand)
        NO CALLS DURING PURCHASES - this is cached
        """
        
        # Get wallet address
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT wallet_address FROM wallet_links
                WHERE discord_user_id = ? AND status = 'active'
            """, (discord_user_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': 'No wallet linked'}
            
            wallet_address = result[0]
        
        # Query blockchain for NFT ownership
        total_nfts = 0
        snapshots = []
        
        for collection_key, collection_info in self.ACCEPTED_COLLECTIONS.items():
            nft_count = await self._query_nft_balance(wallet_address, collection_info['contract_address'])
            
            if nft_count > 0:
                snapshots.append({
                    'collection_key': collection_key,
                    'nft_count': nft_count
                })
                total_nfts += nft_count
        
        # Store snapshots
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear old snapshots for this user
            cursor.execute("""
                DELETE FROM nft_snapshots
                WHERE discord_user_id = ?
            """, (discord_user_id,))
            
            # Store new snapshots
            for snapshot in snapshots:
                cursor.execute("""
                    INSERT INTO nft_snapshots
                    (discord_user_id, wallet_address, collection_key, nft_count, verification_method)
                    VALUES (?, ?, ?, ?, 'alchemy')
                """, (discord_user_id, wallet_address, snapshot['collection_key'], snapshot['nft_count']))
            
            # Calculate entitlement
            eligible_nfts = min(total_nfts, self.MAX_NFTS_COUNTED)
            revenue_share = self.BASE_REVENUE_SHARE + (eligible_nfts * self.NFT_BOOST)
            revenue_share = min(revenue_share, self.MAX_REVENUE_SHARE)
            
            # Update entitlement cache
            cursor.execute("""
                UPDATE entitlement_cache
                SET eligible_nfts = ?,
                    revenue_share_percent = ?,
                    last_verified = CURRENT_TIMESTAMP,
                    verification_status = 'active'
                WHERE discord_user_id = ?
            """, (eligible_nfts, revenue_share, discord_user_id))
            
            # Log refresh
            cursor.execute("""
                INSERT INTO snapshot_refresh_log
                (refresh_type, discord_user_id, success, nfts_found)
                VALUES ('manual', ?, 1, ?)
            """, (discord_user_id, total_nfts))
            
            conn.commit()
        
        return {
            'success': True,
            'total_nfts': total_nfts,
            'eligible_nfts': eligible_nfts,
            'revenue_share_percent': revenue_share,
            'snapshots': snapshots
        }
    
    async def _query_nft_balance(self, wallet_address: str, contract_address: str) -> int:
        """Query NFT balance via Alchemy (read-only, no transactions)"""
        
        if not self.alchemy_api_key:
            # Mock for testing
            return 0
        
        try:
            url = f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}/getNFTs"
            params = {
                'owner': wallet_address,
                'contractAddresses[]': contract_address
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return len(data.get('ownedNfts', []))
            
            return 0
            
        except Exception as e:
            print(f"NFT balance query error: {e}")
            return 0
    
    def get_cached_entitlement(self, discord_user_id: int) -> Dict:
        """
        Get cached entitlement for purchase-time use
        CRITICAL: NO BLOCKCHAIN CALLS HERE
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT wallet_address, eligible_nfts, revenue_share_percent,
                       last_verified, verification_status, freeze_reason
                FROM entitlement_cache
                WHERE discord_user_id = ?
            """, (discord_user_id,))
            
            result = cursor.fetchone()
            
            if not result:
                # No wallet linked - default to 10%
                return {
                    'has_entitlement': False,
                    'revenue_share_percent': self.BASE_REVENUE_SHARE,
                    'eligible_nfts': 0
                }
            
            wallet, eligible_nfts, revenue_share, last_verified, status, freeze_reason = result
            
            # Check if frozen
            if status == 'frozen':
                return {
                    'has_entitlement': True,
                    'frozen': True,
                    'freeze_reason': freeze_reason,
                    'revenue_share_percent': self.BASE_REVENUE_SHARE,  # Revert to base
                    'eligible_nfts': 0
                }
            
            # Check if stale (older than 7 days)
            last_verified_dt = datetime.fromisoformat(last_verified)
            if datetime.now() - last_verified_dt > timedelta(days=self.VERIFICATION_STALE_DAYS):
                # Stale but don't block - use cached value
                return {
                    'has_entitlement': True,
                    'stale': True,
                    'revenue_share_percent': revenue_share,
                    'eligible_nfts': eligible_nfts,
                    'last_verified': last_verified
                }
            
            return {
                'has_entitlement': True,
                'revenue_share_percent': revenue_share,
                'eligible_nfts': eligible_nfts,
                'last_verified': last_verified
            }
    
    def needs_snapshot_refresh(self, discord_user_id: int) -> bool:
        """Check if snapshot needs refresh (24h interval)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT last_verified FROM entitlement_cache
                WHERE discord_user_id = ?
            """, (discord_user_id,))
            
            result = cursor.fetchone()
            if not result:
                return True
            
            last_verified = datetime.fromisoformat(result[0])
            hours_since = (datetime.now() - last_verified).total_seconds() / 3600
            
            return hours_since >= self.SNAPSHOT_INTERVAL_HOURS

# Global instance
nft_entitlement = NFTEntitlementManager()
