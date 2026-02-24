"""Telegram bot handlers.
Runs inside FastAPI process via webhook (no polling).
Handles: /start, /link, outbound battle notifications.
"""
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

_app: Application | None = None
_bot: Bot | None = None


def _tma_url() -> str:
    return os.environ.get("TMA_URL", "https://t.me/MusicLegendsBot/app")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/start [battle_XXXXX] — Open TMA, optionally at a specific deep link."""
    args = ctx.args or []
    start_param = args[0] if args else ""
    url = f"{_tma_url()}?startapp={start_param}" if start_param else _tma_url()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎴 Play Music Legends", web_app=WebAppInfo(url=url))
    ]])
    await update.message.reply_text(
        "🎵 *Music Legends* — collect artist cards, battle friends, win gold!\n\n"
        "Tap below to open the game:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def cmd_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/link — Generate a code to link this Telegram account with Discord."""
    from database import get_db
    tg_id = update.effective_user.id
    tg_username = update.effective_user.username or ""
    db = get_db()
    user = db.get_or_create_telegram_user(tg_id, tg_username)
    code = db.generate_tma_link_code(user["user_id"])
    await update.message.reply_text(
        f"🔗 Your link code: `{code}`\n\n"
        f"Run this in Discord:\n`/link_telegram {code}`\n\n"
        f"_Code expires in 10 minutes._",
        parse_mode="Markdown",
    )


def build_application() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("link", cmd_link))
    return application


def setup_webhook_route(app) -> None:
    """Register /webhook POST route and startup/shutdown events on the FastAPI app."""
    from fastapi import Request

    @app.on_event("startup")
    async def _startup():
        global _app, _bot
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token or token == "dummy":
            print("[BOT] No real bot token — skipping Telegram bot setup")
            return
        _app = build_application()
        await _app.initialize()
        _bot = _app.bot
        webhook_url = os.environ.get("TMA_URL", "").rstrip("/")
        if webhook_url.startswith("https://"):
            try:
                await _bot.set_webhook(f"{webhook_url}/webhook")
                print(f"[BOT] Webhook set: {webhook_url}/webhook")
            except Exception as e:
                print(f"[BOT] Webhook setup failed: {e}")

    @app.on_event("shutdown")
    async def _shutdown():
        if _app:
            await _app.shutdown()

    @app.post("/webhook")
    async def _webhook(request: Request):
        if not _app or not _bot:
            return {"ok": False, "error": "Bot not initialised"}
        data = await request.json()
        update = Update.de_json(data, _bot)
        await _app.process_update(update)
        return {"ok": True}


# ── Outbound notifications ────────────────────────────────────────

async def notify_battle_challenge(
    opponent_telegram_id: int, challenger_name: str,
    battle_id: str, wager_tier: str, link: str,
) -> None:
    """Send battle challenge notification to opponent."""
    if not _bot:
        return
    try:
        await _bot.send_message(
            chat_id=opponent_telegram_id,
            text=(
                f"⚔️ *{challenger_name}* challenged you to a battle!\n"
                f"Tier: *{wager_tier.upper()}*\n\n"
                f"[🎴 Accept the challenge]({link})"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[BOT] Challenge notify failed for {opponent_telegram_id}: {e}")


async def notify_battle_result(
    challenger_id: int, result: dict,
    opponent_name: str, battle_id: str,
) -> None:
    """Notify challenger of battle result. challenger_id is our user_id — look up telegram_id."""
    if not _bot:
        return
    from database import get_db
    db = get_db()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users WHERE user_id = ?", (challenger_id,))
        row = cursor.fetchone()
    if not row or not row[0]:
        return

    winner = result.get("winner", 0)
    c = result.get("challenger", {})
    gold = c.get("gold_reward", 0)
    outcome = "🏆 You *WON*" if winner == 1 else ("😔 You *lost*" if winner == 2 else "🤝 *Draw*")

    try:
        await _bot.send_message(
            chat_id=row[0],
            text=(
                f"⚔️ Battle result vs *{opponent_name}*!\n\n"
                f"{outcome}\n"
                f"Your card: *{c.get('name', '?')}* (power {c.get('power', 0)})\n"
                f"Gold earned: *+{gold}* 💰"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[BOT] Result notify failed: {e}")
