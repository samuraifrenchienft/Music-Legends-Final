"""
battle_engine.py - Battle system for Music Legends
Handles card battles with power calculation and critical hits
"""

import random
import discord
from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from discord_cards import ArtistCard

class BattleEngine:
    """
    Battle system - power-based with RNG elements
    """
    
    # Battle settings
    CRITICAL_HIT_CHANCE = 0.15  # 15% chance for critical hit
    CRITICAL_MULTIPLIER = 1.5   # Critical hit = +50% power
    MIN_POWER_ADVANTAGE = 5     # Minimum power diff to matter
    
    # Wager tiers
    WAGER_TIERS = {
        "casual": {
            "gold": 50,
            "winner_base": 50,
            "loser_base": 10,
            "xp_reward": 25,
        },
        "standard": {
            "gold": 100,
            "winner_base": 75,
            "loser_base": 10,
            "xp_reward": 40,
        },
        "high": {
            "gold": 250,
            "winner_base": 100,
            "loser_base": 15,
            "xp_reward": 60,
        },
        "extreme": {
            "gold": 500,
            "winner_base": 150,
            "loser_base": 20,
            "xp_reward": 100,
        },
    }
    
    @classmethod
    def execute_battle(
        cls,
        card1: 'ArtistCard',
        card2: 'ArtistCard',
        wager_tier: str = "casual"
    ) -> Dict:
        """
        Execute a battle between two cards
        
        Args:
            card1: Player 1's card
            card2: Player 2's card
            wager_tier: Wager level (casual/standard/high/extreme)
        
        Returns:
            Battle result dictionary with winner, powers, rewards
        """
        
        # Get base power
        power1 = card1.power
        power2 = card2.power
        
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
            # Too close - tie
            winner = 0
        elif power1 > power2:
            winner = 1
        else:
            winner = 2
        
        # Get wager info
        wager_info = cls.WAGER_TIERS.get(wager_tier, cls.WAGER_TIERS["casual"])
        
        # Calculate rewards
        if winner == 1:
            player1_gold = wager_info["winner_base"] + wager_info["gold"]
            player2_gold = wager_info["loser_base"]
            player1_xp = wager_info["xp_reward"]
            player2_xp = int(wager_info["xp_reward"] * 0.2)
        elif winner == 2:
            player1_gold = wager_info["loser_base"]
            player2_gold = wager_info["winner_base"] + wager_info["gold"]
            player1_xp = int(wager_info["xp_reward"] * 0.2)
            player2_xp = wager_info["xp_reward"]
        else:
            # Tie - both get small rewards, wagers returned
            player1_gold = 25
            player2_gold = 25
            player1_xp = 10
            player2_xp = 10
        
        return {
            "winner": winner,  # 0 = tie, 1 = player1, 2 = player2
            "player1": {
                "card": card1,
                "base_power": card1.power,
                "final_power": power1,
                "critical_hit": crit1,
                "gold_reward": player1_gold,
                "xp_reward": player1_xp,
            },
            "player2": {
                "card": card2,
                "base_power": card2.power,
                "final_power": power2,
                "critical_hit": crit2,
                "gold_reward": player2_gold,
                "xp_reward": player2_xp,
            },
            "power_difference": power_diff,
            "wager": wager_info["gold"],
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
    
    @classmethod
    def simulate_battle(
        cls,
        card1: 'ArtistCard',
        card2: 'ArtistCard',
        num_simulations: int = 100
    ) -> Dict:
        """
        Simulate multiple battles to calculate win probability
        
        Args:
            card1: Player 1's card
            card2: Player 2's card
            num_simulations: Number of battles to simulate
        
        Returns:
            Statistics dictionary with win rates
        """
        
        wins = {1: 0, 2: 0, 0: 0}  # Player 1, Player 2, Tie
        
        for _ in range(num_simulations):
            result = cls.execute_battle(card1, card2)
            wins[result["winner"]] += 1
        
        return {
            "player1_win_rate": wins[1] / num_simulations,
            "player2_win_rate": wins[2] / num_simulations,
            "tie_rate": wins[0] / num_simulations,
            "player1_favored": wins[1] > wins[2],
            "simulations": num_simulations,
        }


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


# Example usage
if __name__ == "__main__":
    # Create test cards
    from discord_cards import ArtistCard
    
    drake_card = ArtistCard(
        card_id="1",
        artist="Drake",
        song="Hotline Bling",
        youtube_url="https://youtube.com/watch?v=xyz",
        youtube_id="xyz",
        view_count=1_200_000_000,
        thumbnail="",
        rarity="legendary"
    )
    
    taylor_card = ArtistCard(
        card_id="2",
        artist="Taylor Swift",
        song="Shake It Off",
        youtube_url="https://youtube.com/watch?v=abc",
        youtube_id="abc",
        view_count=800_000_000,
        thumbnail="",
        rarity="epic"
    )
    
    # Simulate battle
    print("=== BATTLE SIMULATION ===")
    result = BattleEngine.execute_battle(drake_card, taylor_card, "high")
    
    print(f"Drake: {result['player1']['final_power']} power")
    print(f"Taylor: {result['player2']['final_power']} power")
    print(f"Winner: Player {result['winner']}")
    print(f"Power diff: {result['power_difference']}")
    
    # Probability analysis
    print("\n=== WIN PROBABILITY (100 simulations) ===")
    stats = BattleEngine.simulate_battle(drake_card, taylor_card, 100)
    print(f"Drake win rate: {stats['player1_win_rate'] * 100:.1f}%")
    print(f"Taylor win rate: {stats['player2_win_rate'] * 100:.1f}%")
    print(f"Tie rate: {stats['tie_rate'] * 100:.1f}%")
