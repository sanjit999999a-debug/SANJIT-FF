import os
import time
import html
import logging
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timezone

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ===================== CONFIGURATION =====================
# Load private settings from .env (never share that file).
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_USERNAME = "JOYxWEB"
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Put your numeric Telegram user ID here
CHANNELS = [
    {"chat_id": "@joy_webs", "url": "https://t.me/joy_webs", "title": "JOY WEBS"},
    # For the private invite channel, set PRIVATE_CHANNEL_ID to its numeric ID (usually -100...).
    {"chat_id": os.getenv("PRIVATE_CHANNEL_ID", ""), "url": "https://t.me/+O_Q5wllImjw3NTRl", "title": "Second Channel"},
]
DB_PATH = os.getenv("DB_PATH", "joy_webs_bot.sqlite3")
BOT_STARTED_AT = time.monotonic()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("JOY_WEBS")


# ===================== DATABASE =====================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, joined_at TEXT)")
    conn.commit()
    return conn


def save_user(user):
    if not user:
        return
    with db() as conn:
        conn.execute(
            "INSERT INTO users(user_id, first_name, username, joined_at) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username",
            (user.id, user.first_name or "", user.username or "", datetime.now(timezone.utc).isoformat())
        )


def user_count():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def all_user_ids():
    with db() as conn:
        return [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]


# ===================== KEYBOARDS =====================
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🆔 MY ID"), KeyboardButton("ℹ️ ABOUT")],
            [KeyboardButton("⚙️ COMMANDS"), KeyboardButton("🛡️ STATUS")],
            [KeyboardButton("📢 CHANNEL"), KeyboardButton("👑 OWNER")],
            [KeyboardButton("💎 PREMIUM"), KeyboardButton("💖 SUPPORT")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose a JOY WEBS feature…"
    )


def join_keyboard():
    rows = [
        [InlineKeyboardButton("📢 JOIN JOY WEBS", url=CHANNELS[0]["url"])],
        [InlineKeyboardButton("🔗 JOIN SECOND CHANNEL", url=CHANNELS[1]["url"])],
        [InlineKeyboardButton("✅ VERIFY MEMBERSHIP", callback_data="verify_join")],
    ]
    return InlineKeyboardMarkup(rows)


def premium_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💖 CONTACT OWNER", url=f"https://t.me/{OWNER_USERNAME}")],
        [InlineKeyboardButton("📢 UPDATE CHANNEL", url=CHANNELS[0]["url"])],
    ])


# ===================== MEMBERSHIP GATE =====================
async def is_member(bot, user_id: int) -> tuple[bool, list[str]]:
    missing = []
    for channel in CHANNELS:
        chat_id = channel["chat_id"]
        if not chat_id:
            # Configuration incomplete: fail closed so users cannot bypass the gate.
            missing.append(channel["title"] + " (bot setup incomplete)")
            continue
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                missing.append(channel["title"])
        except TelegramError as exc:
            log.warning("Membership check failed for %s: %s", channel["title"], exc)
            missing.append(channel["title"] + " (verification unavailable)")
    return len(missing) == 0, missing


async def send_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "✨ <b>JOY WEBS • MEMBER VERIFICATION</b> ✨\n\n"
        "🚀 Bot ke features unlock karne ke liye dono channels join karein.\n"
        "Join karne ke baad <b>VERIFY MEMBERSHIP</b> dabayein.\n\n"
        "🔒 Membership Telegram se check hogi."
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=join_keyboard()
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=join_keyboard()
        )


async def require_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    ok, missing = await is_member(context.bot, user.id)
    if not ok:
        await send_join_gate(update, context)
        return False
    return True


# ===================== MAIN CONTENT =====================
WELCOME = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "👑 <b>JOY WEBS</b> 👑\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "✨ Hello, {name}!\n"
    "✅ <b>Membership verified.</b>\n"
    "💎 <b>Access unlocked.</b>\n"
    "🔥 Welcome to the JOY WEBS experience!\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "⚙️ <b>QUICK ACCESS</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🆔 /id — Get your Telegram ID\n"
    "ℹ️ /about — About this bot\n"
    "⚙️ /commands — Full command list\n"
    "🛡️ /status — Bot status\n"
    "💎 /premium — Premium information\n"
    "💖 /support — Contact owner\n"
    "⏱️ /uptime — Bot uptime\n"
    "🌐 /ping — Response latency\n"
    "👑 /owner — Owner information\n\n"
    "✨ <i>Tap a button below to begin.</i> 👇"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    if not await require_membership(update, context):
        return
    await update.effective_message.reply_text(
        WELCOME.format(name=html.escape(user.first_name or "there")),
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(),
        disable_web_page_preview=True
    )


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    save_user(query.from_user)
    ok, missing = await is_member(context.bot, query.from_user.id)
    if ok:
        await query.message.reply_text(
            "✅ <b>VERIFICATION SUCCESSFUL!</b>\n\n"
            "💎 Both channels verified.\n🔥 JOY WEBS access is now unlocked.\n\n"
            "Send /start to open the premium menu.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard()
        )
    else:
        names = "\n".join(f"• {html.escape(item)}" for item in missing)
        await query.message.reply_text(
            "❌ <b>VERIFICATION FAILED</b>\n\n"
            "Please join both channels first, then tap verify again.\n\n"
            f"<b>Still missing / unable to check:</b>\n{names}",
            parse_mode=ParseMode.HTML,
            reply_markup=join_keyboard()
        )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    u = update.effective_user
    await update.effective_message.reply_text(
        f"🆔 <b>YOUR TELEGRAM DETAILS</b>\n\n"
        f"👤 Name: {html.escape(u.full_name)}\n"
        f"🔢 User ID: <code>{u.id}</code>\n"
        f"💬 Chat ID: <code>{update.effective_chat.id}</code>\n"
        f"🔗 Username: @{html.escape(u.username) if u.username else 'not set'}",
        parse_mode=ParseMode.HTML
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        "✨ <b>ABOUT JOY WEBS</b>\n\n"
        "A Telegram utility bot built for the JOY WEBS community.\n"
        "👑 Owner: @JOYxWEB\n"
        "📢 Updates: https://t.me/joy_webs\n\n"
        "⚠️ Features depend on the services configured by the owner.",
        parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        "⚙️ <b>JOY WEBS COMMAND CENTER</b>\n\n"
        "/start — Start bot\n/id — Your ID\n/about — About bot\n"
        "/commands — Command list\n/status — Bot status\n"
        "/premium — Premium info\n/support — Contact owner\n"
        "/owner — Owner info\n/uptime — Uptime\n/ping — Latency\n"
        "/users — User count (owner only)\n/broadcast — Broadcast (owner only; reply to a message)\n",
        parse_mode=ParseMode.HTML
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        f"🛡️ <b>BOT STATUS</b>\n\n🟢 Bot: Online\n"
        f"👥 Registered users: <b>{user_count()}</b>\n"
        f"⏱️ Uptime: <b>{format_uptime(time.monotonic() - BOT_STARTED_AT)}</b>",
        parse_mode=ParseMode.HTML
    )


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        "💎 <b>JOY WEBS PREMIUM</b>\n\n"
        "Premium plans and availability are managed by the owner.\n"
        "Contact @JOYxWEB for current details.\n\n"
        "⚠️ This starter script does not take payments or grant paid access automatically.",
        parse_mode=ParseMode.HTML, reply_markup=premium_keyboard()
    )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        "💖 <b>CONTACT SUPPORT</b>\n\nOwner: @JOYxWEB",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Message Owner", url=f"https://t.me/{OWNER_USERNAME}")]])
    )


async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        f"👑 <b>BOT OWNER</b>\n\nUsername: @{OWNER_USERNAME}\n"
        f"📢 Main channel: {CHANNELS[0]['url']}",
        parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    await update.effective_message.reply_text(
        f"⏱️ <b>UPTIME</b>\n\n{format_uptime(time.monotonic() - BOT_STARTED_AT)}",
        parse_mode=ParseMode.HTML
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    start_time = time.monotonic()
    msg = await update.effective_message.reply_text("🌐 Checking latency…")
    ms = (time.monotonic() - start_time) * 1000
    await msg.edit_text(f"⚡ <b>PONG!</b>\n\n🌐 Telegram response: <code>{ms:.0f} ms</code>", parse_mode=ParseMode.HTML)


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if OWNER_ID == 0 or update.effective_user.id != OWNER_ID:
        await update.effective_message.reply_text("⛔ Owner only.")
        return
    await update.effective_message.reply_text(f"👥 Registered users: {user_count()}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if OWNER_ID == 0 or update.effective_user.id != OWNER_ID:
        await update.effective_message.reply_text("⛔ Owner only.")
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text(
            "Use: kisi message ko reply karke /broadcast bhejein."
        )
        return
    sent = failed = 0
    status = await update.effective_message.reply_text("📣 Broadcast started…")
    for uid in all_user_ids():
        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=update.effective_chat.id,
                message_id=update.effective_message.reply_to_message.message_id
            )
            sent += 1
        except TelegramError:
            failed += 1
    await status.edit_text(f"📣 Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    text = update.effective_message.text
    mapping = {
        "🆔 MY ID": id_command,
        "ℹ️ ABOUT": about_command,
        "⚙️ COMMANDS": commands_command,
        "🛡️ STATUS": status_command,
        "💎 PREMIUM": premium_command,
        "💖 SUPPORT": support_command,
        "👑 OWNER": owner_command,
        "📢 CHANNEL": about_command,
    }
    handler = mapping.get(text)
    if handler:
        await handler(update, context)


async def post_init(app: Application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Help menu"),
        BotCommand("id", "Get your Telegram ID"),
        BotCommand("about", "About this bot"),
        BotCommand("commands", "Full command list"),
        BotCommand("status", "Bot status"),
        BotCommand("premium", "Premium info"),
        BotCommand("support", "Contact owner"),
        BotCommand("owner", "Owner info"),
        BotCommand("uptime", "Bot uptime"),
        BotCommand("ping", "Latency test"),
        BotCommand("users", "User count (owner only)"),
        BotCommand("broadcast", "Broadcast (owner only)"),
    ]
    await app.bot.set_my_commands(commands)


def main():
    if not BOT_TOKEN:
        raise SystemExit("ERROR: Add BOT_TOKEN to your private .env file or environment variables.")
    if OWNER_ID == 0:
        log.warning("OWNER_ID is 0. Set your numeric Telegram user ID to enable owner-only commands.")
    db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["help"], commands_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("commands", commands_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CommandHandler("uptime", uptime_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    log.info("JOY WEBS bot is starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
