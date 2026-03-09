"""Telegram bot handlers.
Runs inside FastAPI process via webhook (no polling).
Handles: /start, /link, outbound battle notifications.
"""
import os
import logging
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

_app: Application | None = None
_bot: Bot | None = None
logger = logging.getLogger(__name__)


def _base_tma_url() -> str:
    """Return a safe HTTPS URL for opening the mini app."""
    raw = (os.environ.get("TMA_URL") or "").strip()
    if not raw:
        bot_username = (os.environ.get("TELEGRAM_BOT_USERNAME") or "MusicLegendsBot").lstrip("@")
        return f"https://t.me/{bot_username}"
    if raw.startswith("t.me/"):
        raw = f"https://{raw}"
    if raw.startswith("http://"):
        raw = "https://" + raw[len("http://") :]
    parsed = urlparse(raw)
    if parsed.scheme != "https":
        bot_username = (os.environ.get("TELEGRAM_BOT_USERNAME") or "MusicLegendsBot").lstrip("@")
        return f"https://t.me/{bot_username}"
    return raw


def _tma_url(start_param: str = "") -> str:
    """Build a deep link while preserving existing query params."""
    base = _base_tma_url()
    if not start_param:
        return base
    parsed = urlparse(base)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    q["startapp"] = start_param
    new_query = urlencode(q)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """/start [battle_XXXXX] — Open TMA, optionally at a specific deep link."""
    args = ctx.args or []
    start_param = args[0] if args else ""
    url = _tma_url(start_param)
    tma_configured = bool((os.environ.get("TMA_URL") or "").strip())

    chat_type = getattr(update.effective_chat, "type", "")
    if chat_type in {"group", "supergroup"}:
        await update.message.reply_text(
            "Use the Mini App from our private chat with the bot.\n"
            f"Open here: {url}"
        )
        return

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎴 Play Music Legends", url=url)
    ]])
    try:
        battle_code_hint = ""
        if start_param.startswith("battle_"):
            battle_code_hint = f"\n\nBattle code: `{start_param.replace('battle_', '').upper()}`"
            if not tma_configured:
                battle_code_hint += "\nIf app deep-linking fails, open the Mini App from bot menu and paste this code in Battle."
        await update.message.reply_text(
            "🎵 *Music Legends* — collect artist cards, battle friends, win gold!\n\n"
            f"Tap below to open the game:{battle_code_hint}",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception as e:
        # Fallback to plain text so /start still responds if Telegram rejects button payload.
        logger.warning("cmd_start button send failed: %s", e)
        await update.message.reply_text(
            "🎵 Music Legends\n"
            f"Open the game here: {url}"
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
        # Use Railway's auto-provided domain (the FastAPI service URL).
        # Fall back to TMA_API_URL if set, but never use TMA_URL (that's the t.me link).
        railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
        api_base = os.environ.get("TMA_API_URL", "")
        if railway_domain:
            webhook_base = f"https://{railway_domain.rstrip('/')}"
        elif api_base:
            webhook_base = api_base.rstrip("/")
        else:
            webhook_base = ""
        if webhook_base.startswith("https://"):
            try:
                await _bot.set_webhook(f"{webhook_base}/webhook")
                print(f"[BOT] Webhook set: {webhook_base}/webhook")
            except Exception as e:
                print(f"[BOT] Webhook setup failed: {e}")
        else:
            print(f"[BOT] No webhook URL found (RAILWAY_PUBLIC_DOMAIN not set) — skipping")

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
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⚔️ Accept Battle", url=link)
        ]])
        await _bot.send_message(
            chat_id=opponent_telegram_id,
            text=(
                f"⚔️ *{challenger_name}* challenged you to a battle!\n"
                f"Tier: *{wager_tier.upper()}*\n\n"
                f"If the button does not open the battle, use /start battle_{battle_id}."
            ),
            reply_markup=keyboard,
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
    ph = db._get_placeholder()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT telegram_id FROM users WHERE user_id = {ph}", (str(challenger_id),))
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
