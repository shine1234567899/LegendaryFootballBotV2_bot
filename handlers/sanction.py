from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import GameSetting


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "sanction.jpg"
)


# ==========================================================
# SANCTION
# ==========================================================
#
# Owner-only command.
#
# The current database model does not expose a dedicated
# sanctions table/fields in the files provided so far.
# Therefore this command stores sanctions in GameSetting
# without changing the existing User/Club schema.
#
# Usage:
#
# /sanction <user_id> <reason>
#
# Example:
# /sanction 123456789 cheating
#
# This creates/updates:
#   sanction:<user_id>
#
# Stored value:
#   ISO timestamp | reason
#
# This is intentionally a recording system. Enforcement
# (blocking commands/matches/etc.) can be connected later.
# ==========================================================


async def _get_setting(
    session,
    key: str,
):
    from sqlalchemy import select

    result = await session.execute(
        select(GameSetting).where(
            GameSetting.key == key
        )
    )

    return result.scalar_one_or_none()


async def sanction(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if (
        message is None
        or user is None
    ):
        return

    # OWNER ONLY
    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    if len(context.args) < 2:
        await message.reply_text(
            (
                "⚠️ 𝐒𝐀𝐍𝐂𝐓𝐈𝐎𝐍\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/sanction <user_id> <reason>\n\n"
                "Example:\n"
                "/sanction 123456789 cheating"
            )
        )
        return

    try:
        target_user_id = int(
            context.args[0]
        )
    except ValueError:
        await message.reply_text(
            "❌ Invalid user ID."
        )
        return

    reason = " ".join(
        context.args[1:]
    ).strip()

    if not reason:
        await message.reply_text(
            "❌ A reason is required."
        )
        return

    now = datetime.now(
        timezone.utc
    )

    key = f"sanction:{target_user_id}"

    async with AsyncSessionLocal() as session:
        setting = await _get_setting(
            session,
            key,
        )

        value = (
            f"{now.isoformat()} | {reason}"
        )

        if setting is None:
            setting = GameSetting(
                key=key,
                value=value,
                description="Owner sanction record.",
            )
            session.add(setting)
        else:
            setting.value = value

        await session.commit()

    if IMAGE_FILE.exists():
        await message.reply_photo(
            photo=open(
                IMAGE_FILE,
                "rb",
            ),
            caption=(
                "🔨 𝐒𝐀𝐍𝐂𝐓𝐈𝐎𝐍\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 User ID : {target_user_id}\n"
                f"📝 Reason : {reason}\n"
                f"🕒 Date : "
                f"{now.strftime('%d/%m/%Y %H:%M UTC')}\n\n"
                "✅ Sanction recorded."
            ),
        )
    else:
        await message.reply_text(
            (
                "🔨 𝐒𝐀𝐍𝐂𝐓𝐈𝐎𝐍\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 User ID : {target_user_id}\n"
                f"📝 Reason : {reason}\n"
                "✅ Sanction recorded."
            )
        )


sanction_handler = CommandHandler(
    "sanction",
    sanction,
)