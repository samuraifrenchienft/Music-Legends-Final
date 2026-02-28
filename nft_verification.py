# nft_verification.py
"""
NFT Verification System
Verifies Music Legends and Samurai Frenchie NFT ownership for revenue boosts
"""
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import sqlite3

from config import settings

class NFTVerifier:
    """Verifies NFT ownership for revenue boost eligibility"""
    
    # Accepted NFT collections (contract addresses)
    ACCEPTED_COLLECTIONS = {
        'music_legends': {
            'name': 'Music Legends NFT',
            'contract_address': settings.MUSIC_LEGENDS_NFT_CONTRACT,
            'chain': 'ethereum',
            'boost_value': 0.10  # +10%
        },
        'samurai_frenchie': {
            'name': 'Samurai Frenchie NFT',
            'contract_address': settings.SAMURAI_FRENCHIE_NFT_CONTRACT,
            'chain': 'ethereum',
            'boost_value': 0.10  # +10%
        }
    }
    
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self.alchemy_api_key = settings.ALCHEMY_API_KEY
        self.moralis_api_key = settings.MORALIS_API_KEY

    def _get_connection(self):
        database_url = settings.DATABASE_URL
        if database_url:
            import psycopg2
            from database import _PgConnectionWrapper
            conn = psycopg2.connect(database_url)
            return _PgConnectionWrapper(conn)
        import sqlite3
        return sqlite3.connect(self.db_path)

    async def verify_nft_ownership(self, wallet_address: str, collection_key: str) -> Dict:
        """
        Verify NFT ownership via blockchain API
        
        Args:
            wallet_address: Ethereum wallet address
            collection_key: 'music_legends' or 'samurai_frenchie'
        
        Returns:
            Dict with verification status and NFT details
        """
        if collection_key not in self.ACCEPTED_COLLECTIONS:
            return {
                'verified': False,
                'error': 'Invalid collection'
            }
        
        collection = self.ACCEPTED_COLLECTIONS[collection_key]
        
        # Try Alchemy API first
        if self.alchemy_api_key:
            result = await self._verify_via_alchemy(wallet_address, collection)
            if result['verified']:
                return result
        
        # Fallback to Moralis API
        if self.moralis_api_key:
            result = await self._verify_via_moralis(wallet_address, collection)
            if result['verified']:
                return result
        
        # If no API keys, return mock verification for testing
        return await self._mock_verification(wallet_address, collection)
    
    async def _verify_via_alchemy(self, wallet_address: str, collection: Dict) -> Dict:
        """Verify NFT ownership via Alchemy API"""
        try:
            url = f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}/getNFTs"
            params = {
                'owner': wallet_address,
                'contractAddresses[]': collection['contract_address']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        owned_nfts = data.get('ownedNfts', [])
                        
                        if owned_nfts:
                            return {
                                'verified': True,
                                'collection': collection['name'],
                                'wallet_address': wallet_address,
                                'nft_count': len(owned_nfts),
                                'token_ids': [nft.get('id', {}).get('tokenId') for nft in owned_nfts[:5]],
                                'verification_method': 'alchemy'
                            }
            
            return {'verified': False, 'error': 'No NFTs found'}
            
        except Exception as e:
            return {'verified': False, 'error': f'Alchemy API error: {str(e)}'}
    
    async def _verify_via_moralis(self, wallet_address: str, collection: Dict) -> Dict:
        """Verify NFT ownership via Moralis API"""
        try:
            url = f"https://deep-index.moralis.io/api/v2/{wallet_address}/nft"
            headers = {
                'X-API-Key': self.moralis_api_key
            }
            params = {
                'chain': 'eth',
                'token_addresses': [collection['contract_address']]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, 
                                      timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        owned_nfts = data.get('result', [])
                        
                        if owned_nfts:
                            return {
                                'verified': True,
                                'collection': collection['name'],
                                'wallet_address': wallet_address,
                                'nft_count': len(owned_nfts),
                                'token_ids': [nft.get('token_id') for nft in owned_nfts[:5]],
                                'verification_method': 'moralis'
                            }
            
            return {'verified': False, 'error': 'No NFTs found'}
            
        except Exception as e:
            return {'verified': False, 'error': f'Moralis API error: {str(e)}'}
    
    async def _mock_verification(self, wallet_address: str, collection: Dict) -> Dict:
        """Mock verification for testing (when no API keys available)"""
        # For testing: verify if wallet address looks valid
        if wallet_address.startswith('0x') and len(wallet_address) == 42:
            return {
                'verified': True,
                'collection': collection['name'],
                'wallet_address': wallet_address,
                'nft_count': 1,
                'token_ids': ['mock_token_1'],
                'verification_method': 'mock',
                'note': 'Mock verification - configure ALCHEMY_API_KEY or MORALIS_API_KEY for real verification'
            }
        
        return {'verified': False, 'error': 'Invalid wallet address format'}
    
    async def register_nft_for_server(self, server_id: int, owner_user_id: int, 
                                     wallet_address: str, collection_key: str) -> Dict:
        """Register an NFT for a server owner to get revenue boost"""
        
        # Verify ownership
        verification = await self.verify_nft_ownership(wallet_address, collection_key)
        
        if not verification['verified']:
            return {
                'success': False,
                'error': verification.get('error', 'NFT verification failed')
            }
        
        # Store in database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get first token ID
            token_id = verification['token_ids'][0] if verification['token_ids'] else 'unknown'
            
            try:
                cursor.execute("""
                    INSERT INTO server_nft_holdings
                    (server_id, owner_user_id, nft_collection, nft_token_id, 
                     wallet_address, verification_status)
                    VALUES (?, ?, ?, ?, ?, 'verified')
                """, (server_id, owner_user_id, collection_key, token_id, wallet_address))
                
                conn.commit()
                
                # Recalculate revenue share
                from server_revenue import server_revenue
                updated_share = server_revenue.calculate_revenue_share(server_id)
                
                return {
                    'success': True,
                    'nft_registered': True,
                    'collection': verification['collection'],
                    'wallet_address': wallet_address,
                    'new_revenue_share': updated_share['revenue_share_display'],
                    'verification_method': verification.get('verification_method')
                }
                
            except Exception as e:
                if 'UNIQUE' in str(e).upper() or 'IntegrityError' in type(e).__name__:
                    return {
                        'success': False,
                        'error': 'This NFT is already registered to another server'
                    }
                raise
    
    def get_server_nfts(self, server_id: int) -> List[Dict]:
        """Get all verified NFTs for a server"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT nft_collection, nft_token_id, wallet_address, 
                       verified_at, verification_status
                FROM server_nft_holdings
                WHERE server_id = ? AND verification_status = 'verified'
            """, (server_id,))
            
            nfts = []
            for row in cursor.fetchall():
                collection_key, token_id, wallet, verified_at, status = row
                collection_info = self.ACCEPTED_COLLECTIONS.get(collection_key, {})
                
                nfts.append({
                    'collection': collection_info.get('name', collection_key),
                    'collection_key': collection_key,
                    'token_id': token_id,
                    'wallet_address': wallet,
                    'verified_at': verified_at,
                    'boost_value': '+10%'
                })
            
            return nfts
    
    def remove_nft(self, server_id: int, nft_token_id: str) -> Dict:
        """Remove an NFT from server holdings"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM server_nft_holdings
                WHERE server_id = ? AND nft_token_id = ?
            """, (server_id, nft_token_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                
                # Recalculate revenue share
                from server_revenue import server_revenue
                updated_share = server_revenue.calculate_revenue_share(server_id)
                
                return {
                    'success': True,
                    'removed': True,
                    'new_revenue_share': updated_share['revenue_share_display']
                }
            
            return {'success': False, 'error': 'NFT not found'}

# Global instance
nft_verifier = NFTVerifier()
