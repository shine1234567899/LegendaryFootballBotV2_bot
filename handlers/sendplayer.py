from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    User,
    Club,
    Player,
    ClubPlayer,
)


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "sendplayer.jpg"
)


async def _get_user_by_username(
    session,
    username: str,
):
    username = username.strip().lstrip("@")

    if not username:
        return None

    result = await session.execute(
        select(User).where(
            User.username.ilike(username)
        )
    )
    return result.scalar_one_or_none()


async def _get_club(
    session,
    owner_id: int,
):
    result = await session.execute(
        select(Club).where(
            Club.owner_id == owner_id
        )
    )
    return result.scalar_one_or_none()


async def _get_player_by_name(
    session,
    player_name: str,
):
    result = await session.execute(
        select(Player).where(
            Player.name.ilike(player_name.strip())
        )
    )
    return result.scalar_one_or_none()


async def sendplayer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if (
        message is None
        or owner is None
    ):
        return

    if owner.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    if len(context.args) < 2:
        await message.reply_text(
            (
                "⚽ 𝐒𝐄𝐍𝐃 𝐏𝐋𝐀𝐘𝐄𝐑\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/sendplayer @username Player Name\n\n"
                "Example:\n"
                "/sendplayer @manager Cristiano Ronaldo"
            )
        )
        return

    username = context.args[0]
    player_name = " ".join(
        context.args[1:]
    ).strip()

    if not player_name:
        await message.reply_text(
            "❌ Player name is required."
        )
        return

    async with AsyncSessionLocal() as session:
        target_user = await _get_user_by_username(
            session,
            username,
        )

        if target_user is None:
            await message.reply_text(
                "❌ User not found."
            )
            return

        target_club = await _get_club(
            session,
            target_user.id,
        )

        if target_club is None:
            await message.reply_text(
                "❌ This user has no club yet."
            )
            return

        player = await _get_player_by_name(
            session,
            player_name,
        )

        player_created = False

        # If the player does not exist yet, create him first,
        # then give him directly to the target club.
        if player is None:
            player = Player(
                name=player_name,
                country="Unknown",
                position="ST",
                age=18,
                overall=60,
                potential=70,
                value=60 * 60 * 5000,
                starter_pool=False,
            )

            session.add(player)
            await session.flush()

            player_created = True

        # Check whether the target already owns the player.
        target_ownership_result = await session.execute(
            select(ClubPlayer).where(
                ClubPlayer.club_id == target_club.id,
                ClubPlayer.player_id == player.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        if target_ownership_result.scalar_one_or_none() is not None:
            await message.reply_text(
                "❌ This club already owns this player."
            )
            return

        # A player can only be current in one club.
        current_owner_result = await session.execute(
            select(ClubPlayer).where(
                ClubPlayer.player_id == player.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        current_ownership = (
            current_owner_result.scalar_one_or_none()
        )

        if current_ownership is not None:
            current_ownership.is_current = False

        session.add(
            ClubPlayer(
                club_id=target_club.id,
                player_id=player.id,
                is_current=True,
            )
        )

        await session.commit()

        target_name = (
            f"@{target_user.username}"
            if target_user.username
            else target_user.first_name
            or f"User #{target_user.id}"
        )

    await message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=(
            "✅ 𝐏𝐋𝐀𝐘𝐄𝐑 𝐒𝐄𝐍𝐓\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Manager : {target_name}\n"
            f"🏟️ Club : {target_club.name}\n"
            f"⚽ Player : {player.name}\n"
            f"⭐ OVR : {player.overall}\n"
            f"{'🆕 Player created automatically.\n' if player_created else ''}"
            f"🌍 Country : {player.country}\n\n"
            "✅ Transfer completed by Owner."
        ),
    )


sendplayer_handler = CommandHandler(
    "sendplayer",
    sendplayer,
)