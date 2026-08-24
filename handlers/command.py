from __future__ import annotations

from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from database.database import AsyncSessionLocal

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS command_usage (
    user_id BIGINT PRIMARY KEY,
    command_count INTEGER NOT NULL DEFAULT 0,
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

async def ensure_command_usage_table() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text(TABLE_SQL))
        await session.commit()

async def count_command_usage(user_id: int) -> int:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        await session.execute(text(TABLE_SQL))

        row = (
            await session.execute(
                text("""
                    SELECT command_count, window_started_at
                    FROM command_usage
                    WHERE user_id = :user_id
                    FOR UPDATE
                """),
                {"user_id": user_id},
            )
        ).first()

        if row is None:
            count = 1
            await session.execute(
                text("""
                    INSERT INTO command_usage
                        (user_id, command_count, window_started_at)
                    VALUES (:user_id, 1, :now)
                """),
                {"user_id": user_id, "now": now},
            )
        else:
            previous_count, started_at = row
            if started_at is None or now - started_at >= timedelta(hours=24):
                count = 1
                await session.execute(
                    text("""
                        UPDATE command_usage
                        SET command_count = 1,
                            window_started_at = :now
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id, "now": now},
                )
            else:
                count = int(previous_count) + 1
                await session.execute(
                    text("""
                        UPDATE command_usage
                        SET command_count = command_count + 1
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id},
                )

        await session.commit()
        return count

async def command_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    count = await count_command_usage(user.id)
    await message.reply_text(
        "📊 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐂𝐎𝐔𝐍𝐓𝐄𝐑\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {user.first_name or 'Manager'}\n"
        f"⚡ Commands used: {count}\n"
        "⏳ The counter resets 24 hours after its window starts."
    )

command_handler = CommandHandler("command", command_usage)