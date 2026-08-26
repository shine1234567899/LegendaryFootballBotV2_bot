from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
    TransferListing,
)


# ==========================================================
# HELPERS
# ==========================================================

async def _manager_club(session, user_id: int):
    return await session.scalar(
        select(Club).where(
            Club.owner_id == user_id
        )
    )


async def _owned_player(
    session,
    club_id: int,
    player_name: str,
):
    """
    Find one CURRENT player owned by the club.

    Exact name is preferred. If there is no exact match, a partial
    match is allowed, but ambiguous partial matches are rejected instead
    of silently selecting the first player.
    """
    name = " ".join(player_name.strip().split())

    if not name:
        return None

    exact = await session.execute(
        select(ClubPlayer, Player)
        .join(
            Player,
            Player.id == ClubPlayer.player_id,
        )
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(name),
        )
    )

    exact_row = exact.first()
    if exact_row is not None:
        return exact_row

    partial = await session.execute(
        select(ClubPlayer, Player)
        .join(
            Player,
            Player.id == ClubPlayer.player_id,
        )
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(f"%{name}%"),
        )
        .order_by(
            Player.overall.desc(),
            Player.name.asc(),
        )
    )

    rows = list(partial.all())

    if len(rows) == 1:
        return rows[0]

    # Never pick an arbitrary player when multiple names match.
    return None


# ==========================================================
# SELL PLAYER
# ==========================================================

async def sell_player(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    List one current squad player on the Transfer Market.

    Usage:
        /sellplayer Player Name PRICE

    Important:
        TransferMarket uses status='available' for listings.
        The previous manager handler used 'active', which meant
        the listing was invisible to the market and /mytransfers.
    """
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if len(context.args) < 2:
        await message.reply_text(
            "🔄 𝐒𝐄𝐋𝐋 𝐏𝐋𝐀𝐘𝐄𝐑\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Usage:\n"
            "/sellplayer Player Name Price\n\n"
            "Example:\n"
            "/sellplayer Cristiano Ronaldo 50000000"
        )
        return

    raw_price = context.args[-1]

    try:
        price = int(raw_price)
    except (TypeError, ValueError):
        await message.reply_text(
            "❌ The price must be a whole number."
        )
        return

    if price <= 0:
        await message.reply_text(
            "❌ The price must be greater than 0."
        )
        return

    player_name = " ".join(
        context.args[:-1]
    ).strip()

    if not player_name:
        await message.reply_text(
            "❌ Player name is missing."
        )
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(
            session,
            user.id,
        )

        if club is None:
            await message.reply_text(
                "❌ You don't have a club."
            )
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

        # Do not allow duplicate active/available listings.
        existing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.seller_club_id == club.id,
                TransferListing.status.in_(
                    ["available", "active"]
                ),
            )
        )

        if existing is not None:
            await message.reply_text(
                "❌ This player is already listed."
            )
            return

        # Also prevent a second listing for the same player
        # from another source.
        global_existing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.status.in_(
                    ["available", "active"]
                ),
            )
        )

        if global_existing is not None:
            await message.reply_text(
                "❌ This player is already on the Transfer Market."
            )
            return

        now = datetime.now(timezone.utc)

        # Create the listing FIRST.
        # The player remains in the club until another manager actually
        # buys the listing. This prevents failed listings from removing
        # players from the squad.
        listing = TransferListing(
            player_id=player.id,
            seller_club_id=club.id,
            price=price,
            currency="coins",
            status="available",
        )

        session.add(listing)
        await session.commit()

    await message.reply_text(
        "🔄 𝐏𝐋𝐀𝐘𝐄𝐑 𝐋𝐈𝐒𝐓𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ Player: {player.name}\n"
        f"⭐ Overall: {player.overall}\n"
        f"💰 Asking price: {price:,} Coins\n"
        f"🏟️ Club: {club.name}\n\n"
        "📢 The player is now available on the Transfer Market."
    )


# ==========================================================
# RELEASE PLAYER
# ==========================================================

async def release_player(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Put a player on the Transfer Market at his normal market value.
    """
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

    player_name = " ".join(
        context.args
    ).strip()

    async with AsyncSessionLocal() as session:
        club = await _manager_club(
            session,
            user.id,
        )

        if club is None:
            await message.reply_text(
                "❌ You don't have a club."
            )
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

        # Check for an existing market listing before changing ownership.
        existing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.status.in_(
                    ["available", "active"]
                ),
            )
        )

        if existing is not None:
            await message.reply_text(
                "❌ This player is already on the Transfer Market."
            )
            return

        market_value = max(
            int(player.value or 0),
            1,
        )

        # Create the release listing first.
        # Ownership is preserved until the market transaction actually
        # completes. This prevents a failed release from removing the
        # player from the squad.
        session.add(
            TransferListing(
                player_id=player.id,
                seller_club_id=None,
                price=market_value,
                currency="coins",
                status="available",
            )
        )

        await session.commit()

    await message.reply_text(
        "❌ 𝐏𝐋𝐀𝐘𝐄𝐑 𝐑𝐄𝐋𝐄𝐀𝐒𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ Player: {player.name}\n"
        f"⭐ Overall: {player.overall}\n"
        f"💰 Market value: {market_value:,} Coins\n\n"
        "🔄 The player has been released and placed on the market."
    )


# ==========================================================
# MY TRANSFERS
# ==========================================================

async def my_transfers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Show all active listings belonging to this manager."""
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(
            session,
            user.id,
        )

        if club is None:
            await message.reply_text(
                "❌ You don't have a club."
            )
            return

        result = await session.execute(
            select(
                TransferListing,
                Player,
            )
            .join(
                Player,
                Player.id == TransferListing.player_id,
            )
            .where(
                TransferListing.seller_club_id == club.id,
                TransferListing.status.in_(
                    ["available", "active"]
                ),
            )
            .order_by(
                Player.name.asc()
            )
        )

        rows = result.all()

    if not rows:
        await message.reply_text(
            "🔄 𝐌𝐘 𝐓𝐑𝐀𝐍𝐒𝐅𝐄𝐑𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📭 You have no active players on the market."
        )
        return

    lines = [
        "🔄 𝐌𝐘 𝐓𝐑𝐀𝐍𝐒𝐅𝐄𝐑𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for index, (listing, player) in enumerate(
        rows,
        start=1,
    ):
        lines.extend(
            [
                f"{index}. ⚽ {player.name}",
                f"   ⭐ OVR: {player.overall}",
                f"   💰 {listing.price:,} Coins",
                "",
            ]
        )

    await message.reply_text(
        "\n".join(lines)
    )


# ==========================================================
# HANDLERS
# ==========================================================

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
