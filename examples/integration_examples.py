# examples/integration_examples.py
# Examples of how to integrate monitoring into your services

from monitor.alerts import (
    send_ops, send_econ, legendary_created, purchase_completed,
    refund_executed, trade_completed, pack_opened, system_error
)

# Economy Service Integration
class EconomyService:
    async def create_legendary_card(self, user_id, card_data):
        """Create legendary card with monitoring"""
        try:
            # Your card creation logic here
            card = await self._create_card(user_id, card_data)
            
            # Send economy alert
            await legendary_created(
                user_id=user_id,
                card_serial=card.serial,
                card_name=card.name
            )
            
            return card
            
        except Exception as e:
            await system_error(f"Failed to create legendary card: {e}", {"user_id": user_id})
            raise
    
    async def process_purchase(self, user_id, purchase_data):
        """Process purchase with monitoring"""
        try:
            # Your purchase logic here
            purchase = await self._process_payment(user_id, purchase_data)
            
            # Send economy alert
            await purchase_completed(
                user_id=user_id,
                purchase_id=purchase.id,
                amount=purchase.amount_cents,
                pack_type=purchase.pack_type
            )
            
            return purchase
            
        except Exception as e:
            await system_error(f"Purchase processing failed: {e}", {"user_id": user_id, "purchase_id": purchase_data.get("id")})
            raise
    
    async def process_refund(self, user_id, purchase_id, amount):
        """Process refund with monitoring"""
        try:
            # Your refund logic here
            refund = await self._execute_refund(user_id, purchase_id, amount)
            
            # Send economy alert
            await refund_executed(
                user_id=user_id,
                purchase_id=purchase_id,
                amount=amount
            )
            
            return refund
            
        except Exception as e:
            await system_error(f"Refund processing failed: {e}", {"user_id": user_id, "purchase_id": purchase_id})
            raise
    
    async def open_pack(self, user_id, pack_type):
        """Open pack with monitoring"""
        try:
            # Your pack opening logic here
            cards = await self._generate_pack_cards(pack_type)
            await self._award_cards(user_id, cards)
            
            # Check for legendary
            legendary_count = sum(1 for card in cards if card.tier == "legendary")
            
            # Send economy alert
            await pack_opened(
                user_id=user_id,
                pack_type=pack_type,
                card_count=len(cards),
                legendary=legendary_count > 0
            )
            
            return cards
            
        except Exception as e:
            await system_error(f"Pack opening failed: {e}", {"user_id": user_id, "pack_type": pack_type})
            raise


# Trade Service Integration
class TradeService:
    async def complete_trade(self, trade_id):
        """Complete trade with monitoring"""
        try:
            # Your trade completion logic here
            trade = await self._finalize_trade(trade_id)
            
            # Send economy alert
            await trade_completed(
                user_a=trade.user_a,
                user_b=trade.user_b,
                trade_id=trade_id,
                card_count=len(trade.cards_a) + len(trade.cards_b)
            )
            
            return trade
            
        except Exception as e:
            await system_error(f"Trade completion failed: {e}", {"trade_id": trade_id})
            raise


# Bot Event Integration
class BotEvents:
    def __init__(self, bot):
        self.bot = bot
        
    async def on_ready(self):
        """Bot ready event with monitoring"""
        await send_ops("🚀 Bot Online", f"Music Legends bot is ready\nGuilds: {len(self.bot.guilds)}", "success")
        
    async def on_command_error(self, ctx, error):
        """Command error with monitoring"""
        if isinstance(error, discord.CommandError):
            await system_error(
                f"Command error: {error}",
                {
                    "command": ctx.command.name if ctx.command else "Unknown",
                    "user": ctx.author.id,
                    "guild": ctx.guild.id if ctx.guild else "DM"
                }
            )
    
    async def on_guild_join(self, guild):
        """Guild join event with monitoring"""
        await send_ops(
            "📈 New Guild", 
            f"Bot added to {guild.name} ({guild.id})\nMembers: {guild.member_count}",
            "success"
        )
    
    async def on_guild_remove(self, guild):
        """Guild leave event with monitoring"""
        await send_ops(
            "📉 Guild Left", 
            f"Bot removed from {guild.name} ({guild.id})",
            "warning"
        )


# Background Task Integration
class BackgroundTasks:
    def __init__(self, redis_conn, queues):
        self.redis_conn = redis_conn
        self.queues = queues
        
    async def backup_database(self):
        """Database backup with monitoring"""
        try:
            # Your backup logic here
            backup_path = await self._create_backup()
            backup_size = await self._get_backup_size(backup_path)
            
            await send_ops(
                "💾 Database Backup",
                f"Backup completed successfully\nSize: {backup_size}\nPath: {backup_path}",
                "success"
            )
            
        except Exception as e:
            await system_error(f"Database backup failed: {e}")
            raise
    
    async def cleanup_expired_data(self):
        """Data cleanup with monitoring"""
        try:
            # Your cleanup logic here
            deleted_count = await self._cleanup_expired_records()
            
            await send_ops(
                "🧹 Data Cleanup",
                f"Cleaned up {deleted_count} expired records",
                "success"
            )
            
        except Exception as e:
            await system_error(f"Data cleanup failed: {e}")
            raise


# Usage in your main bot file
async def setup_monitoring(bot):
    """Setup monitoring for the bot"""
    # Load monitoring commands
    await bot.load_extension("cogs.monitor_commands")
    
    # Setup bot events
    bot_events = BotEvents(bot)
    bot.add_listener(bot_events.on_ready, "on_ready")
    bot.add_listener(bot_events.on_command_error, "on_command_error")
    bot.add_listener(bot_events.on_guild_join, "on_guild_join")
    bot.add_listener(bot_events.on_guild_remove, "on_guild_remove")
    
    # Start background monitoring
    from monitor.health_checks import start_monitoring
    
    # Get Redis connection and queues (you'll need to implement this)
    redis_conn = get_redis_connection()  # Your Redis connection
    queues = get_all_queues()  # Your queue dictionary
    
    # Start monitoring in background
    asyncio.create_task(start_monitoring(redis_conn, queues))


# Example service usage
async def example_usage():
    """Example of how to use the monitoring in your services"""
    
    # Economy service
    economy = EconomyService()
    
    # Create legendary card
    await economy.create_legendary_card(
        user_id=12345,
        card_data={"name": "Fire Dragon", "tier": "legendary"}
    )
    
    # Process purchase
    await economy.process_purchase(
        user_id=12345,
        purchase_data={"pack_type": "founder_pack_black", "amount_cents": 9999}
    )
    
    # Open pack
    await economy.open_pack(user_id=12345, pack_type="black")
    
    # Trade service
    trade_service = TradeService()
    await trade_service.complete_trade(trade_id="trade_123")
    
    # Manual alerts
    await send_ops("Manual Test", "This is a manual operations alert", "info")
    await send_econ("Manual Test", "This is a manual economy alert", "success")
