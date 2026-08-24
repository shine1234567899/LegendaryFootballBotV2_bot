from __future__ import annotations

from pathlib import Path

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User
IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "ref.jpg"
)


REF_REWARD = 1_000_000


def _ref_link(
    bot_username: str,
    user_id: int,
) -> str:
    return (
        f"https://t.me/{bot_username}"
        f"?start=ref_{user_id}"
    )


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


async def ref(
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

    async with AsyncSessionLocal() as session:
        db_user = await _get_user(
            session,
            user.id,
        )

    if db_user is None:
        await message.reply_text(
            "❌ Your account was not found.\n"
            "Use /start first."
        )
        return

    bot = context.bot
    bot_info = await bot.get_me()

    username = bot_info.username

    if not username:
        await message.reply_text(
            "❌ The bot username is unavailable."
        )
        return

    link = _ref_link(
        username,
        user.id,
    )

    keyboard = InlineKeyboardMarkup(
        [
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
        ]
    )

    await message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=(
            "🤝 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋 𝐒𝐘𝐒𝐓𝐄𝐌\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Invite your friends to Legendary Football.\n\n"
            f"🎁 Reward : +{REF_REWARD:,} Coins\n"
            "👤 Your referral code : "
            f"`{user.id}`\n\n"
            "🔗 <b>Your referral link:</b>\n"
            f'<a href="{link}">{link}</a>\n\n'
            "The reward system is linked to the "
            "new player's first registration."
        ),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


ref_handler = CommandHandler(
    "ref",
    ref,
)