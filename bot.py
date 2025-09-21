# bot.py
import os
import re
import traceback
import base64
import requests
import logging
from typing import List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ---------- Configuration (from env) ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DUMP_CHAT_ID = os.getenv("DUMP_CHAT_ID", None)  # where errors will be sent (int or string)

if DUMP_CHAT_ID is None:
    # keep None — later code will attempt to notify admin if set, otherwise only logs locally
    pass

# ---------- Encoded API strings (copied from your script.py) ----------
ENCODED_API_URL = "aHR0cDovLzQ2LjYyLjEzNS4xMjU6NTAwMC9hcGkvbW9iaWxl"
ENCODED_API_KEY = "TmlraGlsZXNoVjI="

def decode_string(encoded_data: str) -> str:
    return base64.b64decode(encoded_data).decode("utf-8")

API_URL = decode_string(ENCODED_API_URL)
API_KEY = decode_string(ENCODED_API_KEY)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- UI Text ----------
START_TEXT = (
    "Welcome! 👋\n\n"
    "Send me a phone number (e.g. +919876543210 or 9876543210) and I'll look up the info.\n\n"
    "Choose an option below for more."
)
ABOUT_TEXT = (
    "About me:\n"
    "- This bot queries a lookup API and returns available info (name, address, circle, etc.).\n"
    "- Powered by the Nexus lookup tool.\n\n"
    "Privacy: This bot only forwards the query to the configured API and returns the result."
)
HELP_TEXT = (
    "How to use:\n"
    "1. Send a phone number in international or local format (digits, optional leading '+').\n"
    "2. If results exist they will appear here.\n\n"
    "Notes:\n- Use valid phone numbers only.\n- If something goes wrong the admin will be notified."
)

# Inline keyboards
def start_keyboard():
    keyboard = [
        [InlineKeyboardButton("About me", callback_data="about")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    keyboard = [[InlineKeyboardButton("⬅ Back", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)

# ---------- Helper: send error dump ----------
async def send_dump(context: ContextTypes.DEFAULT_TYPE, title: str, error_text: str):
    """Send error text to dump chat if configured; also log locally."""
    full = f"*{title}*\n```\n{error_text}\n```"
    logger.error("%s\n%s", title, error_text)
    if DUMP_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(DUMP_CHAT_ID),
                text=full,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception as e:
            # log but do not raise — avoid crash loop
            logger.exception("Failed to send dump message: %s", e)

# ---------- Lookup function (returns list of formatted strings) ----------
def lookup_phone(query: str) -> List[str]:
    """
    Query the API and return a list of result strings (formatted).
    Raises requests exceptions on network problems.
    """
    params = {"apikey": API_KEY, "query": query}
    resp = requests.get(API_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return []

    messages = []
    for idx, user in enumerate(data, 1):
        parts = [
            f"*Result {idx}*",
            f"• *Name:* {escape_md(user.get('name','Not Available'))}",
            f"• *Father's:* {escape_md(user.get('fname','Not Available'))}",
            f"• *Address:* {escape_md(user.get('address','Not Available').replace('!', ', '))}",
            f"• *Mobile:* `{escape_md(user.get('mobile','Not Available'))}`",
            f"• *Aadhaar:* {escape_md(user.get('id','Not Available'))}",
            f"• *Circle:* {escape_md(user.get('circle','Not Available'))}",
        ]
        footer = f"✺ Powered by Nexus | Credit: {escape_md(str(data[0].get('credit','No Credit')))}"
        messages.append("\n".join(parts) + "\n\n" + footer)
    return messages

# ---------- Markdown escaping helper for Telegram markdown v2 ----------
def escape_md(text: str) -> str:
    """
    Escape text for Telegram MarkdownV2; keep it simple and conservative.
    """
    if text is None:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f"\\{c}" if c in escape_chars else c for c in str(text))

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.effective_message.reply_text(
            START_TEXT,
            reply_markup=start_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as e:
        # send dump
        tb = traceback.format_exc()
        await send_dump(context, "Error in /start handler", tb)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "about":
            await query.edit_message_text(ABOUT_TEXT, reply_markup=back_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        elif data == "help":
            await query.edit_message_text(HELP_TEXT, reply_markup=back_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        elif data == "back":
            # return to start message
            await query.edit_message_text(START_TEXT, reply_markup=start_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await query.edit_message_text("Unknown action.", reply_markup=back_keyboard())
    except Exception as e:
        tb = traceback.format_exc()
        await send_dump(context, "Error in callback handler", tb)

PHONE_RE = re.compile(r"^\+?\d{7,15}$")

async def phone_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = (msg.text or "").strip()
    try:
        if not text:
            return
        if not PHONE_RE.match(text):
            await msg.reply_text("Please send a valid phone number (digits only, optional leading +).")
            return

        # Inform user we're working
        working_msg = await msg.reply_text("Looking up. Please wait...")

        # Do the lookup (blocking requests). This is OK for small scale.
        try:
            results = lookup_phone(text)
        except requests.exceptions.HTTPError as e:
            await working_msg.edit_text("Network error while contacting lookup API.")
            tb = traceback.format_exc()
            await send_dump(context, "HTTPError during lookup", tb)
            return
        except requests.exceptions.RequestException:
            await working_msg.edit_text("Network/connection error while contacting lookup API.")
            tb = traceback.format_exc()
            await send_dump(context, "RequestException during lookup", tb)
            return
        except ValueError:
            await working_msg.edit_text("Received an invalid response from the lookup API.")
            tb = traceback.format_exc()
            await send_dump(context, "ValueError during lookup", tb)
            return
        except Exception:
            await working_msg.edit_text("An unexpected error occurred during lookup.")
            tb = traceback.format_exc()
            await send_dump(context, "Unexpected exception during lookup", tb)
            return

        if not results:
            await working_msg.edit_text("No results found for that number.")
            return

        # Send results, split if too long
        for part in results:
            # Telegram message limit ~4096; we're using moderate text so safe.
            try:
                await msg.reply_text(part, parse_mode=ParseMode.MARKDOWN_V2)
            except Exception:
                # if formatting errors, send as plain
                await msg.reply_text(part)

        # remove the working message
        try:
            await working_msg.delete()
        except Exception:
            pass

    except Exception:
        tb = traceback.format_exc()
        await send_dump(context, "Error in phone_message_handler", tb)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("I didn't understand that. Send a phone number or /start.")

# ---------- Main ----------
def main():
    if BOT_TOKEN.startswith("YOUR_"):
        raise SystemExit("Set BOT_TOKEN env variable before running.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, phone_message_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))  # unknown commands

    logger.info("Bot started. Running polling...")
    app.run_polling()

if __name__ == "__main__":
    main()    query = console.input("[bold green]➤ Enter search query: [/]")
    search_user(query)
