# drop_system.py
import asyncio
import time
import sqlite3
from typing import Dict, Optional, List
from dataclasses import dataclass
from scheduler import scheduler
from action_queue import action_queue, Task
from card_economy import CardEconomyManager
from database import DatabaseManager

@dataclass
class DropConfig:
    DROP_COOLDOWN: int = 1800  # 30 minutes in seconds
    CLAIM_WINDOW: int = 1000    # 1 second in milliseconds
    MAX_RETRIES: int = 3
    QUEUE_POLL: int = 50        # 50ms poll interval

class DropTimer:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config = DropConfig()
        
    def can_drop(self, server_id: int) -> bool:
        """Check if server can drop based on cooldown"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_drop_time, activity_level FROM server_drop_cooldowns 
                WHERE server_id = ?
            """, (server_id,))
            result = cursor.fetchone()
            
            if not result:
                return True  # First drop
            
            last_drop, activity_level = result
            if not last_drop:
                return True
            
            # Cooldown based on activity level (1-5)
            cooldown_minutes = max(1, 30 - (activity_level * 6))  # 30 min to 1 min
            cooldown_time = time.time() - (cooldown_minutes * 60)
            
            return float(last_drop) < cooldown_time
    
    def update_cooldown(self, server_id: int):
        """Update server cooldown after drop"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO server_drop_cooldowns 
                (server_id, last_drop_time, drop_count_today, last_activity_update)
                VALUES (?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT drop_count_today FROM server_drop_cooldowns WHERE server_id = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            """, (server_id, server_id))
            conn.commit()

class DropSystem:
    def __init__(self, bot, db_manager: DatabaseManager, economy_manager: CardEconomyManager):
        self.bot = bot
        self.db = db_manager
        self.economy = economy_manager
        self.timer = DropTimer(db_manager)
        self.active_drops: Dict[int, Dict] = {}  # channel_id -> drop_data
        self.config = DropConfig()
        
        # Start scheduler
        scheduler.start()
    
    async def create_drop(self, channel_id: int, server_id: int, initiator_id: int, drop_type: str = 'standard') -> Dict:
        """Create a new drop with queue protection"""
        # Check cooldown first
        if not self.timer.can_drop(server_id):
            return {'success': False, 'error': 'Drop on cooldown'}
        
        # Use queue to prevent concurrent drops in same channel
        task_key = f"drop_channel_{channel_id}"
        
        async def create_drop_task():
            # Generate cards
            cards = []
            if drop_type == 'standard':
                for _ in range(3):
                    artists = self.db.get_all_artists(limit=100)
                    if artists:
                        artist = artists[0]  # Use first artist for simplicity
                        card = self.economy.create_card(artist, acquisition_source='drop')
                        if card:
                            cards.append(card)
            
            if not cards:
                return {'success': False, 'error': 'Failed to generate cards'}
            
            # Create drop record
            import uuid
            drop_id = str(uuid.uuid4())
            expires_at = time.time() + (self.config.CLAIM_WINDOW / 1000)
            
            # Store drop data
            drop_data = {
                'drop_id': drop_id,
                'channel_id': channel_id,
                'server_id': server_id,
                'initiator_id': initiator_id,
                'cards': cards,
                'drop_type': drop_type,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            self.active_drops[channel_id] = drop_data
            
            # Update cooldown
            self.timer.update_cooldown(server_id)
            
            # Schedule expiration
            scheduler.schedule('expireDrop', {
                'channel_id': channel_id,
                'drop_id': drop_id
            }, self.config.CLAIM_WINDOW)
            
            return {
                'success': True,
                'drop_id': drop_id,
                'cards': cards,
                'expires_at': expires_at
            }
        
        # Run with queue protection
        try:
            task = Task(key=task_key, action=create_drop_task)
            return await action_queue.run(task)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def wait_for_reactions(self, channel_id: int, drop_id: str) -> Optional[Dict]:
        """Wait for reactions within claim window"""
        if channel_id not in self.active_drops:
            return None
        
        drop_data = self.active_drops[channel_id]
        if drop_data['drop_id'] != drop_id:
            return None
        
        # Wait for claim window
        remaining_time = drop_data['expires_at'] - time.time()
        if remaining_time > 0:
            await asyncio.sleep(min(remaining_time, self.config.CLAIM_WINDOW / 1000))
        
        # Check if drop was claimed
        if channel_id in self.active_drops:
            return self.active_drops[channel_id]
        else:
            return None  # Expired or claimed
    
    async def resolve_drop(self, channel_id: int, user_id: int, reaction_number: int) -> Dict:
        """Resolve a drop claim"""
        if channel_id not in self.active_drops:
            return {'success': False, 'error': 'No active drop'}
        
        drop_data = self.active_drops[channel_id]
        
        # Check if expired
        if time.time() > drop_data['expires_at']:
            del self.active_drops[channel_id]
            return {'success': False, 'error': 'Drop expired'}
        
        # Check if valid reaction number
        if reaction_number < 1 or reaction_number > len(drop_data['cards']):
            return {'success': False, 'error': 'Invalid card number'}
        
        # Get the card
        card = drop_data['cards'][reaction_number - 1]
        
        # Queue the award operation
        task_key = f"award_{user_id}_{card['card_id']}"
        
        async def award_task():
            # Award card to user
            self.economy._award_card_to_user(user_id, card)
            
            # Remove from active drops
            if channel_id in self.active_drops:
                del self.active_drops[channel_id]
            
            return {
                'success': True,
                'card': card,
                'drop_id': drop_data['drop_id']
            }
        
        try:
            task = Task(key=task_key, action=award_task)
            result = await action_queue.run(task)
            
            # Schedule cooldown reset
            scheduler.schedule('resetCooldown', {
                'server_id': drop_data['server_id'],
                'channel_id': channel_id
            }, self.config.DROP_COOLDOWN * 1000)  # Convert to milliseconds
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def expire_drop(self, channel_id: int, drop_id: str):
        """Handle drop expiration"""
        if channel_id in self.active_drops:
            drop_data = self.active_drops[channel_id]
            if drop_data['drop_id'] == drop_id:
                del self.active_drops[channel_id]
                print(f"Drop {drop_id} expired in channel {channel_id}")
    
    def get_active_drops(self) -> List[Dict]:
        """Get all active drops"""
        return list(self.active_drops.values())
    
    def get_drop_status(self, channel_id: int) -> Optional[Dict]:
        """Get status of a specific drop"""
        if channel_id not in self.active_drops:
            return None
        
        drop = self.active_drops[channel_id]
        remaining_time = max(0, drop['expires_at'] - time.time())
        
        return {
            'drop_id': drop['drop_id'],
            'expires_in': remaining_time,
            'card_count': len(drop['cards']),
            'initiator_id': drop['initiator_id']
        }

# Import sqlite3 for database operations
import sqlite3

# Global drop system instance
drop_system = None

def initialize_drop_system(bot, db_manager, economy_manager):
    """Initialize the drop system"""
    global drop_system
    drop_system = DropSystem(bot, db_manager, economy_manager)
    return drop_system
