from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import text

from database.database import AsyncSessionLocal

REF_REWARD = 1_000_000

async def process_start_referral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    telegram_user = update.effective_user

    if message is None or telegram_user is None:
        return

    # Only /start ref_<user_id>
    args = getattr(context, "args", None) or []
    if not args or not str(args[0]).startswith("ref_"):
        return

    try:
        referrer_id = int(str(args[0])[4:])
    except (TypeError, ValueError):
        return

    referred_id = int(telegram_user.id)

    if referrer_id == referred_id:
        return

    # Let the normal /start handler create the user first.
    await asyncio.sleep(0.5)

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

        # Both accounts must exist.
        exists = (
            await session.execute(
                text("""
                    SELECT
                        EXISTS(SELECT 1 FROM users WHERE id = :referrer_id),
                        EXISTS(SELECT 1 FROM users WHERE id = :referred_id)
                """),
                {
                    "referrer_id": referrer_id,
                    "referred_id": referred_id,
                },
            )
        ).first()

        if not exists or not exists[0] or not exists[1]:
            await session.rollback()
            return

        # One referred account can only reward one referrer once.
        inserted = (
            await session.execute(
                text("""
                    INSERT INTO referrals
                        (referrer_id, referred_id, reward_claimed)
                    VALUES
                        (:referrer_id, :referred_id, TRUE)
                    ON CONFLICT (referred_id) DO NOTHING
                    RETURNING id
                """),
                {
                    "referrer_id": referrer_id,
                    "referred_id": referred_id,
                },
            )
        ).scalar_one_or_none()

        if inserted is None:
            await session.rollback()
            return

        await session.execute(
            text("""
                UPDATE users
                SET coins = COALESCE(coins, 0) + :reward
                WHERE id = :referrer_id
            """),
            {
                "reward": REF_REWARD,
                "referrer_id": referrer_id,
            },
        )

        await session.commit()

        try:
            await message.reply_text(
                "🎉 Welcome to Legendary Football!\n"
                "Your referral has been registered successfully."
            )
        except Exception:
            pass

async def referral_start_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    if message is None or not message.text:
        return

    command = message.text.split(maxsplit=1)[0].split("@", 1)[0].lower()
    if command != "/start":
        return

    context.application.create_task(
        process_start_referral(update, context),
        update=update,
    )