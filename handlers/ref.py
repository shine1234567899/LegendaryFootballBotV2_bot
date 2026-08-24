from __future__ import annotations

from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from database.database import AsyncSessionLocal

IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "ref.jpg"
)

REF_REWARD = 1_000_000

def _ref_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS referrals (
                id BIGSERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL UNIQUE,
                reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        referral_count = await session.scalar(
            text("""
                SELECT COUNT(*)
                FROM referrals
                WHERE referrer_id = :user_id
            """),
            {"user_id": user.id},
        ) or 0

        await session.commit()

    bot_info = await context.bot.get_me()
    username = bot_info.username

    if not username:
        await message.reply_text("❌ The bot username is unavailable.")
        return

    link = _ref_link(username, user.id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 SHARE REFERRAL",
                url=(
                    "https://t.me/share/url"
                    f"?url={link}"
                    "&text=Join%20Legendary%20Football%20%F0%9F%8F%86"
                ),
            )
        ]
    ])

    await message.reply_photo(
        photo=open(IMAGE_FILE, "rb"),
        caption=(
            "🤝 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋 𝐒𝐘𝐒𝐓𝐄𝐌\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Invite your friends to Legendary Football.\n\n"
            f"🎁 Reward : +{REF_REWARD:,} Coins\n"
            f"👥 People invited : {int(referral_count)}\n"
            f"👤 Your referral code : `{user.id}`\n\n"
            "🔗 Your referral link:\n"
            f"{link}\n\n"
            "The reward is given only once when a new user "
            "registers through your link."
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

ref_handler = CommandHandler("ref", ref)