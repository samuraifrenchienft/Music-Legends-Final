"""
card_economy.py - Economy management for Music Legends
Handles gold, tickets, daily claims, rewards
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import discord

class PlayerEconomy:
    """
    Manages a player's economy (gold, tickets, daily claims)
    """
    
    def __init__(
        self,
        user_id: str,
        gold: int = 500,  # Starting gold
        tickets: int = 0,
        last_daily_claim: Optional[datetime] = None,
        daily_streak: int = 0
    ):
        self.user_id = user_id
        self.gold = gold
        self.tickets = tickets
        self.last_daily_claim = last_daily_claim
        self.daily_streak = daily_streak
    
    def add_gold(self, amount: int):
        """Add gold to player"""
        self.gold += amount
    
    def remove_gold(self, amount: int) -> bool:
        """
        Remove gold from player
        Returns True if successful, False if insufficient gold
        """
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False
    
    def add_tickets(self, amount: int):
        """Add tickets to player"""
        self.tickets += amount
    
    def remove_tickets(self, amount: int) -> bool:
        """
        Remove tickets from player
        Returns True if successful, False if insufficient tickets
        """
        if self.tickets >= amount:
            self.tickets -= amount
            return True
        return False
    
    def can_claim_daily(self) -> bool:
        """Check if player can claim daily reward"""
        if self.last_daily_claim is None:
            return True
        
        time_since_claim = datetime.now() - self.last_daily_claim
        return time_since_claim >= timedelta(hours=20)  # 20 hour cooldown (allows timezone flexibility)
    
    def claim_daily(self) -> Dict:
        """
        Claim daily reward
        
        Returns:
            Dictionary with gold, tickets, and streak info
        """
        if not self.can_claim_daily():
            # Calculate time until next claim
            time_since = datetime.now() - self.last_daily_claim
            time_until = timedelta(hours=24) - time_since
            return {
                "success": False,
                "error": "Already claimed today",
                "time_until_next": time_until,
            }
        
        # Check if streak continues
        if self.last_daily_claim:
            time_since_claim = datetime.now() - self.last_daily_claim
            if time_since_claim <= timedelta(hours=48):  # 48 hour grace period
                self.daily_streak += 1
            else:
                self.daily_streak = 1  # Streak broken
        else:
            self.daily_streak = 1
        
        # Calculate rewards
        base_gold = 100
        bonus_gold = 0
        tickets = 0
        
        # Streak bonuses
        streak_bonuses = {
            3: {"gold": 50, "tickets": 0},
            7: {"gold": 200, "tickets": 1},
            14: {"gold": 500, "tickets": 2},
            30: {"gold": 1000, "tickets": 5},
        }
        
        if self.daily_streak in streak_bonuses:
            bonus = streak_bonuses[self.daily_streak]
            bonus_gold = bonus["gold"]
            tickets = bonus["tickets"]
        
        total_gold = base_gold + bonus_gold
        
        # Add rewards
        self.add_gold(total_gold)
        self.add_tickets(tickets)
        
        # Update claim time
        self.last_daily_claim = datetime.now()
        
        return {
            "success": True,
            "gold": total_gold,
            "base_gold": base_gold,
            "bonus_gold": bonus_gold,
            "tickets": tickets,
            "streak": self.daily_streak,
            "streak_bonus": self.daily_streak in streak_bonuses,
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "gold": self.gold,
            "tickets": self.tickets,
            "last_daily_claim": self.last_daily_claim.isoformat() if self.last_daily_claim else None,
            "daily_streak": self.daily_streak,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerEconomy':
        """Create from dictionary"""
        last_claim = None
        if data.get("last_daily_claim"):
            last_claim = datetime.fromisoformat(data["last_daily_claim"])
        
        return cls(
            user_id=data["user_id"],
            gold=data.get("gold", 500),
            tickets=data.get("tickets", 0),
            last_daily_claim=last_claim,
            daily_streak=data.get("daily_streak", 0),
        )


class PackPricing:
    """Pack prices and creation costs"""
    
    # Pack prices (buying from marketplace)
    COMMUNITY_PACK_GOLD = 500
    COMMUNITY_PACK_USD = 2.99
    
    GOLD_PACK_USD = 4.99
    GOLD_PACK_TICKETS = 100
    
    # Pack creation costs
    GOLD_PACK_CREATE_USD = 6.99
    GOLD_PACK_CREATE_TICKETS = 150
    
    @classmethod
    def can_afford_pack(cls, economy: PlayerEconomy, pack_type: str, currency: str = "gold") -> bool:
        """
        Check if player can afford a pack
        
        Args:
            economy: PlayerEconomy instance
            pack_type: "community" or "gold"
            currency: "gold", "tickets", or "usd"
        
        Returns:
            True if can afford, False otherwise
        """
        if pack_type == "community":
            if currency == "gold":
                return economy.gold >= cls.COMMUNITY_PACK_GOLD
            elif currency == "usd":
                return True  # Handled by payment processor
        
        elif pack_type == "gold":
            if currency == "tickets":
                return economy.tickets >= cls.GOLD_PACK_TICKETS
            elif currency == "usd":
                return True  # Handled by payment processor
        
        return False
    
    @classmethod
    def purchase_pack(
        cls,
        economy: PlayerEconomy,
        pack_type: str,
        currency: str = "gold"
    ) -> bool:
        """
        Purchase a pack (deduct currency)
        
        Returns:
            True if successful, False if insufficient funds
        """
        if pack_type == "community":
            if currency == "gold":
                return economy.remove_gold(cls.COMMUNITY_PACK_GOLD)
        
        elif pack_type == "gold":
            if currency == "tickets":
                return economy.remove_tickets(cls.GOLD_PACK_TICKETS)
        
        return False


class CardSelling:
    """Card selling/trading economy"""
    
    # Sell values by rarity
    SELL_VALUES = {
        "common": 10,
        "rare": 25,
        "epic": 75,
        "legendary": 200,
        "mythic": 500,
        "ultra_mythic": 1000,
    }
    
    # Marketplace fees
    MARKETPLACE_FEE = 0.10  # 10% fee
    MARKETPLACE_FEE_VIP = 0.00  # 0% for VIP
    
    # Trading fees
    TRADE_FEE = 50  # 50 gold per trade
    TRADE_FEE_VIP = 0  # Free for VIP
    
    @classmethod
    def calculate_sell_value(cls, rarity: str, is_duplicate: bool = False) -> int:
        """
        Calculate gold value when selling a card
        
        Args:
            rarity: Card rarity
            is_duplicate: Whether player already has this card
        
        Returns:
            Gold value
        """
        base_value = cls.SELL_VALUES.get(rarity.lower(), 10)
        
        # Duplicate bonus (+50%)
        if is_duplicate:
            base_value = int(base_value * 1.5)
        
        return base_value
    
    @classmethod
    def calculate_marketplace_fee(cls, price: int, is_vip: bool = False) -> int:
        """Calculate marketplace listing fee"""
        if is_vip:
            return 0
        return int(price * cls.MARKETPLACE_FEE)


class DailyQuests:
    """Daily quest system for extra rewards"""
    
    QUESTS = [
        {
            "id": "win_3_battles",
            "name": "Battle Victor",
            "description": "Win 3 battles",
            "requirement": 3,
            "reward": {"gold": 150, "xp": 50},
        },
        {
            "id": "open_pack",
            "name": "Pack Opener",
            "description": "Open a pack",
            "requirement": 1,
            "reward": {"gold": 75, "xp": 25},
        },
        {
            "id": "collect_daily",
            "name": "Daily Grind",
            "description": "Claim daily reward",
            "requirement": 1,
            "reward": {"gold": 50, "xp": 10},
        },
        {
            "id": "trade_card",
            "name": "Trader",
            "description": "Trade or sell a card",
            "requirement": 1,
            "reward": {"gold": 100, "xp": 20},
        },
        {
            "id": "battle_streak",
            "name": "Win Streak",
            "description": "Win 5 battles in a row",
            "requirement": 5,
            "reward": {"gold": 300, "xp": 100},
        },
    ]


class EconomyDisplay:
    """Helper class for creating economy-related Discord embeds"""
    
    @staticmethod
    def create_balance_embed(economy: PlayerEconomy, username: str) -> discord.Embed:
        """Create embed showing player's balance"""
        embed = discord.Embed(
            title=f"💰 {username}'s Balance",
            color=0xf39c12
        )
        
        embed.add_field(
            name="💰 Gold",
            value=f"**{economy.gold:,}**",
            inline=True
        )
        
        embed.add_field(
            name="🎫 Tickets",
            value=f"**{economy.tickets}**",
            inline=True
        )
        
        # Daily claim status
        if economy.can_claim_daily():
            claim_status = "✅ Available!"
        else:
            time_since = datetime.now() - economy.last_daily_claim
            time_until = timedelta(hours=24) - time_since
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            claim_status = f"⏰ {hours}h {minutes}m"
        
        embed.add_field(
            name="🎁 Daily Claim",
            value=claim_status,
            inline=True
        )
        
        # Streak info
        if economy.daily_streak > 0:
            embed.add_field(
                name="🔥 Daily Streak",
                value=f"**{economy.daily_streak} days**",
                inline=True
            )
        
        return embed
    
    @staticmethod
    def create_daily_claim_embed(result: Dict, username: str) -> discord.Embed:
        """Create embed for daily claim result"""
        if not result["success"]:
            # Failed claim
            time_until = result["time_until_next"]
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏰ Daily Claim Not Ready",
                description=f"Come back in **{hours}h {minutes}m**",
                color=0xe74c3c
            )
            return embed
        
        # Successful claim
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"**Streak:** {result['streak']} days",
            color=0x2ecc71
        )
        
        # Rewards
        reward_text = f"+{result['base_gold']} gold (base)"
        
        if result['bonus_gold'] > 0:
            reward_text += f"\n+{result['bonus_gold']} gold (streak bonus!)"
        
        if result['tickets'] > 0:
            reward_text += f"\n+{result['tickets']} tickets (streak bonus!)"
        
        embed.add_field(
            name="💰 Rewards",
            value=reward_text,
            inline=False
        )
        
        # Next milestone
        next_milestones = {
            3: "Day 3: +50 gold bonus",
            7: "Day 7: +200 gold, +1 ticket",
            14: "Day 14: +500 gold, +2 tickets",
            30: "Day 30: +1,000 gold, +5 tickets",
        }
        
        for milestone, reward in next_milestones.items():
            if result['streak'] < milestone:
                embed.set_footer(text=f"Next milestone: {reward}")
                break
        
        return embed


# Example usage
if __name__ == "__main__":
    # Create player economy
    player = PlayerEconomy(user_id="123456789")
    
    print(f"Starting gold: {player.gold}")
    print(f"Starting tickets: {player.tickets}")
    
    # Claim daily
    print("\n=== DAILY CLAIM ===")
    result = player.claim_daily()
    print(f"Success: {result['success']}")
    print(f"Gold earned: {result.get('gold', 0)}")
    print(f"Streak: {result.get('streak', 0)}")
    
    print(f"\nGold after claim: {player.gold}")
    
    # Try to buy pack
    print("\n=== BUY PACK ===")
    can_buy = PackPricing.can_afford_pack(player, "community", "gold")
    print(f"Can afford community pack: {can_buy}")
    
    if can_buy:
        success = PackPricing.purchase_pack(player, "community", "gold")
        print(f"Purchase successful: {success}")
        print(f"Gold after purchase: {player.gold}")
