"""
Missing Battle Classes
PlayerState, MatchState, BattleCard, and wager configuration
"""

from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
from discord_cards import ArtistCard

# ============================================
# BATTLE WAGER CONFIGURATION
# ============================================

class BattleWagerConfig:
    """
    Battle wager configuration
    Defines costs and rewards for each tier
    """
    
    TIERS = {
        "casual": {
            "name": "Casual",
            "wager_cost": 50,
            "winner_gold": 100,      # Total gold winner gets
            "loser_gold": 10,        # Consolation gold
            "winner_xp": 25,
            "loser_xp": 5,
            "emoji": "🎮",
        },
        "standard": {
            "name": "Standard",
            "wager_cost": 100,
            "winner_gold": 175,
            "loser_gold": 10,
            "winner_xp": 40,
            "loser_xp": 8,
            "emoji": "⚔️",
        },
        "high": {
            "name": "High Stakes",
            "wager_cost": 250,
            "winner_gold": 350,
            "loser_gold": 15,
            "winner_xp": 60,
            "loser_xp": 12,
            "emoji": "🔥",
        },
        "extreme": {
            "name": "Extreme",
            "wager_cost": 500,
            "winner_gold": 650,
            "loser_gold": 20,
            "winner_xp": 100,
            "loser_xp": 20,
            "emoji": "💀",
        },
    }
    
    @classmethod
    def get_tier(cls, tier_name: str) -> Dict:
        """Get wager tier configuration"""
        return cls.TIERS.get(tier_name.lower(), cls.TIERS["casual"])
    
    @classmethod
    def get_wager_cost(cls, tier_name: str) -> int:
        """Get wager cost for tier"""
        tier = cls.get_tier(tier_name)
        return tier["wager_cost"]
    
    @classmethod
    def get_winner_reward(cls, tier_name: str) -> Dict:
        """Get winner rewards"""
        tier = cls.get_tier(tier_name)
        return {
            "gold": tier["winner_gold"],
            "xp": tier["winner_xp"],
        }
    
    @classmethod
    def get_loser_reward(cls, tier_name: str) -> Dict:
        """Get loser consolation rewards"""
        tier = cls.get_tier(tier_name)
        return {
            "gold": tier["loser_gold"],
            "xp": tier["loser_xp"],
        }


# ============================================
# BATTLE CARD (Wrapper for ArtistCard in battles)
# ============================================

class BattleCard:
    """
    Battle-specific card wrapper
    Adds battle state to ArtistCard
    """
    
    def __init__(
        self,
        artist_card: ArtistCard,
        owner_id: str,
        owner_name: str
    ):
        self.card = artist_card
        self.owner_id = owner_id
        self.owner_name = owner_name
        
        # Battle stats
        self.base_power = artist_card.power
        self.final_power = artist_card.power
        self.critical_hit = False
        self.power_modifier = 1.0
    
    def apply_critical_hit(self, multiplier: float = 1.5):
        """Apply critical hit bonus"""
        self.critical_hit = True
        self.final_power = int(self.base_power * multiplier)
    
    def apply_power_modifier(self, modifier: float):
        """Apply power modifier (buffs/debuffs)"""
        self.power_modifier = modifier
        self.final_power = int(self.base_power * modifier)
    
    def reset(self):
        """Reset to base stats"""
        self.final_power = self.base_power
        self.critical_hit = False
        self.power_modifier = 1.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "card": self.card.to_dict(),
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "base_power": self.base_power,
            "final_power": self.final_power,
            "critical_hit": self.critical_hit,
            "power_modifier": self.power_modifier,
        }
    
    @classmethod
    def from_artist_card(
        cls,
        artist_card: ArtistCard,
        owner_id: str,
        owner_name: str
    ) -> 'BattleCard':
        """Create BattleCard from ArtistCard"""
        return cls(artist_card, owner_id, owner_name)
    
    def __repr__(self):
        crit_tag = " [CRIT]" if self.critical_hit else ""
        return f"<BattleCard: {self.card.artist} - {self.card.song} ({self.final_power} PWR{crit_tag})>"


# ============================================
# PLAYER STATE (Battle participant state)
# ============================================

class PlayerState:
    """
    Represents a player's state in a battle
    """
    
    def __init__(
        self,
        user_id: str,
        username: str,
        card: Optional[BattleCard] = None
    ):
        self.user_id = user_id
        self.username = username
        self.card = card
        
        # Battle state
        self.is_ready = False
        self.has_accepted = False
        self.gold_wagered = 0
        
        # Results
        self.gold_reward = 0
        self.xp_reward = 0
        self.won = False
    
    def set_card(self, card: BattleCard):
        """Set player's battle card"""
        self.card = card
        self.is_ready = True
    
    def accept_battle(self, wager_amount: int):
        """Accept battle invitation"""
        self.has_accepted = True
        self.gold_wagered = wager_amount
    
    def set_rewards(self, gold: int, xp: int, won: bool):
        """Set battle rewards"""
        self.gold_reward = gold
        self.xp_reward = xp
        self.won = won
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "card": self.card.to_dict() if self.card else None,
            "is_ready": self.is_ready,
            "has_accepted": self.has_accepted,
            "gold_wagered": self.gold_wagered,
            "gold_reward": self.gold_reward,
            "xp_reward": self.xp_reward,
            "won": self.won,
        }
    
    def __repr__(self):
        ready_tag = "✓" if self.is_ready else "✗"
        return f"<PlayerState: {self.username} [{ready_tag}]>"


# ============================================
# MATCH STATE (Overall battle state)
# ============================================

class BattleStatus(Enum):
    """Battle status enum"""
    PENDING = "pending"           # Waiting for acceptance
    SELECTING = "selecting"       # Players selecting cards
    IN_PROGRESS = "in_progress"   # Battle executing
    COMPLETED = "completed"       # Battle finished
    CANCELLED = "cancelled"       # Battle cancelled
    EXPIRED = "expired"           # Battle timed out


class MatchState:
    """
    Represents the complete state of a battle match
    """
    
    def __init__(
        self,
        match_id: str,
        player1: PlayerState,
        player2: PlayerState,
        wager_tier: str = "casual"
    ):
        self.match_id = match_id
        self.player1 = player1
        self.player2 = player2
        self.wager_tier = wager_tier
        
        # Match state
        self.status = BattleStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Battle results
        self.winner_id: Optional[str] = None
        self.is_tie = False
        self.power_difference = 0
        
        # Get wager config
        self.wager_config = BattleWagerConfig.get_tier(wager_tier)
    
    def accept_battle(self, user_id: str) -> bool:
        """
        Player accepts battle
        Returns True if both players have accepted
        """
        if user_id == self.player1.user_id:
            self.player1.accept_battle(self.wager_config["wager_cost"])
        elif user_id == self.player2.user_id:
            self.player2.accept_battle(self.wager_config["wager_cost"])
        else:
            return False
        
        # Check if both accepted
        if self.player1.has_accepted and self.player2.has_accepted:
            self.status = BattleStatus.SELECTING
            return True
        
        return False
    
    def set_player_card(self, user_id: str, card: BattleCard) -> bool:
        """
        Set player's card
        Returns True if both players are ready
        """
        if user_id == self.player1.user_id:
            self.player1.set_card(card)
        elif user_id == self.player2.user_id:
            self.player2.set_card(card)
        else:
            return False
        
        # Check if both ready
        if self.player1.is_ready and self.player2.is_ready:
            self.status = BattleStatus.IN_PROGRESS
            self.started_at = datetime.now()
            return True
        
        return False
    
    def complete_battle(
        self,
        winner_id: Optional[str],
        is_tie: bool,
        power_diff: int
    ):
        """Mark battle as completed"""
        self.status = BattleStatus.COMPLETED
        self.completed_at = datetime.now()
        self.winner_id = winner_id
        self.is_tie = is_tie
        self.power_difference = power_diff
        
        # Set rewards
        if is_tie:
            # Tie - both get small rewards
            tie_gold = 25
            tie_xp = 10
            self.player1.set_rewards(tie_gold, tie_xp, False)
            self.player2.set_rewards(tie_gold, tie_xp, False)
        
        elif winner_id == self.player1.user_id:
            # Player 1 wins
            winner_rewards = BattleWagerConfig.get_winner_reward(self.wager_tier)
            loser_rewards = BattleWagerConfig.get_loser_reward(self.wager_tier)
            
            self.player1.set_rewards(
                winner_rewards["gold"],
                winner_rewards["xp"],
                True
            )
            self.player2.set_rewards(
                loser_rewards["gold"],
                loser_rewards["xp"],
                False
            )
        
        else:
            # Player 2 wins
            winner_rewards = BattleWagerConfig.get_winner_reward(self.wager_tier)
            loser_rewards = BattleWagerConfig.get_loser_reward(self.wager_tier)
            
            self.player2.set_rewards(
                winner_rewards["gold"],
                winner_rewards["xp"],
                True
            )
            self.player1.set_rewards(
                loser_rewards["gold"],
                loser_rewards["xp"],
                False
            )
    
    def cancel(self):
        """Cancel battle — refund wagers to both players"""
        self.status = BattleStatus.CANCELLED
        # Refund wagers
        self.player1.gold_reward = self.player1.gold_wagered
        self.player2.gold_reward = self.player2.gold_wagered

    def expire(self):
        """Mark battle as expired — refund wagers to both players"""
        self.status = BattleStatus.EXPIRED
        # Refund wagers
        self.player1.gold_reward = self.player1.gold_wagered
        self.player2.gold_reward = self.player2.gold_wagered
    
    def get_winner(self) -> Optional[PlayerState]:
        """Get winning player"""
        if self.winner_id == self.player1.user_id:
            return self.player1
        elif self.winner_id == self.player2.user_id:
            return self.player2
        return None
    
    def get_loser(self) -> Optional[PlayerState]:
        """Get losing player"""
        if self.winner_id == self.player1.user_id:
            return self.player2
        elif self.winner_id == self.player2.user_id:
            return self.player1
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "match_id": self.match_id,
            "player1": self.player1.to_dict(),
            "player2": self.player2.to_dict(),
            "wager_tier": self.wager_tier,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "winner_id": self.winner_id,
            "is_tie": self.is_tie,
            "power_difference": self.power_difference,
        }
    
    def __repr__(self):
        return f"<MatchState: {self.player1.username} vs {self.player2.username} ({self.status.value})>"


# ============================================
# BATTLE MANAGER (Helper class)
# ============================================

class BattleManager:
    """
    Helper class to manage active battles
    """
    
    def __init__(self):
        self.active_matches: Dict[str, MatchState] = {}
        self.user_to_match: Dict[str, str] = {}  # user_id -> match_id
    
    def create_match(
        self,
        match_id: str,
        player1_id: str,
        player1_name: str,
        player2_id: str,
        player2_name: str,
        wager_tier: str = "casual"
    ) -> MatchState:
        """Create a new battle match"""
        
        player1 = PlayerState(player1_id, player1_name)
        player2 = PlayerState(player2_id, player2_name)
        
        match = MatchState(match_id, player1, player2, wager_tier)
        
        # Store match
        self.active_matches[match_id] = match
        self.user_to_match[player1_id] = match_id
        self.user_to_match[player2_id] = match_id
        
        return match
    
    def get_match(self, match_id: str) -> Optional[MatchState]:
        """Get match by ID"""
        return self.active_matches.get(match_id)
    
    def get_user_match(self, user_id: str) -> Optional[MatchState]:
        """Get user's current match"""
        match_id = self.user_to_match.get(user_id)
        if match_id:
            return self.active_matches.get(match_id)
        return None
    
    def is_user_in_battle(self, user_id: str) -> bool:
        """Check if user is in a battle"""
        return user_id in self.user_to_match
    
    def complete_match(self, match_id: str):
        """Clean up completed match"""
        match = self.active_matches.get(match_id)
        if match:
            # Remove user mappings
            if match.player1.user_id in self.user_to_match:
                del self.user_to_match[match.player1.user_id]
            if match.player2.user_id in self.user_to_match:
                del self.user_to_match[match.player2.user_id]
            
            # Remove match
            del self.active_matches[match_id]
    
    def get_active_count(self) -> int:
        """Get count of active matches"""
        return len(self.active_matches)


# ============================================
# LEGACY BATTLE ENGINE (Keep for compatibility)
# ============================================

import random
import discord

class BattleEngine:
    """
    Legacy BattleEngine class for backward compatibility
    """
    
    # Battle settings
    CRITICAL_HIT_CHANCE = 0.15  # 15% chance for critical hit
    CRITICAL_MULTIPLIER = 1.5   # Critical hit = +50% power
    MIN_POWER_ADVANTAGE = 5     # Minimum power diff to matter
    
    @classmethod
    def execute_battle(
        cls,
        card1: ArtistCard,
        card2: ArtistCard,
        wager_tier: str = "casual",
        p1_override: int = None,
        p2_override: int = None,
    ) -> Dict:
        """Execute a battle between two cards (legacy method)"""

        # Use override power if provided (direct stat calculation bypasses lossy view_count)
        base1 = p1_override if p1_override is not None else card1.power
        base2 = p2_override if p2_override is not None else card2.power
        power1 = base1
        power2 = base2

        # Check for critical hits
        crit1 = random.random() < cls.CRITICAL_HIT_CHANCE
        crit2 = random.random() < cls.CRITICAL_HIT_CHANCE

        # Apply critical hit multipliers
        if crit1:
            power1 = int(power1 * cls.CRITICAL_MULTIPLIER)
        if crit2:
            power2 = int(power2 * cls.CRITICAL_MULTIPLIER)

        # Determine winner
        power_diff = abs(power1 - power2)

        if power_diff < cls.MIN_POWER_ADVANTAGE:
            winner = 0  # Tie
        elif power1 > power2:
            winner = 1
        else:
            winner = 2

        # Get wager info
        wager_info = BattleWagerConfig.get_tier(wager_tier)

        # Calculate rewards
        if winner == 1:
            player1_gold = wager_info["winner_gold"]
            player2_gold = wager_info["loser_gold"]
            player1_xp = wager_info["winner_xp"]
            player2_xp = wager_info["loser_xp"]
        elif winner == 2:
            player1_gold = wager_info["loser_gold"]
            player2_gold = wager_info["winner_gold"]
            player1_xp = wager_info["loser_xp"]
            player2_xp = wager_info["winner_xp"]
        else:
            # Tie - both get small rewards
            player1_gold = 25
            player2_gold = 25
            player1_xp = 10
            player2_xp = 10

        return {
            "winner": winner,
            "player1": {
                "card": card1,
                "base_power": base1,
                "final_power": power1,
                "critical_hit": crit1,
                "gold_reward": player1_gold,
                "xp_reward": player1_xp,
            },
            "player2": {
                "card": card2,
                "base_power": base2,
                "final_power": power2,
                "critical_hit": crit2,
                "gold_reward": player2_gold,
                "xp_reward": player2_xp,
            },
            "power_difference": power_diff,
            "wager": wager_info["wager_cost"],
            "wager_tier": wager_tier,
        }
    
    @classmethod
    def create_battle_embed(
        cls,
        result: Dict,
        player1_name: str,
        player2_name: str
    ) -> discord.Embed:
        """
        Create Discord embed showing battle results
        
        Args:
            result: Battle result from execute_battle()
            player1_name: Display name for player 1
            player2_name: Display name for player 2
        
        Returns:
            discord.Embed with battle results
        """
        
        p1 = result["player1"]
        p2 = result["player2"]
        
        # Determine embed color based on winner
        if result["winner"] == 1:
            color = 0x2ecc71  # Green (player 1 wins)
        elif result["winner"] == 2:
            color = 0xe74c3c  # Red (player 2 wins)
        else:
            color = 0xf39c12  # Yellow (tie)
        
        embed = discord.Embed(
            title="⚔️ BATTLE RESULTS ⚔️",
            color=color
        )
        
        # Player 1
        p1_text = f"**{player1_name}**\n"
        p1_text += f"{p1['card'].get_rarity_emoji()} {p1['card'].artist} - {p1['card'].song}\n"
        p1_text += f"**Power:** {p1['base_power']} → {p1['final_power']}"
        if p1['critical_hit']:
            p1_text += " 💥 **CRIT!**"
        
        embed.add_field(
            name="🔵 Player 1",
            value=p1_text,
            inline=True
        )
        
        # VS
        embed.add_field(
            name="⚡",
            value="**VS**",
            inline=True
        )
        
        # Player 2
        p2_text = f"**{player2_name}**\n"
        p2_text += f"{p2['card'].get_rarity_emoji()} {p2['card'].artist} - {p2['card'].song}\n"
        p2_text += f"**Power:** {p2['base_power']} → {p2['final_power']}"
        if p2['critical_hit']:
            p2_text += " 💥 **CRIT!**"
        
        embed.add_field(
            name="🔴 Player 2",
            value=p2_text,
            inline=True
        )
        
        # Result
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value="\u200b",  # Invisible separator
            inline=False
        )
        
        if result["winner"] == 0:
            result_text = "🤝 **TIE!**\n"
            result_text += f"Power difference too small ({result['power_difference']})\n"
            result_text += "Both players get consolation rewards"
        elif result["winner"] == 1:
            result_text = f"🏆 **{player1_name.upper()} WINS!**\n"
            result_text += f"Victory by +{result['power_difference']} power!"
        else:
            result_text = f"🏆 **{player2_name.upper()} WINS!**\n"
            result_text += f"Victory by +{result['power_difference']} power!"
        
        embed.add_field(
            name="🎯 Result",
            value=result_text,
            inline=False
        )
        
        # Rewards
        rewards_text = ""
        
        if result["winner"] == 1:
            rewards_text += f"**{player1_name}:** +{p1['gold_reward']} gold, +{p1['xp_reward']} XP\n"
            rewards_text += f"**{player2_name}:** +{p2['gold_reward']} gold, +{p2['xp_reward']} XP"
        elif result["winner"] == 2:
            rewards_text += f"**{player1_name}:** +{p1['gold_reward']} gold, +{p1['xp_reward']} XP\n"
            rewards_text += f"**{player2_name}:** +{p2['gold_reward']} gold, +{p2['xp_reward']} XP"
        else:
            rewards_text += f"**Both:** +{p1['gold_reward']} gold, +{p1['xp_reward']} XP\n"
            rewards_text += f"Wagers returned"
        
        embed.add_field(
            name="💰 Rewards",
            value=rewards_text,
            inline=False
        )
        
        # Footer
        embed.set_footer(
            text=f"Wager: {result['wager']} gold ({result['wager_tier']})"
        )
        
        return embed


class BattleHistory:
    """Track battle history for a user"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.battles = []
        self.wins = 0
        self.losses = 0
        self.ties = 0
    
    def add_battle(self, result: Dict, was_player1: bool):
        """Add battle to history"""
        self.battles.append({
            "result": result,
            "was_player1": was_player1,
            "timestamp": discord.utils.utcnow(),
        })
        
        # Update stats
        if result["winner"] == 0:
            self.ties += 1
        elif (result["winner"] == 1 and was_player1) or (result["winner"] == 2 and not was_player1):
            self.wins += 1
        else:
            self.losses += 1
    
    def win_rate(self) -> float:
        """Calculate win rate"""
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return self.wins / total
    
    def total_battles(self) -> int:
        """Get total battle count"""
        return len(self.battles)
    
    def get_stats_embed(self, username: str) -> discord.Embed:
        """Create embed showing battle stats"""
        embed = discord.Embed(
            title=f"⚔️ Battle Stats - {username}",
            color=0x3498db
        )
        
        embed.add_field(
            name="📊 Record",
            value=f"**Wins:** {self.wins}\n**Losses:** {self.losses}\n**Ties:** {self.ties}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Win Rate",
            value=f"**{self.win_rate() * 100:.1f}%**",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Total Battles",
            value=f"**{self.total_battles()}**",
            inline=True
        )
        
        return embed


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Create battle manager
    manager = BattleManager()
    
    # Create match
    match = manager.create_match(
        match_id="battle_123",
        player1_id="user1",
        player1_name="Player1",
        player2_id="user2",
        player2_name="Player2",
        wager_tier="high"
    )
    
    print(f"Created: {match}")
    print(f"Wager cost: {match.wager_config['wager_cost']} gold")
    print(f"Status: {match.status.value}")
    
    # Player 2 accepts
    both_accepted = match.accept_battle("user2")
    print(f"Player 2 accepted. Both ready: {both_accepted}")
    
    # Player 1 accepts
    both_accepted = match.accept_battle("user1")
    print(f"Player 1 accepted. Both ready: {both_accepted}")
    print(f"Status: {match.status.value}")
    
    # Create battle cards
    drake = ArtistCard(
        card_id="1",
        artist="Drake",
        song="Hotline Bling",
        youtube_url="https://youtube.com/watch?v=test",
        youtube_id="test",
        view_count=1_200_000_000,
        thumbnail="",
        rarity="legendary"
    )
    
    taylor = ArtistCard(
        card_id="2",
        artist="Taylor Swift",
        song="Shake It Off",
        youtube_url="https://youtube.com/watch?v=test2",
        youtube_id="test2",
        view_count=800_000_000,
        thumbnail="",
        rarity="epic"
    )
    
    # Wrap in BattleCards
    battle_card1 = BattleCard.from_artist_card(drake, "user1", "Player1")
    battle_card2 = BattleCard.from_artist_card(taylor, "user2", "Player2")
    
    # Set cards
    match.set_player_card("user1", battle_card1)
    both_ready = match.set_player_card("user2", battle_card2)
    print(f"\nBoth players ready: {both_ready}")
    print(f"Status: {match.status.value}")
    
    # Complete battle
    match.complete_battle(
        winner_id="user1",
        is_tie=False,
        power_diff=20
    )
    
    print(f"\nBattle completed!")
    print(f"Winner: {match.get_winner().username}")
    print(f"Winner rewards: {match.get_winner().gold_reward}g, {match.get_winner().xp_reward}xp")
    print(f"Loser rewards: {match.get_loser().gold_reward}g, {match.get_loser().xp_reward}xp")
