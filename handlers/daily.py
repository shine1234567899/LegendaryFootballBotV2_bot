from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User, GameSetting


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "daily.jpg"
)

DAILY_REWARD = 100_000
DAILY_COOLDOWN = timedelta(hours=24)


async def _get_user(
    session,
    user_id: int,
):
    result = await session.execute(
        select(User).where(
            User.id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _get_last_claim(
    session,
    user_id: int,
):
    key = f"daily_claim:{user_id}"

    result = await session.execute(
        select(GameSetting).where(
            GameSetting.key == key
        )
    )

    setting = result.scalar_one_or_none()

    if setting is None:
        return None

    try:
        return datetime.fromisoformat(
            setting.value
        )
    except ValueError:
        return None


async def _save_last_claim(
    session,
    user_id: int,
    claimed_at: datetime,
):
    key = f"daily_claim:{user_id}"

    result = await session.execute(
        select(GameSetting).where(
            GameSetting.key == key
        )
    )

    setting = result.scalar_one_or_none()

    value = claimed_at.isoformat()

    if setting is None:
        session.add(
            GameSetting(
                key=key,
                value=value,
                description="Last daily reward claim.",
            )
        )
    else:
        setting.value = value


async def daily(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    telegram_user = update.effective_user

    if (
        message is None
        or telegram_user is None
    ):
        return

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        user = await _get_user(
            session,
            telegram_user.id,
        )

        if user is None:
            await message.reply_text(
                "❌ Your account was not found.\n"
                "Use /start first."
            )
            return

        last_claim = await _get_last_claim(
            session,
            telegram_user.id,
        )

        if last_claim is not None:
            if last_claim.tzinfo is None:
                last_claim = last_claim.replace(
                    tzinfo=timezone.utc
                )

            next_claim = (
                last_claim
                + DAILY_COOLDOWN
            )

            if now < next_claim:
                remaining = (
                    next_claim - now
                )

                total_seconds = int(
                    remaining.total_seconds()
                )

                hours = total_seconds // 3600
                minutes = (
                    total_seconds % 3600
                ) // 60

                await message.reply_photo(
                    photo=open(
                        IMAGE_FILE,
                        "rb",
                    ),
                    caption=(
                        "🎁 𝐃𝐀𝐈𝐋𝐘 𝐑𝐄𝐖𝐀𝐑𝐃\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        "⏳ You already claimed your "
                        "daily reward.\n\n"
                        f"🕒 Come back in "
                        f"{hours}h {minutes}m."
                    ),
                )
                return

        user.coins += DAILY_REWARD

        await _save_last_claim(
            session,
            telegram_user.id,
            now,
        )

        await session.commit()

        balance = user.coins

    await message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=(
            "🎁 𝐃𝐀𝐈𝐋𝐘 𝐑𝐄𝐖𝐀𝐑𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Daily reward claimed!\n\n"
            f"💰 +{DAILY_REWARD:,} Coins\n"
            f"💰 Balance : {balance:,} Coins\n\n"
            "⏳ Come back in 24 hours."
        ),
    )


daily_handler = CommandHandler(
    "daily",
    daily,
)