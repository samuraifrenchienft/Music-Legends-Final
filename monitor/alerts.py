# monitor/alerts.py
import aiohttp
import asyncio
from datetime import datetime
from config.monitor import MONITOR, ALERT_COLORS


async def send_ops(title, message, level="info"):
    """Send operations alert"""
    color = ALERT_COLORS.get(level, ALERT_COLORS["blue"])
    await _send(MONITOR["WEBHOOK_OPS"], title, message, color)


async def send_econ(title, message, level="info"):
    """Send economy alert"""
    color = ALERT_COLORS.get(level, ALERT_COLORS["green"])
    await _send(MONITOR["WEBHOOK_ECON"], title, message, color)


async def _send(url, title, message, color):
    """Send webhook with embed"""
    if not url:
        return  # fail safe

    embed = {
        "title": title,
        "description": message,
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }

    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"embeds": [embed]}, timeout=5)
        except Exception as e:
            # Fail silently to avoid infinite loops
            print(f"Webhook failed: {e}")


# Economy event helpers
async def legendary_created(user_id, card_serial, card_name=None):
    """Alert when legendary card is created"""
    message = f"User {user_id} → {card_serial}"
    if card_name:
        message += f" ({card_name})"
    await send_econ("🏆 Legendary Created", message, "success")


async def purchase_completed(user_id, purchase_id, amount, pack_type=None):
    """Alert when purchase is completed"""
    message = f"User {user_id} → Purchase {purchase_id}"
    if amount:
        message += f" (${amount/100:.2f})"
    if pack_type:
        message += f" - {pack_type}"
    await send_econ("💳 Purchase Completed", message, "success")


async def refund_executed(user_id, purchase_id, amount):
    """Alert when refund is processed"""
    message = f"User {user_id} → Refund {purchase_id}"
    if amount:
        message += f" (${amount/100:.2f})"
    await send_econ("💰 Refund Executed", message, "warning")


async def trade_completed(user_a, user_b, trade_id, card_count=None):
    """Alert when trade is completed"""
    message = f"Trade {trade_id}: {user_a} ↔ {user_b}"
    if card_count:
        message += f" ({card_count} cards)"
    await send_econ("🤝 Trade Completed", message, "success")


async def pack_opened(user_id, pack_type, card_count, legendary=False):
    """Alert when pack is opened"""
    message = f"User {user_id} opened {pack_type} pack ({card_count} cards)"
    if legendary:
        message += " 🏆 LEGENDARY!"
    await send_econ("📦 Pack Opened", message, "success" if legendary else "info")


# Operations event helpers
async def system_started():
    """Alert when system starts"""
    await send_ops("🚀 System Started", "Music Legends bot is online", "success")


async def system_error(error_message, context=None):
    """Alert when system error occurs"""
    message = error_message
    if context:
        message += f"\n\nContext: {context}"
    await send_ops("❌ System Error", message, "red")


async def database_backup_completed(backup_size, backup_path):
    """Alert when database backup completes"""
    message = f"Backup completed: {backup_size}\nPath: {backup_path}"
    await send_ops("💾 Database Backup", message, "success")


async def queue_backlog(queue_name, size, threshold=None):
    """Alert when queue has backlog"""
    message = f"Queue '{queue_name}': {size} jobs"
    if threshold:
        message += f" (threshold: {threshold})"
    await send_ops("⚠️ Queue Backlog", message, "orange" if size < threshold*2 else "red")


async def job_failures(failed_count, threshold=None):
    """Alert when jobs are failing"""
    message = f"{failed_count} failed jobs"
    if threshold:
        message += f" (threshold: {threshold})"
    await send_ops("🔥 Job Failures", message, "red" if failed_count > threshold else "orange")


async def worker_timeout(worker_name, duration, timeout_threshold):
    """Alert when worker times out"""
    message = f"Worker '{worker_name}' timed out after {duration}s (threshold: {timeout_threshold}s)"
    await send_ops("⏰ Worker Timeout", message, "red")


async def high_memory_usage(percentage, used_mb, total_mb):
    """Alert when memory usage is high"""
    message = f"Memory usage: {percentage}% ({used_mb}MB / {total_mb}MB)"
    await send_ops("💾 High Memory Usage", message, "orange" if percentage < 90 else "red")


async def redis_connection_failed():
    """Alert when Redis connection fails"""
    await send_ops("🔴 Redis Connection Failed", "Unable to connect to Redis server", "red")


async def database_connection_failed():
    """Alert when database connection fails"""
    await send_ops("🔴 Database Connection Failed", "Unable to connect to database", "red")
