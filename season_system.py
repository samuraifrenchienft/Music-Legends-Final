# season_system.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import DatabaseManager

class SeasonManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.current_season = None
        self.season_duration_days = 30  # 30 days per season
        
    def initialize_season_tables(self):
        """Create season-related database tables"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Seasons table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seasons (
                    season_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season_name TEXT NOT NULL,
                    season_number INTEGER NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    theme TEXT,
                    special_cards TEXT, -- JSON array of special card IDs
                    season_stats TEXT, -- JSON object with season statistics
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Season-specific card caps
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_card_caps (
                    cap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season_id INTEGER,
                    artist_name TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    max_prints INTEGER NOT NULL,
                    current_prints INTEGER DEFAULT 0,
                    is_hard_cap BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
                )
            """)
            
            # Player season progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_season_progress (
                    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    season_id INTEGER NOT NULL,
                    season_level INTEGER DEFAULT 1,
                    season_xp INTEGER DEFAULT 0,
                    cards_collected INTEGER DEFAULT 0,
                    unique_artists INTEGER DEFAULT 0,
                    battles_won INTEGER DEFAULT 0,
                    trades_completed INTEGER DEFAULT 0,
                    season_rank TEXT DEFAULT 'Bronze',
                    rewards_claimed TEXT DEFAULT '[]', -- JSON array of claimed reward IDs
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
                    UNIQUE(user_id, season_id)
                )
            """)
            
            # Season rewards
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_rewards (
                    reward_id TEXT PRIMARY KEY,
                    season_id INTEGER,
                    reward_type TEXT NOT NULL, -- 'card', 'currency', 'title', 'badge'
                    reward_name TEXT NOT NULL,
                    reward_data TEXT, -- JSON object with reward details
                    required_level INTEGER,
                    required_xp INTEGER,
                    required_cards INTEGER,
                    required_rank TEXT,
                    is_claimable BOOLEAN DEFAULT TRUE,
                    is_limited BOOLEAN DEFAULT FALSE,
                    total_claims INTEGER DEFAULT 0,
                    max_claims INTEGER,
                    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
                )
            """)
            
            # Season prestige tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_prestige (
                    prestige_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL,
                    original_season_id INTEGER,
                    seasons_active INTEGER DEFAULT 1, -- How many seasons this card has been active
                    prestige_score INTEGER DEFAULT 0,
                    ownership_history TEXT, -- JSON array of notable owners
                    notable_events TEXT, -- JSON array of notable events
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (original_season_id) REFERENCES seasons(season_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id)
                )
            """)
            
            conn.commit()
    
    def create_new_season(self, season_name: str, theme: str = None) -> Dict:
        """Create a new season"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current season number
            cursor.execute("SELECT MAX(season_number) FROM seasons")
            result = cursor.fetchone()
            next_season_number = (result[0] or 0) + 1
            
            # Calculate season dates
            start_date = datetime.now()
            end_date = start_date + timedelta(days=self.season_duration_days)
            
            # Create season record
            cursor.execute("""
                INSERT INTO seasons 
                (season_name, season_number, start_date, end_date, is_active, theme)
                VALUES (?, ?, ?, ?, TRUE, ?)
            """, (season_name, next_season_number, start_date, end_date, theme))
            
            season_id = cursor.lastrowid
            
            # Deactivate previous seasons
            cursor.execute("UPDATE seasons SET is_active = FALSE WHERE season_id != ?", (season_id,))
            
            # Reset card caps for new season
            self._reset_season_caps(season_id)
            
            # Generate season rewards
            self._generate_season_rewards(season_id)
            
            conn.commit()
            
            return {
                'season_id': season_id,
                'season_name': season_name,
                'season_number': next_season_number,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'theme': theme
            }
    
    def _reset_season_caps(self, new_season_id: int):
        """Reset card printing caps for new season"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get unique artists from existing cards
            cursor.execute("SELECT DISTINCT name FROM cards WHERE type = 'artist' ORDER BY name")
            artists = cursor.fetchall()
            
            # If no artists exist, create some default ones
            if not artists:
                default_artists = [
                    'Artist A', 'Artist B', 'Artist C', 'Artist D', 'Artist E',
                    'Artist F', 'Artist G', 'Artist H', 'Artist I', 'Artist J'
                ]
                artists = [(artist,) for artist in default_artists]
            
            # Set caps for each artist and tier
            tier_caps = {
                'legendary': {'max_prints': 10, 'hard_cap': True},
                'platinum': {'max_prints': 50, 'hard_cap': False},
                'gold': {'max_prints': 200, 'hard_cap': False},
                'community': {'max_prints': 1000, 'hard_cap': False}
            }
            
            for artist in artists:
                artist_name = artist[0]
                for tier, cap_info in tier_caps.items():
                    cursor.execute("""
                        INSERT INTO season_card_caps 
                        (season_id, artist_name, tier, max_prints, is_hard_cap)
                        VALUES (?, ?, ?, ?, ?)
                    """, (new_season_id, artist_name, tier, cap_info['max_prints'], cap_info['hard_cap']))
    
    def _generate_season_rewards(self, season_id: int):
        """Generate rewards for the season"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            rewards = [
                # Level-based rewards
                {'id': f'season_{season_id}_level_5', 'type': 'currency', 'name': 'Season Starter Pack', 'level': 5, 'data': {'gold': 100, 'dust': 50}},
                {'id': f'season_{season_id}_level_10', 'type': 'card', 'name': 'Season Gold Card', 'level': 10, 'data': {'tier': 'gold', 'guaranteed': True}},
                {'id': f'season_{season_id}_level_20', 'type': 'card', 'name': 'Season Platinum Card', 'level': 20, 'data': {'tier': 'platinum', 'guaranteed': True}},
                {'id': f'season_{season_id}_level_30', 'type': 'card', 'name': 'Season Legendary Card', 'level': 30, 'data': {'tier': 'legendary', 'guaranteed': True}},
                
                # XP-based rewards
                {'id': f'season_{season_id}_xp_1000', 'type': 'currency', 'name': 'XP Milestone 1K', 'xp': 1000, 'data': {'gold': 50, 'tickets': 5}},
                {'id': f'season_{season_id}_xp_5000', 'type': 'currency', 'name': 'XP Milestone 5K', 'xp': 5000, 'data': {'gold': 200, 'tickets': 10}},
                {'id': f'season_{season_id}_xp_10000', 'type': 'title', 'name': 'Season Master', 'xp': 10000, 'data': {'title': 'Season Master', 'rarity': 'epic'}},
                
                # Collection-based rewards
                {'id': f'season_{season_id}_cards_100', 'type': 'currency', 'name': 'Collector 100', 'cards': 100, 'data': {'gold': 150, 'dust': 100}},
                {'id': f'season_{season_id}_cards_500', 'type': 'badge', 'name': 'Collector 500', 'cards': 500, 'data': {'badge': 'collector', 'tier': 'gold'}},
                {'id': f'season_{season_id}_cards_1000', 'type': 'badge', 'name': 'Collector 1K', 'cards': 1000, 'data': {'badge': 'collector', 'tier': 'platinum'}},
                
                # Rank-based rewards
                {'id': f'season_{season_id}_rank_silver', 'type': 'currency', 'name': 'Silver Rank', 'rank': 'Silver', 'data': {'gold': 300, 'gems': 5}},
                {'id': f'season_{season_id}_rank_gold', 'type': 'currency', 'name': 'Gold Rank', 'rank': 'Gold', 'data': {'gold': 500, 'gems': 10}},
                {'id': f'season_{season_id}_rank_platinum', 'type': 'card', 'name': 'Platinum Rank Reward', 'rank': 'Platinum', 'data': {'tier': 'platinum', 'guaranteed': True}},
                {'id': f'season_{season_id}_rank_diamond', 'type': 'card', 'name': 'Diamond Rank Reward', 'rank': 'Diamond', 'data': {'tier': 'legendary', 'guaranteed': True}},
            ]
            
            for reward in rewards:
                cursor.execute("""
                    INSERT INTO season_rewards 
                    (reward_id, season_id, reward_type, reward_name, reward_data, 
                     required_level, required_xp, required_cards, required_rank)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reward['id'], season_id, reward['type'], reward['name'], 
                    json.dumps(reward['data']), reward.get('level'), reward.get('xp'), 
                    reward.get('cards'), reward.get('rank')
                ))
    
    def get_current_season(self) -> Optional[Dict]:
        """Get the currently active season"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM seasons 
                WHERE is_active = TRUE 
                ORDER BY season_number DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            else:
                return None
    
    def get_player_season_progress(self, user_id: int) -> Dict:
        """Get player's progress in current season"""
        current_season = self.get_current_season()
        if not current_season:
            return {'error': 'No active season'}
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM player_season_progress 
                WHERE user_id = ? AND season_id = ?
            """, (user_id, current_season['season_id']))
            
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            else:
                # Create new progress record
                cursor.execute("""
                    INSERT INTO player_season_progress 
                    (user_id, season_id, season_level, season_xp, cards_collected, unique_artists)
                    VALUES (?, ?, 1, 0, 0, 0)
                """, (user_id, current_season['season_id']))
                
                cursor.execute("""
                    SELECT * FROM player_season_progress 
                    WHERE user_id = ? AND season_id = ?
                """, (user_id, current_season['season_id']))
                
                result = cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
    
    def update_player_progress(self, user_id: int, action_type: str, amount: int = 1, extra_data: Dict = None):
        """Update player's season progress based on actions"""
        current_season = self.get_current_season()
        if not current_season:
            return
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current progress
            progress = self.get_player_season_progress(user_id)
            
            # Update based on action type
            if action_type == 'card_collected':
                cursor.execute("""
                    UPDATE player_season_progress 
                    SET cards_collected = cards_collected + ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND season_id = ?
                """, (amount, user_id, current_season['season_id']))
                
                # Add XP for collecting cards
                xp_gained = amount * 10
                self._add_season_xp(user_id, current_season['season_id'], xp_gained)
                
            elif action_type == 'battle_won':
                cursor.execute("""
                    UPDATE player_season_progress 
                    SET battles_won = battles_won + ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND season_id = ?
                """, (amount, user_id, current_season['season_id']))
                
                # Add XP for winning battles
                xp_gained = amount * 25
                self._add_season_xp(user_id, current_season['season_id'], xp_gained)
                
            elif action_type == 'trade_completed':
                cursor.execute("""
                    UPDATE player_season_progress 
                    SET trades_completed = trades_completed + ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND season_id = ?
                """, (amount, user_id, current_season['season_id']))
                
                # Add XP for trading
                xp_gained = amount * 15
                self._add_season_xp(user_id, current_season['season_id'], xp_gained)
                
            elif action_type == 'unique_artist':
                # Update unique artist count
                cursor.execute("""
                    UPDATE player_season_progress 
                    SET unique_artists = unique_artists + 1, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND season_id = ?
                """, (user_id, current_season['season_id']))
                
                # Bonus XP for unique artists
                self._add_season_xp(user_id, current_season['season_id'], 50)
            
            # Update season rank based on XP
            self._update_season_rank(user_id, current_season['season_id'])
            
            conn.commit()
    
    def _add_season_xp(self, user_id: int, season_id: int, xp_amount: int):
        """Add XP to player and check for level ups"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current XP and level
            cursor.execute("""
                SELECT season_xp, season_level FROM player_season_progress 
                WHERE user_id = ? AND season_id = ?
            """, (user_id, season_id))
            
            result = cursor.fetchone()
            if not result:
                return
            
            current_xp, current_level = result
            
            # Add XP
            new_xp = current_xp + xp_amount
            
            # Check for level ups (100 XP per level)
            new_level = current_level + (new_xp // 100)
            new_xp = new_xp % 100
            
            cursor.execute("""
                UPDATE player_season_progress 
                SET season_xp = ?, season_level = ?
                WHERE user_id = ? AND season_id = ?
            """, (new_xp, new_level, user_id, season_id))
    
    def _update_season_rank(self, user_id: int, season_id: int):
        """Update player's season rank based on XP and level"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT season_level, season_xp FROM player_season_progress 
                WHERE user_id = ? AND season_id = ?
            """, (user_id, season_id))
            
            result = cursor.fetchone()
            if not result:
                return
            
            level, xp = result
            total_xp = (level * 100) + xp
            
            # Determine rank based on XP
            if total_xp >= 10000:
                rank = 'Diamond'
            elif total_xp >= 5000:
                rank = 'Platinum'
            elif total_xp >= 2000:
                rank = 'Gold'
            elif total_xp >= 500:
                rank = 'Silver'
            else:
                rank = 'Bronze'
            
            cursor.execute("""
                UPDATE player_season_progress 
                SET season_rank = ?
                WHERE user_id = ? AND season_id = ?
            """, (rank, user_id, season_id))
    
    def check_card_cap(self, artist_name: str, tier: str) -> Dict:
        """Check if a card can still be printed this season"""
        current_season = self.get_current_season()
        if not current_season:
            return {'can_print': True, 'remaining': 999}
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT max_prints, current_prints, is_hard_cap 
                FROM season_card_caps 
                WHERE season_id = ? AND artist_name = ? AND tier = ?
            """, (current_season['season_id'], artist_name, tier))
            
            result = cursor.fetchone()
            if not result:
                return {'can_print': True, 'remaining': 999}
            
            max_prints, current_prints, is_hard_cap = result
            remaining = max_prints - current_prints
            
            return {
                'can_print': remaining > 0,
                'remaining': remaining,
                'is_hard_cap': is_hard_cap,
                'max_prints': max_prints,
                'current_prints': current_prints
            }
    
    def increment_card_print(self, artist_name: str, tier: str):
        """Increment the print count for a card"""
        current_season = self.get_current_season()
        if not current_season:
            return
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE season_card_caps 
                SET current_prints = current_prints + 1
                WHERE season_id = ? AND artist_name = ? AND tier = ?
            """, (current_season['season_id'], artist_name, tier))
            
            conn.commit()
    
    def get_available_rewards(self, user_id: int) -> List[Dict]:
        """Get rewards available for a player"""
        current_season = self.get_current_season()
        if not current_season:
            return []
        
        progress = self.get_player_season_progress(user_id)
        claimed_rewards = json.loads(progress['claimed_rewards']) if progress['claimed_rewards'] else []
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM season_rewards 
                WHERE season_id = ? AND is_claimable = TRUE
                ORDER BY required_level, required_xp, required_cards
            """, (current_season['season_id'],))
            
            all_rewards = cursor.fetchall()
            available_rewards = []
            
            for reward in all_rewards:
                reward_id = reward[0]
                
                if reward_id in claimed_rewards:
                    continue
                
                # Check if player meets requirements
                can_claim = True
                
                if reward[5] and progress['season_level'] < reward[5]:  # required_level
                    can_claim = False
                elif reward[6] and (progress['season_level'] * 100 + progress['season_xp']) < reward[6]:  # required_xp
                    can_claim = False
                elif reward[7] and progress['cards_collected'] < reward[7]:  # required_cards
                    can_claim = False
                elif reward[8] and progress['season_rank'] != reward[8]:  # required_rank
                    can_claim = False
                
                if can_claim:
                    columns = [desc[0] for desc in cursor.description]
                    reward_dict = dict(zip(columns, reward))
                    reward_dict['can_claim'] = True
                    available_rewards.append(reward_dict)
            
            return available_rewards
    
    def claim_reward(self, user_id: int, reward_id: str) -> Dict:
        """Claim a season reward"""
        current_season = self.get_current_season()
        if not current_season:
            return {'success': False, 'error': 'No active season'}
        
        progress = self.get_player_season_progress(user_id)
        claimed_rewards = json.loads(progress['claimed_rewards']) if progress['claimed_rewards'] else []
        
        if reward_id in claimed_rewards:
            return {'success': False, 'error': 'Reward already claimed'}
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get reward details
            cursor.execute("""
                SELECT * FROM season_rewards 
                WHERE reward_id = ? AND season_id = ?
            """, (reward_id, current_season['season_id']))
            
            reward = cursor.fetchone()
            if not reward:
                return {'success': False, 'error': 'Reward not found'}
            
            # Check if player meets requirements
            can_claim = True
            
            if reward[5] and progress['season_level'] < reward[5]:  # required_level
                can_claim = False
            elif reward[6] and (progress['season_level'] * 100 + progress['season_xp']) < reward[6]:  # required_xp
                can_claim = False
            elif reward[7] and progress['cards_collected'] < reward[7]:  # required_cards
                can_claim = False
            elif reward[8] and progress['season_rank'] != reward[8]:  # required_rank
                can_claim = False
            
            if not can_claim:
                return {'success': False, 'error': 'Requirements not met'}
            
            # Add to claimed rewards
            claimed_rewards.append(reward_id)
            cursor.execute("""
                UPDATE player_season_progress 
                SET claimed_rewards = ?
                WHERE user_id = ? AND season_id = ?
            """, (json.dumps(claimed_rewards), user_id, current_season['season_id']))
            
            # Update total claims if limited
            if reward[10]:  # is_limited
                cursor.execute("""
                    UPDATE season_rewards 
                    SET total_claims = total_claims + 1
                    WHERE reward_id = ?
                """, (reward_id,))
            
            conn.commit()
            
            # Return reward data for processing
            reward_data = json.loads(reward[4]) if reward[4] else {}
            
            return {
                'success': True,
                'reward_type': reward[2],
                'reward_name': reward[3],
                'reward_data': reward_data
            }
    
    def get_season_leaderboard(self, limit: int = 50) -> List[Dict]:
        """Get the season leaderboard"""
        current_season = self.get_current_season()
        if not current_season:
            return []
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, u.username, u.discord_tag 
                FROM player_season_progress p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.season_id = ?
                ORDER BY (p.season_level * 100 + p.season_xp) DESC, p.cards_collected DESC
                LIMIT ?
            """, (current_season['season_id'], limit))
            
            results = cursor.fetchall()
            leaderboard = []
            
            for i, row in enumerate(results, 1):
                # Get user info from the row
                user_data = {
                    'rank': i,
                    'user_id': row[1],
                    'season_level': row[2],
                    'season_xp': row[3],
                    'cards_collected': row[4],
                    'unique_artists': row[5],
                    'battles_won': row[6],
                    'trades_completed': row[7],
                    'season_rank': row[8],
                    'username': row[10],
                    'discord_tag': row[11]
                }
                leaderboard.append(user_data)
            
            return leaderboard
    
    def end_season(self, season_id: int) -> Dict:
        """End a season and calculate final rewards"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Mark season as inactive
            cursor.execute("""
                UPDATE seasons 
                SET is_active = FALSE 
                WHERE season_id = ?
            """, (season_id,))
            
            # Get top players for special rewards
            cursor.execute("""
                SELECT user_id, season_level, season_xp 
                FROM player_season_progress 
                WHERE season_id = ?
                ORDER BY (season_level * 100 + season_xp) DESC
                LIMIT 10
            """, (season_id,))
            
            top_players = cursor.fetchall()
            
            # Award prestige to old cards
            self._award_season_prestige(season_id)
            
            # Generate season summary
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_players,
                    AVG(season_level) as avg_level,
                    AVG(season_xp) as avg_xp,
                    SUM(cards_collected) as total_cards,
                    SUM(battles_won) as total_battles,
                    SUM(trades_completed) as total_trades
                FROM player_season_progress 
                WHERE season_id = ?
            """, (season_id,))
            
            stats = cursor.fetchone()
            
            conn.commit()
            
            return {
                'season_id': season_id,
                'top_players': top_players,
                'stats': {
                    'total_players': stats[0],
                    'avg_level': stats[1],
                    'avg_xp': stats[2],
                    'total_cards': stats[3],
                    'total_battles': stats[4],
                    'total_trades': stats[5]
                }
            }
    
    def _award_season_prestige(self, season_id: int):
        """Award prestige points to cards from the season"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all cards from the season
            cursor.execute("""
                SELECT card_id, owner_user_id, tier 
                FROM cards 
                WHERE acquisition_date >= (
                    SELECT start_date FROM seasons WHERE season_id = ?
                ) AND acquisition_date <= (
                    SELECT end_date FROM seasons WHERE season_id = ?
                )
            """, (season_id, season_id))
            
            season_cards = cursor.fetchall()
            
            for card in season_cards:
                card_id, owner_id, tier = card
                
                # Calculate prestige based on tier and owner achievements
                base_prestige = {'community': 1, 'gold': 5, 'platinum': 15, 'legendary': 50}[tier]
                
                cursor.execute("""
                    INSERT OR REPLACE INTO card_prestige 
                    (card_id, original_season_id, prestige_score)
                    VALUES (?, ?, COALESCE(
                        (SELECT prestige_score FROM card_prestige WHERE card_id = ?), 0
                    ) + ?)
                """, (card_id, season_id, card_id, base_prestige))
            
            conn.commit()

# Global season manager instance
season_manager = None
