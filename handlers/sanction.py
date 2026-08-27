from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import GameSetting, User


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "sanction.jpg"
)


async def _get_setting(session, key: str):
    result = await session.execute(
        select(GameSetting).where(GameSetting.key == key)
    )
    return result.scalar_one_or_none()


async def sanction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    owner = update.effective_user

    if message is None or owner is None:
        return

    if owner.id not in OWNER_IDS:
        await message.reply_text("⛔ This command is Owner only.")
        return

    # /sanction <user_id> <amount> <reason>
    if len(context.args) < 2:
        await message.reply_text(
            "⚠️ Usage:\n/sanction <user_id> <amount> [reason]\n\n"
            "Example:\n/sanction 123456789 50000 cheating"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await message.reply_text("❌ User ID and amount must be numbers.")
        return

    if amount <= 0:
        await message.reply_text("❌ The fine must be greater than 0.")
        return

    reason = " ".join(context.args[2:]).strip() or "No reason specified"
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        target = await session.get(User, target_id)
        if target is None:
            await message.reply_text("❌ User not found.")
            return

        key = f"sanction:{target_id}"
        setting = await _get_setting(session, key)
        value = f"{amount}|{reason}|{now.isoformat()}"

        if setting is None:
            session.add(GameSetting(
                key=key,
                value=value,
                description="Active owner fine; all commands blocked until paid.",
            ))
        else:
            setting.value = value

        await session.commit()

    # Notify the sanctioned user in DM.
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🔨 𝐘𝐎𝐔 𝐇𝐀𝐕𝐄 𝐁𝐄𝐄𝐍 𝐒𝐀𝐍𝐂𝐓𝐈𝐎𝐍𝐄𝐃\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Fine: {amount:,} Coins\n"
                f"📝 Reason: {reason}\n\n"
                "🚫 Your bot commands are blocked.\n"
                "💳 Pay your fine to restore access."
            ),
        )
    except Exception:
        pass

    await message.reply_text(
        f"✅ Sanction applied to {target_id}.\n"
        f"💰 Fine: {amount:,} Coins\n"
        f"📝 Reason: {reason}\n"
        "🚫 Commands blocked until payment."
    )


async def payfine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    key = f"sanction:{user.id}"

    async with AsyncSessionLocal() as session:
        setting = await _get_setting(session, key)
        if setting is None:
            await message.reply_text("✅ You have no active fine.")
            return

        try:
            amount_str, reason, created_at = setting.value.split("|", 2)
            amount = int(amount_str)
        except Exception:
            await message.reply_text("❌ Your sanction record is invalid.")
            return

        target = await session.get(User, user.id)
        if target is None:
            await message.reply_text("❌ User account not found.")
            return

        if int(target.coins or 0) < amount:
            await message.reply_text(
                f"❌ Not enough Coins.\n"
                f"💰 Fine: {amount:,}\n"
                f"💵 Your balance: {int(target.coins or 0):,}"
            )
            return

        target.coins -= amount
        await session.delete(setting)
        await session.commit()

    await message.reply_text(
        "✅ 𝐅𝐈𝐍𝐄 𝐏𝐀𝐈𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Paid: {amount:,} Coins\n"
        "🔓 Your bot access has been restored."
    )


async def sanction_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block commands for sanctioned users, except /payfine."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    if not message.text or not message.text.startswith("/"):
        return

    command = message.text.split()[0].split("@", 1)[0].lower()
    if command in ("/payfine", "/sanction"):
        return

    async with AsyncSessionLocal() as session:
        setting = await _get_setting(session, f"sanction:{user.id}")

    if setting is None:
        return

    try:
        amount, reason, _ = setting.value.split("|", 2)
    except Exception:
        amount = "unknown"

    await message.reply_text(
        "🚫 𝐀𝐂𝐂𝐄𝐒𝐒 𝐁𝐋𝐎𝐂𝐊𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Fine due: {amount} Coins\n"
        "💳 Use /payfine to pay your fine."
    )


sanction_handler = CommandHandler("sanction", sanction)
payfine_handler = CommandHandler("payfine", payfine)

# IMPORTANT:
# Register this handler BEFORE normal CommandHandlers in the same group.
# It intercepts commands from sanctioned users and lets /payfine through.
sanction_guard_handler = MessageHandler(
    filters.COMMAND,
    sanction_guard,
)

