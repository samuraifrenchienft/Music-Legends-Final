# services/marketplace_announcements.py
"""
Daily Marketplace Update System
Generates and posts daily marketplace statistics and updates
"""

import discord
from datetime import datetime, timedelta
from typing import Dict, Optional
from database import DatabaseManager


class MarketplaceAnnouncementService:
    """Handles daily marketplace update generation and posting"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def record_pack_creation(self, pack_id: str, creator_id: int):
        """Record a new pack creation for today's stats"""
        today = datetime.now().date()
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Initialize today's record if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO marketplace_daily_stats (date, packs_added)
                VALUES (?, 0)
            """, (today,))
            
            # Increment packs_added
            cursor.execute("""
                UPDATE marketplace_daily_stats
                SET packs_added = packs_added + 1
                WHERE date = ?
            """, (today,))
            
            conn.commit()
    
    def record_pack_purchase(self, pack_id: str, buyer_id: int, price_cents: int):
        """Record a pack purchase for today's stats"""
        today = datetime.now().date()
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Initialize today's record if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO marketplace_daily_stats (date, packs_sold, total_revenue_cents)
                VALUES (?, 0, 0)
            """, (today,))
            
            # Increment stats
            cursor.execute("""
                UPDATE marketplace_daily_stats
                SET packs_sold = packs_sold + 1,
                    total_revenue_cents = total_revenue_cents + ?
                WHERE date = ?
            """, (price_cents, today))
            
            conn.commit()
    
    def generate_daily_summary(self, date: Optional[datetime.date] = None) -> Dict:
        """Generate summary for a specific date (defaults to yesterday)"""
        if date is None:
            date = (datetime.now() - timedelta(days=1)).date()
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get daily stats
            cursor.execute("""
                SELECT * FROM marketplace_daily_stats
                WHERE date = ?
            """, (date,))
            
            row = cursor.fetchone()
            
            if not row:
                return {
                    'date': date,
                    'packs_added': 0,
                    'packs_sold': 0,
                    'revenue': 0,
                    'top_pack': None,
                    'top_creator': None
                }
            
            columns = [desc[0] for desc in cursor.description]
            stats = dict(zip(columns, row))
            
            # Get top pack info
            if stats.get('top_pack_id'):
                cursor.execute("""
                    SELECT name, creator_id FROM creator_packs
                    WHERE pack_id = ?
                """, (stats['top_pack_id'],))
                pack_info = cursor.fetchone()
                stats['top_pack_name'] = pack_info[0] if pack_info else "Unknown"
            
            # Get top creator info
            if stats.get('top_creator_id'):
                cursor.execute("""
                    SELECT username FROM users
                    WHERE user_id = ?
                """, (stats['top_creator_id'],))
                creator_info = cursor.fetchone()
                stats['top_creator_name'] = creator_info[0] if creator_info else "Unknown"
            
            return stats
    
    def create_announcement_embed(self, stats: Dict) -> discord.Embed:
        """Create Discord embed for daily marketplace update"""
        date = stats['date']
        date_str = date.strftime('%B %d, %Y') if isinstance(date, datetime) else str(date)
        
        # Determine color based on activity
        if stats['packs_added'] > 10:
            color = discord.Color.green()
            activity_level = "🔥 HIGHLY ACTIVE"
        elif stats['packs_added'] > 5:
            color = discord.Color.gold()
            activity_level = "📈 ACTIVE"
        elif stats['packs_added'] > 0:
            color = discord.Color.blue()
            activity_level = "📊 MODERATE"
        else:
            color = discord.Color.light_gray()
            activity_level = "🌙 QUIET DAY"
        
        embed = discord.Embed(
            title=f"🛍️ Daily Marketplace Update - {date_str}",
            description=f"{activity_level}\n\nYour daily snapshot of marketplace activity!",
            color=color
        )
        
        # Packs Added
        packs_emoji = "📦" * min(stats['packs_added'], 5)
        embed.add_field(
            name="📦 New Packs Added",
            value=f"**{stats['packs_added']}** new packs {packs_emoji}",
            inline=True
        )
        
        # Packs Sold
        sales_emoji = "💰" * min(stats['packs_sold'], 5)
        embed.add_field(
            name="💎 Packs Sold",
            value=f"**{stats['packs_sold']}** packs sold {sales_emoji}",
            inline=True
        )
        
        # Revenue
        revenue_dollars = stats.get('total_revenue_cents', 0) / 100
        embed.add_field(
            name="💵 Total Revenue",
            value=f"${revenue_dollars:.2f}",
            inline=True
        )
        
        # Top Pack
        if stats.get('top_pack_name'):
            embed.add_field(
                name="🏆 Trending Pack",
                value=f"**{stats['top_pack_name']}**\n{stats.get('top_pack_sales', 0)} sales",
                inline=False
            )
        
        # Top Creator
        if stats.get('top_creator_name'):
            embed.add_field(
                name="⭐ Top Creator",
                value=f"**{stats['top_creator_name']}**",
                inline=True
            )
        
        # Call to action
        if stats['packs_added'] > 0:
            embed.add_field(
                name="🎴 Browse New Packs",
                value="Use `/packs` to explore the latest additions!",
                inline=False
            )
        
        embed.set_footer(text="Daily updates powered by Music Legends Marketplace")
        embed.timestamp = datetime.now()
        
        return embed
    
    async def post_daily_update(self, channel: discord.TextChannel):
        """Post daily marketplace update to a channel"""
        try:
            yesterday_stats = self.generate_daily_summary()
            embed = self.create_announcement_embed(yesterday_stats)
            
            message = await channel.send(embed=embed)
            
            # Add reactions for engagement
            try:
                await message.add_reaction("📦")
                await message.add_reaction("💎")
            except:
                pass
            
            return True
        except Exception as e:
            print(f"❌ Failed to post marketplace update: {e}")
            return False


# Global instance
marketplace_announcements = None

def get_marketplace_announcements(db: DatabaseManager = None) -> MarketplaceAnnouncementService:
    """Get or create marketplace announcements service"""
    global marketplace_announcements
    if marketplace_announcements is None:
        if db is None:
            db = DatabaseManager()
        marketplace_announcements = MarketplaceAnnouncementService(db)
    return marketplace_announcements
