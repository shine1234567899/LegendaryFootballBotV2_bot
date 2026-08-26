from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
    TransferListing,
)


async def _manager_club(session, user_id: int):
    return await session.scalar(
        select(Club).where(Club.owner_id == user_id)
    )


async def _owned_player(session, club_id: int, player_name: str):
    result = await session.execute(
        select(ClubPlayer, Player)
        .join(Player, Player.id == ClubPlayer.player_id)
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(player_name.strip()),
        )
    )
    return result.first()


async def sell_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Put one of the manager's current players on the transfer market."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if len(context.args) < 2:
        await message.reply_text(
            "🔄 Usage:\n"
            "/sellplayer Player Name price\n\n"
            "Example:\n"
            "/sellplayer Cristiano Ronaldo 50000000"
        )
        return

    try:
        price = int(context.args[-1])
    except ValueError:
        await message.reply_text("❌ Price must be a number.")
        return

    player_name = " ".join(context.args[:-1]).strip()

    if not player_name or price <= 0:
        await message.reply_text("❌ Invalid player or price.")
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, user.id)

        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        owned = await _owned_player(
            session,
            club.id,
            player_name,
        )

        if owned is None:
            await message.reply_text(
                "❌ This player is not currently in your club."
            )
            return

        club_player, player = owned

        # A player already listed by this club cannot be listed twice.
        existing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.seller_club_id == club.id,
                TransferListing.status == "active",
            )
        )

        if existing is not None:
            await message.reply_text(
                "❌ This player is already listed."
            )
            return

        # A listed player must no longer count as current in the squad.
        club_player.is_current = False
        club_player.left_at = datetime.now(timezone.utc)

        # Disable the active contract while the player is on the market.
        contract = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club.id,
                PlayerContract.player_id == player.id,
                PlayerContract.active.is_(True),
            )
        )

        if contract is not None:
            contract.active = False

        listing = TransferListing(
            player_id=player.id,
            seller_club_id=club.id,
            price=price,
            currency="coins",
            status="active",
        )

        session.add(listing)
        await session.commit()

    await message.reply_text(
        "🔄 𝐏𝐋𝐀𝐘𝐄𝐑 𝐋𝐈𝐒𝐓𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ Player: {player.name}\n"
        f"💰 Asking price: {price:,} Coins\n"
        f"🏟️ Club: {club.name}\n\n"
        "📢 The player is now available on the transfer market."
    )


async def release_player(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Release a player without a transfer fee."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if not context.args:
        await message.reply_text(
            "❌ Usage:\n"
            "/releaseplayer Player Name"
        )
        return

    player_name = " ".join(context.args).strip()

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, user.id)

        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        owned = await _owned_player(
            session,
            club.id,
            player_name,
        )

        if owned is None:
            await message.reply_text(
                "❌ This player is not currently in your club."
            )
            return

        club_player, player = owned
        now = datetime.now(timezone.utc)

        club_player.is_current = False
        club_player.left_at = now

        contract = await session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club.id,
                PlayerContract.player_id == player.id,
                PlayerContract.active.is_(True),
            )
        )

        if contract is not None:
            contract.active = False

        # If there is already an active listing, leave it alone.
        # Otherwise create a normal-value listing.
        listing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.status == "active",
            )
        )

        if listing is None:
            session.add(
                TransferListing(
                    player_id=player.id,
                    seller_club_id=None,
                    price=max(int(player.value or 0), 1),
                    currency="coins",
                    status="active",
                )
            )

        await session.commit()

    await message.reply_text(
        "❌ 𝐏𝐋𝐀𝐘𝐄𝐑 𝐑𝐄𝐋𝐄𝐀𝐒𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ Player: {player.name}\n"
        f"💰 Market value: {player.value:,} Coins\n\n"
        "🔄 The player has been released and placed on the market."
    )


async def my_transfers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Show the manager's active listings."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, user.id)

        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        result = await session.execute(
            select(TransferListing, Player)
            .join(Player, Player.id == TransferListing.player_id)
            .where(
                TransferListing.seller_club_id == club.id,
                TransferListing.status == "active",
            )
            .order_by(Player.name)
        )

        rows = result.all()

    if not rows:
        await message.reply_text(
            "🔄 Your club has no active transfer listings."
        )
        return

    text = (
        "🔄 𝐌𝐘 𝐓𝐑𝐀𝐍𝐒𝐅𝐄𝐑𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for listing, player in rows:
        text += (
            f"⚽ {player.name}\n"
            f"💰 {listing.price:,} {listing.currency.upper()}\n\n"
        )

    await message.reply_text(text)


sellplayer_handler = CommandHandler(
    "sellplayer",
    sell_player,
)

releaseplayer_handler = CommandHandler(
    "releaseplayer",
    release_player,
)

mytransfers_handler = CommandHandler(
    "mytransfers",
    my_transfers,
)
