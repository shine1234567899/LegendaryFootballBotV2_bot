from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    PlayerContract,
    TransferListing,
    SavedLineup,
    SavedLineupPlayer,
)


async def _manager_club(session, user_id: int):
    return await session.scalar(
        select(Club).where(Club.owner_id == user_id)
    )


async def _owned_player(session, club_id: int, player_name: str):
    name = " ".join(player_name.strip().split())
    if not name:
        return None

    exact = await session.execute(
        select(ClubPlayer, Player)
        .join(Player, Player.id == ClubPlayer.player_id)
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(name),
        )
    )
    row = exact.first()
    if row is not None:
        return row

    partial = await session.execute(
        select(ClubPlayer, Player)
        .join(Player, Player.id == ClubPlayer.player_id)
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
            Player.name.ilike(f"%{name}%"),
        )
        .order_by(Player.overall.desc(), Player.name.asc())
    )
    rows = list(partial.all())
    return rows[0] if len(rows) == 1 else None


async def sell_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    if len(context.args) < 2:
        await message.reply_text(
            "🔄 𝐒𝐄𝐋𝐋 𝐏𝐋𝐀𝐘𝐄𝐑\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Usage:\n/sellplayer Player Name PRICE"
        )
        return

    try:
        price = int(context.args[-1])
    except (TypeError, ValueError):
        await message.reply_text("❌ The price must be a whole number.")
        return

    if price <= 0:
        await message.reply_text("❌ The price must be greater than 0.")
        return

    player_name = " ".join(context.args[:-1]).strip()

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, user.id)
        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        owned = await _owned_player(session, club.id, player_name)
        if owned is None:
            await message.reply_text(
                "❌ This player is not currently in your club."
            )
            return

        _, player = owned

        existing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.status.in_(["available", "active"]),
            )
        )
        if existing is not None:
            await message.reply_text(
                "❌ This player is already on the Transfer Market."
            )
            return

        session.add(
            TransferListing(
                player_id=player.id,
                seller_club_id=club.id,
                price=price,
                currency="coins",
                status="available",
            )
        )
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


async def _release_now(
    session,
    club,
    player,
):
    now = datetime.now(timezone.utc)

    ownership = await session.scalar(
        select(ClubPlayer).where(
            ClubPlayer.club_id == club.id,
            ClubPlayer.player_id == player.id,
            ClubPlayer.is_current.is_(True),
        )
    )
    if ownership is None:
        return False, "❌ This player is no longer in your club."

    existing = await session.scalar(
        select(TransferListing).where(
            TransferListing.player_id == player.id,
            TransferListing.status.in_(["available", "active"]),
        )
    )
    if existing is not None:
        return False, "❌ This player is already on the Transfer Market."

    # Release ownership.
    ownership.is_current = False
    ownership.left_at = now

    # Remove the player from every saved lineup of this club.
    lineup_result = await session.execute(
        select(SavedLineup.id).where(
            SavedLineup.club_id == club.id
        )
    )
    lineup_ids = [row[0] for row in lineup_result.all()]

    if lineup_ids:
        await session.execute(
            SavedLineupPlayer.__table__.delete().where(
                SavedLineupPlayer.saved_lineup_id.in_(lineup_ids),
                SavedLineupPlayer.player_id == player.id,
            )
        )

    # Disable active contract.
    contracts = await session.execute(
        select(PlayerContract).where(
            PlayerContract.club_id == club.id,
            PlayerContract.player_id == player.id,
            PlayerContract.active.is_(True),
        )
    )
    for contract in contracts.scalars().all():
        contract.active = False

    market_value = max(int(player.value or 0), 1)

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
    return True, market_value


async def release_player(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, user.id)
        if club is None:
            await message.reply_text("❌ You don't have a club.")
            return

        # Direct form: /releaseplayer Yamal
        if context.args:
            player_name = " ".join(context.args).strip()
            owned = await _owned_player(session, club.id, player_name)

            if owned is None:
                await message.reply_text(
                    "❌ This player is not currently in your club."
                )
                return

            _, player = owned

            await message.reply_text(
                "⚠️ 𝐂𝐎𝐍𝐅𝐈𝐑𝐌 𝐑𝐄𝐋𝐄𝐀𝐒𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"⚽ {player.name}\n"
                f"⭐ Overall: {player.overall}\n"
                f"🏟️ {club.name}\n\n"
                "This will remove the player from your squad and lineup."
                "\n\nAre you sure?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ RELEASE",
                            callback_data=f"release_confirm:{player.id}",
                        ),
                        InlineKeyboardButton(
                            "❌ CANCEL",
                            callback_data="release_cancel",
                        ),
                    ]
                ]),
            )
            return

        # Interactive form: /releaseplayer -> clickable squad list.
        result = await session.execute(
            select(ClubPlayer, Player)
            .join(Player, Player.id == ClubPlayer.player_id)
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
            .order_by(Player.overall.desc(), Player.name.asc())
        )
        rows = result.all()

    if not rows:
        await message.reply_text("📭 Your squad has no players.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"⚽ {player.name} • ⭐ {player.overall}",
                callback_data=f"release_select:{player.id}",
            )
        ]
        for _, player in rows
    ]
    keyboard.append([
        InlineKeyboardButton(
            "❌ CLOSE",
            callback_data="release_cancel",
        )
    ])

    await message.reply_text(
        "❌ 𝐑𝐄𝐋𝐄𝐀𝐒𝐄 𝐏𝐋𝐀𝐘𝐄𝐑\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Select the player you want to release:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )



async def release_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    data = query.data or ""
    if data == "release_cancel":
        await query.edit_message_text("❌ Release cancelled.")
        return

    if ":" not in data:
        return

    action, raw_id = data.split(":", 1)
    if action not in {"release_select", "release_confirm"}:
        return

    try:
        player_id = int(raw_id)
    except ValueError:
        await query.edit_message_text("❌ Invalid player.")
        return

    async with AsyncSessionLocal() as session:
        club = await _manager_club(session, query.from_user.id)
        if club is None:
            await query.edit_message_text("❌ You don't have a club.")
            return

        player = await session.get(Player, player_id)
        if player is None:
            await query.edit_message_text("❌ Player not found.")
            return

        ownership = await session.scalar(
            select(ClubPlayer).where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.player_id == player.id,
                ClubPlayer.is_current.is_(True),
            )
        )
        if ownership is None:
            await query.edit_message_text(
                "❌ This player is no longer in your squad."
            )
            return

        if action == "release_select":
            await query.edit_message_text(
                "⚠️ 𝐂𝐎𝐍𝐅𝐈𝐑𝐌 𝐑𝐄𝐋𝐄𝐀𝐒𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"⚽ {player.name}\n"
                f"⭐ Overall: {player.overall}\n"
                f"🏟️ {club.name}\n\n"
                "Are you sure you want to release this player?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ RELEASE",
                            callback_data=f"release_confirm:{player.id}",
                        ),
                        InlineKeyboardButton(
                            "❌ CANCEL",
                            callback_data="release_cancel",
                        ),
                    ]
                ]),
            )
            return

        now = datetime.now(timezone.utc)
        ownership.is_current = False
        ownership.left_at = now

        lineup_rows = await session.execute(
            select(SavedLineup.id).where(
                SavedLineup.club_id == club.id
            )
        )
        lineup_ids = [row[0] for row in lineup_rows.all()]

        if lineup_ids:
            await session.execute(
                SavedLineupPlayer.__table__.delete().where(
                    SavedLineupPlayer.saved_lineup_id.in_(lineup_ids),
                    SavedLineupPlayer.player_id == player.id,
                )
            )

        contracts = await session.execute(
            select(PlayerContract).where(
                PlayerContract.club_id == club.id,
                PlayerContract.player_id == player.id,
                PlayerContract.active.is_(True),
            )
        )
        for contract in contracts.scalars().all():
            contract.active = False

        market_value = max(int(player.value or 0), 1)

        listing = await session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == player.id,
                TransferListing.status.in_(["available", "active"]),
            )
        )

        # player_id is UNIQUE in transfer_listings, so never INSERT a
        # second row for a player who already has a sold/old listing.
        if listing is None:
            listing = await session.scalar(
                select(TransferListing).where(
                    TransferListing.player_id == player.id
                )
            )

        if listing is None:
            listing = TransferListing(
                player_id=player.id,
                seller_club_id=None,
                price=market_value,
                currency="coins",
                status="available",
            )
            session.add(listing)
        else:
            listing.seller_club_id = None
            listing.price = market_value
            listing.currency = "coins"
            listing.status = "available"
            listing.listed_at = now
            listing.sold_at = None

        await session.commit()

    await query.edit_message_text(
        "❌ 𝐏𝐋𝐀𝐘𝐄𝐑 𝐑𝐄𝐋𝐄𝐀𝐒𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ {player.name}\n"
        f"⭐ Overall: {player.overall}\n"
        f"💰 Market value: {market_value:,} Coins\n\n"
        "✅ Removed from the squad.\n"
        "✅ Removed from the lineup.\n"
        "✅ Contract deactivated.\n"
        "🔄 Player is now available on the market."
    )

release_callback_handler = CallbackQueryHandler(
    release_callback,
    pattern=r"^(release_select|release_confirm):\d+$|^release_cancel$",
)



# ==========================================================
# MY TRANSFERS
# ==========================================================

async def my_transfers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
                TransferListing.status.in_(["available", "active"]),
            )
            .order_by(Player.overall.desc(), Player.name.asc())
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

    for index, (listing, player) in enumerate(rows, 1):
        lines.extend([
            f"{index}. ⚽ {player.name}",
            f"   ⭐ OVR: {player.overall}",
            f"   💰 {listing.price:,} Coins",
            "",
        ])

    await message.reply_text("\n".join(lines))

# ==========================================================
# HANDLER EXPORTS
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

release_callback_handler = CallbackQueryHandler(
    release_callback,
    pattern=r"^(release_select|release_confirm):\d+$|^release_cancel$",
)

