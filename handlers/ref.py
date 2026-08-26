from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

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


async def _ensure_referrals_table(session):
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS referrals (
            id BIGSERIAL PRIMARY KEY,
            referrer_id BIGINT NOT NULL,
            referred_id BIGINT NOT NULL UNIQUE,
            reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))


async def process_referral_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Record /start ref_<user_id>.

    IMPORTANT:
    No reward is paid here. The reward is paid only after the
    referred user successfully creates a club.
    """
    user = update.effective_user
    if user is None or not context.args:
        return False

    payload = str(context.args[0]).strip()

    if not payload.startswith("ref_"):
        return False

    try:
        referrer_id = int(payload[4:])
    except (TypeError, ValueError):
        return False

    if referrer_id <= 0 or referrer_id == user.id:
        return False

    async with AsyncSessionLocal() as session:
        await _ensure_referrals_table(session)

        # The referred user does NOT need to exist in users yet.
        # /createclub will create that row later.
        referrer_exists = await session.scalar(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM users WHERE id = :uid
                )
            """),
            {"uid": referrer_id},
        )

        if not referrer_exists:
            await session.commit()
            return True

        # One referred Telegram account can only belong to one referrer.
        await session.execute(
            text("""
                INSERT INTO referrals (
                    referrer_id,
                    referred_id,
                    reward_claimed
                )
                VALUES (
                    :referrer_id,
                    :referred_id,
                    FALSE
                )
                ON CONFLICT (referred_id) DO NOTHING
            """),
            {
                "referrer_id": referrer_id,
                "referred_id": user.id,
            },
        )

        await session.commit()

    return True


async def reward_referral_for_club_creation(
    session,
    referred_id: int,
    reward: int = REF_REWARD,
) -> int | None:
    """
    Pay the referrer when `referred_id` successfully creates a club.

    Returns the referrer_id when a reward was paid, otherwise None.

    This function is called BEFORE the club transaction commits, so a
    failed club creation does not permanently grant the reward.
    """
    await _ensure_referrals_table(session)

    row = (
        await session.execute(
            text("""
                SELECT id, referrer_id
                FROM referrals
                WHERE referred_id = :referred_id
                  AND reward_claimed = FALSE
                LIMIT 1
                FOR UPDATE
            """),
            {"referred_id": referred_id},
        )
    ).first()

    if row is None:
        return None

    referral_id = int(row.id)
    referrer_id = int(row.referrer_id)

    # Never reward self-referrals.
    if referrer_id == referred_id:
        return None

    # Referrer must still exist.
    referrer_exists = await session.scalar(
        text("""
            SELECT EXISTS(
                SELECT 1 FROM users WHERE id = :uid
            )
        """),
        {"uid": referrer_id},
    )

    if not referrer_exists:
        return None

    # Atomic claim: protects against double reward.
    claimed = await session.execute(
        text("""
            UPDATE referrals
            SET reward_claimed = TRUE
            WHERE id = :referral_id
              AND reward_claimed = FALSE
        """),
        {"referral_id": referral_id},
    )

    if claimed.rowcount != 1:
        return None

    await session.execute(
        text("""
            UPDATE users
            SET coins = COALESCE(coins, 0) + :reward
            WHERE id = :referrer_id
        """),
        {
            "reward": int(reward),
            "referrer_id": referrer_id,
        },
    )

    return referrer_id


async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        await _ensure_referrals_table(session)

        referral_count = await session.scalar(
            text("""
                SELECT COUNT(*)
                FROM referrals
                WHERE referrer_id = :user_id
                  AND reward_claimed = TRUE
            """),
            {"user_id": user.id},
        ) or 0

        pending_count = await session.scalar(
            text("""
                SELECT COUNT(*)
                FROM referrals
                WHERE referrer_id = :user_id
                  AND reward_claimed = FALSE
            """),
            {"user_id": user.id},
        ) or 0

        await session.commit()

    bot_info = await context.bot.get_me()
    username = bot_info.username

    if not username:
        await message.reply_text(
            "❌ The bot username is unavailable."
        )
        return

    link = _ref_link(username, user.id)

    share_url = (
        "https://t.me/share/url"
        f"?url={quote(link, safe='')}"
        f"&text={quote('Join Legendary Football 🏆', safe='')}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 SHARE REFERRAL",
                url=share_url,
            )
        ]
    ])

    with open(IMAGE_FILE, "rb") as photo:
        await message.reply_photo(
            photo=photo,
            caption=(
                "🤝 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋 𝐒𝐘𝐒𝐓𝐄𝐌\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Invite your friends to Legendary Football.\n\n"
                f"🎁 Reward : +{REF_REWARD:,} Coins\n"
                f"👥 Clubs created : {int(referral_count)}\n"
                f"⏳ Pending : {int(pending_count)}\n"
                f"👤 Your referral ID : `{user.id}`\n\n"
                "🔗 Your referral link:\n"
                f"`{link}`\n\n"
                "🎁 The reward is given when a NEW user "
                "successfully creates their club."
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


ref_handler = CommandHandler("ref", ref)
