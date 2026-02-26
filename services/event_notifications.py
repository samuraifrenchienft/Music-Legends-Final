# services/event_notifications.py
"""
Event Notification Service
Handle notifications for creators and admins
"""

from typing import Dict, Any, Optional
from datetime import datetime
from models.creator_pack import CreatorPack
from models.card import Card
from models.audit_minimal import AuditLog
import discord

class EventNotificationService:
    """Service for handling event notifications"""
    
    def __init__(self, bot=None):
        self.bot = bot
    
    async def notify_pack_approved(self, pack: CreatorPack, admin_id: int):
        """Notify creator that pack was approved"""
        try:
            # Get creator user
            creator = self.bot.get_user(pack.owner_id) if self.bot else None
            
            if creator:
                embed = discord.Embed(
                    title="✅ Your Pack Was Approved!",
                    description=f"Your creator pack '{pack.name}' has been approved and is now live!",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack Details", value=f"Name: {pack.name}\nGenre: {pack.genre}\nArtists: {len(pack.artist_ids) if pack.artist_ids else 0}", inline=False)
                embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="📊 Status", value="✅ Approved & Available", inline=True)
                embed.add_field(name="🎮 Next Steps", value="You can now open your pack to collect cards! Use `/creator_dashboard` to manage your packs.", inline=False)
                embed.add_field(name="📅 Approved At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
                
                await creator.send(embed=embed)
                
                # Log notification
                AuditLog.record(
                    event="creator_approval_notification_sent",
                    user_id=admin_id,
                    target_id=str(pack.id),
                    payload={
                        "pack_name": pack.name,
                        "creator_id": pack.owner_id,
                        "notified_at": datetime.utcnow().isoformat()
                    }
                )
                
                return True
            else:
                print(f"Could not find creator user {pack.owner_id}")
                return False
                
        except Exception as e:
            print(f"Error notifying creator about approval: {e}")
            return False
    
    async def notify_pack_rejected(self, pack: CreatorPack, admin_id: int, reason: str):
        """Notify creator that pack was rejected"""
        try:
            creator = self.bot.get_user(pack.owner_id) if self.bot else None
            
            if creator:
                embed = discord.Embed(
                    title="❌ Your Pack Was Rejected",
                    description=f"Your creator pack '{pack.name}' was not approved.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack Details", value=f"Name: {pack.name}\nGenre: {pack.genre}\nArtists: {len(pack.artist_ids) if pack.artist_ids else 0}", inline=False)
                embed.add_field(name="📝 Rejection Reason", value=reason, inline=False)
                embed.add_field(name="💰 Payment", value="Your payment has been automatically refunded", inline=True)
                embed.add_field(name="🔄 Next Steps", value="You can edit your pack and resubmit for review. Use `/creator_dashboard` to manage your packs.", inline=False)
                embed.add_field(name="📅 Rejected At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
                
                await creator.send(embed=embed)
                
                # Log notification
                AuditLog.record(
                    event="creator_rejection_notification_sent",
                    user_id=admin_id,
                    target_id=str(pack.id),
                    payload={
                        "pack_name": pack.name,
                        "creator_id": pack.owner_id,
                        "rejection_reason": reason,
                        "notified_at": datetime.utcnow().isoformat()
                    }
                )
                
                return True
            else:
                print(f"Could not find creator user {pack.owner_id}")
                return False
                
        except Exception as e:
            print(f"Error notifying creator about rejection: {e}")
            return False
    
    async def notify_admin_channel_pack_approved(self, pack: CreatorPack, admin_id: int):
        """Notify admin channel about pack approval"""
        try:
            if not self.bot:
                return False
            
            # Find admin notification channel
            guild = self.bot.get_guild(pack.owner_id)  # This would need adjustment for multi-guild
            if not guild:
                return False
            
            # Look for admin channels
            admin_channel = None
            channel_names = ["admin-log", "admin-logs", "admin-notifications", "moderator-log"]
            
            for channel_name in channel_names:
                admin_channel = discord.utils.get(guild.text_channels, name=channel_name)
                if admin_channel:
                    break
            
            if not admin_channel:
                print("No admin notification channel found")
                return False
            
            embed = discord.Embed(
                title="📦 Pack Approved",
                description=f"Creator pack has been approved and activated",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Pack Name", value=pack.name, inline=True)
            embed.add_field(name="Pack ID", value=str(pack.id)[:8], inline=True)
            embed.add_field(name="Approved By", value=f"<@{admin_id}>", inline=True)
            embed.add_field(name="Creator", value=f"<@{pack.owner_id}>", inline=True)
            embed.add_field(name="Payment Captured", value=f"${pack.price_cents / 100:.2f}", inline=True)
            embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
            embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids) if pack.artist_ids else 0), inline=True)
            embed.add_field(name="📅 Approved At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
            
            await admin_channel.send(embed=embed)
            
            # Log notification
            AuditLog.record(
                event="admin_approval_notification_sent",
                user_id=admin_id,
                target_id=str(pack.id),
                payload={
                    "pack_name": pack.name,
                    "admin_channel": admin_channel.name,
                    "notified_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error notifying admin channel about approval: {e}")
            return False
    
    async def notify_admin_channel_pack_rejected(self, pack: CreatorPack, admin_id: int, reason: str):
        """Notify admin channel about pack rejection"""
        try:
            if not self.bot:
                return False
            
            guild = self.bot.get_guild(pack.owner_id)
            if not guild:
                return False
            
            # Find admin channel
            admin_channel = None
            channel_names = ["admin-log", "admin-logs", "admin-notifications", "moderator-log"]
            
            for channel_name in channel_names:
                admin_channel = discord.utils.get(guild.text_channels, name=channel_name)
                if admin_channel:
                    break
            
            if not admin_channel:
                return False
            
            embed = discord.Embed(
                title="❌ Pack Rejected",
                description=f"Creator pack has been rejected",
                color=discord.Color.red()
            )
            
            embed.add_field(name="Pack Name", value=pack.name, inline=True)
            embed.add_field(name="Pack ID", value=str(pack.id)[:8], inline=True)
            embed.add_field(name="Rejected By", value=f"<@{admin_id}>", inline=True)
            embed.add_field(name="Creator", value=f"<@{pack.owner_id}>", inline=True)
            embed.add_field(name="Payment Status", value="💸 Refunded", inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            embed.add_field(name="📅 Rejected At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
            
            await admin_channel.send(embed=embed)
            
            # Log notification
            AuditLog.record(
                event="admin_rejection_notification_sent",
                user_id=admin_id,
                target_id=str(pack.id),
                payload={
                    "pack_name": pack.name,
                    "rejection_reason": reason,
                    "admin_channel": admin_channel.name,
                    "notified_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error notifying admin channel about rejection: {e}")
            return False
    
    async def notify_legendary_card_created(self, card: Card, pack: CreatorPack):
        """Notify admin channel about legendary card creation"""
        try:
            if not self.bot or card.tier != "legendary":
                return False
            
            guild = self.bot.get_guild(pack.owner_id)
            if not guild:
                return False
            
            # Find admin channel
            admin_channel = None
            channel_names = ["admin-log", "admin-logs", "admin-notifications", "card-drops", "legendary-alerts"]
            
            for channel_name in channel_names:
                admin_channel = discord.utils.get(guild.text_channels, name=channel_name)
                if admin_channel:
                    break
            
            if not admin_channel:
                return False
            
            embed = discord.Embed(
                title="🏆 Legendary Card Created!",
                description=f"A legendary card was created from a creator pack",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="🎴 Card", value=f"{card.artist_name} ({card.tier})", inline=True)
            embed.add_field(name="🔢 Serial", value=card.serial, inline=True)
            embed.add_field(name="👤 Owner", value=f"<@{card.owner_id}>", inline=True)
            embed.add_field(name="📦 Source Pack", value=f"{pack.name} (ID: {str(pack.id)[:8]})", inline=False)
            embed.add_field(name="👤 Pack Creator", value=f"<@{pack.owner_id}>", inline=True)
            embed.add_field(name="📅 Created At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
            
            # Add card image if available
            if hasattr(card, 'image_url') and card.image_url:
                embed.set_thumbnail(url=card.image_url)
            
            await admin_channel.send(embed=embed)
            
            # Log notification
            AuditLog.record(
                event="legendary_card_notification_sent",
                user_id=card.owner_id,
                target_id=str(card.id),
                payload={
                    "card_serial": card.serial,
                    "card_tier": card.tier,
                    "artist_name": card.artist_name,
                    "pack_id": str(pack.id),
                    "pack_name": pack.name,
                    "notified_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error notifying about legendary card: {e}")
            return False
    
    async def notify_pack_payment_failed(self, pack: CreatorPack, error: str):
        """Notify creator about payment failure"""
        try:
            creator = self.bot.get_user(pack.owner_id) if self.bot else None
            
            if creator:
                embed = discord.Embed(
                    title="❌ Payment Failed",
                    description=f"There was an issue with the payment for your pack '{pack.name}'",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack", value=pack.name, inline=True)
                embed.add_field(name="💰 Amount", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="❌ Error", value=error, inline=False)
                embed.add_field(name="🔄 Next Steps", value="Please check your payment method and try again, or contact support if the issue persists.", inline=False)
                
                await creator.send(embed=embed)
                
                # Log notification
                AuditLog.record(
                    event="payment_failure_notification_sent",
                    user_id=pack.owner_id,
                    target_id=str(pack.id),
                    payload={
                        "pack_name": pack.name,
                        "error": error,
                        "notified_at": datetime.utcnow().isoformat()
                    }
                )
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error notifying about payment failure: {e}")
            return False
    
    async def send_admin_message_to_creator(self, pack: CreatorPack, admin_id: int, message: str):
        """Send message from admin to creator"""
        try:
            creator = self.bot.get_user(pack.owner_id) if self.bot else None
            
            if creator:
                embed = discord.Embed(
                    title="💬 Message from Admin",
                    description=f"Regarding your pack '{pack.name}'",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="📝 Message", value=message, inline=False)
                embed.add_field(name="👤 Sent By", value=f"<@{admin_id}>", inline=True)
                embed.add_field(name="📅 Sent At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
                
                await creator.send(embed=embed)
                
                # Log notification
                AuditLog.record(
                    event="admin_message_sent_to_creator",
                    user_id=admin_id,
                    target_id=str(pack.id),
                    payload={
                        "pack_name": pack.name,
                        "creator_id": pack.owner_id,
                        "message": message,
                        "notified_at": datetime.utcnow().isoformat()
                    }
                )
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error sending admin message to creator: {e}")
            return False
    
    async def notify_pack_disabled(self, pack: CreatorPack, admin_id: int, reason: str):
        """Notify creator that pack was disabled"""
        try:
            creator = self.bot.get_user(pack.owner_id) if self.bot else None
            
            if creator:
                embed = discord.Embed(
                    title="⚫ Your Pack Was Disabled",
                    description=f"Your creator pack '{pack.name}' has been disabled.",
                    color=discord.Color.dark_grey()
                )
                
                embed.add_field(name="📦 Pack Details", value=f"Name: {pack.name}\nGenre: {pack.genre}", inline=False)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                embed.add_field(name="⚠️ Impact", value="Your pack is no longer available for opening. Existing cards remain in your collection.", inline=True)
                embed.add_field(name="🔄 Next Steps", value="Contact an admin if you believe this was done in error.", inline=False)
                embed.add_field(name="📅 Disabled At", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"), inline=True)
                
                await creator.send(embed=embed)
                
                # Log notification
                AuditLog.record(
                    event="creator_disable_notification_sent",
                    user_id=admin_id,
                    target_id=str(pack.id),
                    payload={
                        "pack_name": pack.name,
                        "creator_id": pack.owner_id,
                        "disable_reason": reason,
                        "notified_at": datetime.utcnow().isoformat()
                    }
                )
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error notifying creator about pack disable: {e}")
            return False


# Global notification service instance
event_notifications = EventNotificationService()


# Convenience functions
async def notify_pack_approved(pack: CreatorPack, admin_id: int):
    """Notify pack approval"""
    return await event_notifications.notify_pack_approved(pack, admin_id)


async def notify_pack_rejected(pack: CreatorPack, admin_id: int, reason: str):
    """Notify pack rejection"""
    return await event_notifications.notify_pack_rejected(pack, admin_id, reason)


async def notify_admin_channel_pack_approved(pack: CreatorPack, admin_id: int):
    """Notify admin channel about approval"""
    return await event_notifications.notify_admin_channel_pack_approved(pack, admin_id)


async def notify_legendary_card_created(card: Card, pack: CreatorPack):
    """Notify about legendary card creation"""
    return await event_notifications.notify_legendary_card_created(card, pack)


# Example usage
def example_usage():
    """Example of notification service usage"""
    
    print("📢 Event Notification Service Examples:")
    print("=====================================")
    
    print("1. Pack Approval Notification:")
    print("   ✅ Creator gets approval message")
    print("   ✅ Admin channel gets approval notification")
    print("   ✅ Audit log records notification")
    
    print("\n2. Pack Rejection Notification:")
    print("   ✅ Creator gets rejection message with reason")
    print("   ✅ Admin channel gets rejection notification")
    print("   ✅ Payment refund information included")
    
    print("\n3. Legendary Card Notification:")
    print("   ✅ Admin channel gets legendary alert")
    print("   ✅ Card details and pack information")
    print("   ✅ Owner information included")
    
    print("\n4. Admin Message to Creator:")
    print("   ✅ Direct message from admin")
    print("   ✅ Pack context included")
    print("   ✅ Admin identification")


if __name__ == "__main__":
    example_usage()
