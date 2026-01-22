# services/rewards.py
import logging
import sqlite3
from datetime import datetime, timedelta
from database import DatabaseManager
from card_economy import CardEconomyManager

class RewardsService:
    def __init__(self):
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
    async def reset_all(self):
        """Reset all daily rewards"""
        logging.info("Resetting all daily rewards")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Reset daily claim status for all users
            cursor.execute("""
                UPDATE user_inventory 
                SET last_daily = NULL
                WHERE last_daily IS NOT NULL
            """)
            
            # Grant daily rewards to active users
            cursor.execute("""
                UPDATE user_inventory 
                SET gold = COALESCECE(gold, 0) + 50,
                    dust = COALESCECE(dust, 0) + 25,
                    tickets = COALESCECE(tickets, 0) + 5
                WHERE user_id IN (
                    SELECT DISTINCT user_id FROM user_cards 
                    WHERE acquisition_date >= date('now', '-7 days')
                )
            """)
            
            conn.commit()
        
        logging.info("Daily rewards reset completed")
        return {'success': True, 'users_reset': 'all'}
    
    async def grant_daily_reward(self, user_id: int):
        """Grant daily reward to specific user"""
        logging.info(f"Granting daily reward to user {user_id}")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if already claimed
            cursor.execute("""
                SELECT last_daily FROM user_inventory WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                last_daily = datetime.fromisoformat(result[0])
                if last_daily.date() >= datetime.now().date():
                    return {'success': False, 'error': 'Already claimed today'}
            
            # Grant reward
            cursor.execute("""
                INSERT OR REPLACE INTO user_inventory 
                (user_id, gold, dust, tickets, last_daily)
                VALUES (?, 
                    COALESCE((SELECT gold FROM user_inventory WHERE user_id = ?), 0) + 50,
                    COALESCE((SELECT dust FROM user_inventory WHERE user_id = ?), 0) + 25,
                    COALESCE((SELECT tickets FROM user_inventory WHERE user_id = ?), 0) + 5,
                    CURRENT_TIMESTAMP
                )
            """, (user_id, user_id, user_id))
            
            conn.commit()
        
        return {'success': True, 'user_id': user_id}
    
    def get_daily_status(self, user_id: int) -> dict:
        """Get daily reward status for user"""
        with sqlite3.connect(self.db.path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_daily FROM user_inventory WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                last_daily = datetime.fromisoformat(result[0])
                today = datetime.now().date()
                
                if last_daily.date() >= today:
                    return {
                        'claimed': True,
                        'last_claimed': last_daily.isoformat(),
                        'next_claim': (last_daily + timedelta(days=1)).date().isoformat()
                    }
                else:
                    return {
                        'claimed': False,
                        'next_claim': today.isoformat()
                    }
            else:
                return {
                    'claimed': False,
                    'next_claim': datetime.now().date().isoformat()
                }

# services/drops.py
import logging
import sqlite3
import random
from datetime import datetime, timedelta
from database import DatabaseManager
from card_economy import CardEconomyManager

class DropsService:
    def __init__(self):
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
    async def activity_spawn(self):
        """Spawn drops based on server activity"""
        logging.info("Checking for activity-based drops")
        
        # Get active servers with recent activity
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get servers with activity in last hour
            cursor.execute("""
                SELECT server_id, COUNT(*) as message_count
                FROM server_activity 
                WHERE timestamp >= datetime('now', '-1 hour')
                GROUP BY server_id
                HAVING message_count >= 10
                ORDER BY message_count DESC
                LIMIT 5
            """)
            
            active_servers = cursor.fetchall()
            
            drops_spawned = 0
            for server_id, message_count in active_servers:
                # Calculate drop chance based on activity
                drop_chance = min(0.8, message_count / 100)  # Max 80% chance
                
                if random.random() < drop_chance:
                    # Spawn a drop in this server
                    await self._spawn_server_drop(server_id)
                    drops_spawned += 1
            
            logging.info(f"Spawned {drops_spawned} activity-based drops")
            return {'success': True, 'drops_spawned': drops_spawned}
    
    async def _spawn_server_drop(self, server_id: int):
        """Spawn a drop in a specific server"""
        # This would integrate with your drop system
        # For now, just log the event
        logging.info(f"Spawning activity drop in server {server_id}")
        
        # In production, this would:
        # 1. Create drop in most active channel
        # 2. Queue drop resolution
        # 3. Notify users
        
        return {'server_id': server_id, 'type': 'activity_drop'}

# services/trades.py
import logging
import sqlite3
from datetime import datetime, timedelta
from database import DatabaseManager

class TradesService:
    def __init__(self):
        self.db = DatabaseManager()
    
    async def expire_old(self):
        """Expire old trades"""
        logging.info("Expiring old trades")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Find trades older than 10 minutes
            expiry_time = datetime.now() - timedelta(minutes=10)
            
            cursor.execute("""
                UPDATE trades 
                SET status = 'expired',
                    expired_at = CURRENT_TIMESTAMP
                WHERE status = 'pending' 
                AND created_at < ?
            """, (expiry_time.isoformat(),))
            
            expired_count = cursor.rowcount
            conn.commit()
        
        logging.info(f"Expired {expired_count} old trades")
        return {'success': True, 'expired_count': expired_count}
    
    async def finalize_trade(self, trade_id: str):
        """Finalize a trade"""
        logging.info(f"Finalizing trade {trade_id}")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get trade details
            cursor.execute("""
                SELECT * FROM trades 
                WHERE trade_id = ? AND status = 'pending'
            """, (trade_id,))
            
            trade_data = cursor.fetchone()
            if not trade_data:
                return {'success': False, 'error': 'Trade not found or not pending'}
            
            # Update trade status
            cursor.execute("""
                UPDATE trades 
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE trade_id = ?
            """, (trade_id,))
            
            conn.commit()
        
        logging.info(f"Trade {trade_id} finalized successfully")
        return {'success': True, 'trade_id': trade_id}

# services/seasons.py
import logging
import sqlite3
from datetime import datetime
from database import DatabaseManager
from card_economy import CardEconomyManager

class SeasonsService:
    def __init__(self):
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
    async def enforce_caps(self):
        """Enforce card printing caps"""
        logging.info("Checking and enforcing card caps")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # This would check season caps and prevent overprinting
            # Implementation depends on your season system
            
            # For now, just log the check
            cursor.execute("""
                SELECT COUNT(*) as total_cards 
                FROM cards 
                WHERE created_at >= date('now', '-1 day')
            """)
            
            result = cursor.fetchone()
            total_cards = result[0] if result else 0
            
            logging.info(f"Current daily card count: {total_cards}")
        
        return {'success': True, 'total_cards': total_cards}
    
    async def check_season_transition(self):
        """Check if season transition is needed"""
        logging.info("Checking for season transition")
        
        # This would check if current season should end
        # Implementation depends on your season system
        
        # For now, just log the check
        current_season = self._get_current_season()
        
        if current_season:
            # Check if season should end (e.g., 30 days passed)
            # Implementation depends on your season logic
            
            logging.info(f"Current season: {current_season}")
        
        return {'success': True, 'current_season': current_season}
    
    def _get_current_season(self) -> str:
        """Get current season name"""
        # This would get the current active season
        # Implementation depends on your season system
        
        # For now, return default
        return "Season 1: Genesis"

# services/data.py
import logging
import sqlite3
from datetime import datetime, timedelta
from database import DatabaseManager

class DataService:
    def __init__(self):
        self.db = DatabaseManager()
    
    async def prune_old_data(self):
        """Prune old data - cleanup task"""
        logging.info("Pruning old data")
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old job execution logs (older than 7 days)
            cutoff_time = datetime.now() - timedelta(days=7)
            
            cursor.execute("""
                DELETE FROM job_logs 
                WHERE executed_at < ?
            """, (cutoff_time.isoformat(),))
            
            # Delete old analytics logs (older than 30 days)
            analytics_cutoff = datetime.now() - timedelta(days=30)
            
            cursor.execute("""
                DELETE FROM analytics_logs 
                WHERE timestamp < ?
            """, (analytics_cutoff.isoformat(),))
            
            # Delete expired drops (older than 1 hour)
            drop_cutoff = datetime.now() - timedelta(hours=1)
            
            cursor.execute("""
                DELETE FROM active_drops 
                WHERE expires_at < ?
            """, (drop_cutoff.isoformat(),))
            
            # Delete expired locks (older than 5 minutes)
            lock_cutoff = datetime.now() - timedelta(minutes=5)
            
            cursor.execute("""
                DELETE FROM locks 
                WHERE created_at < ?
            """, (lock_cutoff.isoformat(),))
            
            deleted_rows = cursor.rowcount
            conn.commit()
        
        logging.info(f"Pruned {deleted_rows} old data records")
        return {'success': True, 'deleted_rows': deleted_rows}

# Service instances
rewards = RewardsService()
drops = DropsService()
trades = TradesService()
seasons = SeasonsService()
data = DataService()
