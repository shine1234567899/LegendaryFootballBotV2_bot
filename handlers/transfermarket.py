from pathlib import Path
from datetime import datetime, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select, func

from database.database import AsyncSessionLocal
from database.models import (
    User,
    Club,
    ClubPlayer,
    Player,
    TransferListing,
    Transaction,
)
from handlers.manager_contracts import ensure_player_contract


BASE_DIR = Path(__file__).resolve().parent.parent
TRANSFER_BANNER = BASE_DIR / "assets" / "TRANSFER_WINDOW.jpg"

PLAYERS_PER_PAGE = 5
MAX_SQUAD_SIZE = 36


def currency_text(price: int, currency: str) -> str:
    if currency == "GEMS":
        return f"💎 {price:,} Gems"
    return f"💰 {price:,} Coins"


async def get_market_page(page: int):
    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(TransferListing, Player)
            .join(
                Player,
                Player.id == TransferListing.player_id,
            )
            .where(
                TransferListing.status == "available"
            )
            .order_by(TransferListing.id)
        )

        listings = result.all()

    total = len(listings)

    if total == 0:
        return [], 0, 0

    total_pages = (
        total + PLAYERS_PER_PAGE - 1
    ) // PLAYERS_PER_PAGE

    page = max(
        0,
        min(page, total_pages - 1),
    )

    start = page * PLAYERS_PER_PAGE
    end = start + PLAYERS_PER_PAGE

    return (
        listings[start:end],
        page,
        total_pages,
    )


async def get_market_count():
    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                func.count(TransferListing.id)
            ).where(
                TransferListing.status == "available"
            )
        )

        return result.scalar() or 0


async def get_user_club_data(user_id: int):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club, User)
            .join(
                User,
                User.id == Club.owner_id,
            )
            .where(
                Club.owner_id == user_id
            )
        )

        row = result.first()

        if row is None:
            return None

        club, user = row

        squad_result = await session.execute(
            select(
                func.count(ClubPlayer.id)
            ).where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
        )

        squad_size = (
            squad_result.scalar() or 0
        )

        return club, user, squad_size


def build_market_text(
    user,
    squad_size,
    listings,
    page,
    total_pages,
    market_count,
):

    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "      𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗠𝗔𝗥𝗞𝗘𝗧\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"💰 Coins: {user.coins:,}\n"
        f"💎 Gems: {user.gems:,}\n"
        f"👥 Squad: {squad_size}/{MAX_SQUAD_SIZE}\n\n"
        "🔥 AVAILABLE PLAYERS\n\n"
    )

    for index, (listing, player) in enumerate(
        listings,
        start=page * PLAYERS_PER_PAGE + 1,
    ):

        text += (
            f"{index}. ⚽ {player.name}\n"
            f"   ⭐ OVR {player.overall} • "
            f"📍 {player.position} • "
            f"🌍 {player.country}\n"
            f"   {currency_text(listing.price, listing.currency)}\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 Page {page + 1}/{total_pages}\n"
        f"🔥 {market_count} players available"
    )

    return text


def build_market_keyboard(
    listings,
    page,
    total_pages,
):

    keyboard = []

    # Boutons d'achat
    for listing, player in listings:

        keyboard.append([
            InlineKeyboardButton(
                f"🛒 Buy {player.name}",
                callback_data=f"transfer_buy:{listing.id}",
            )
        ])

    # Pagination
    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"transfer_page:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"transfer_page:{page + 1}",
            )
        )

    if navigation:
        keyboard.append(navigation)

    if not keyboard:
        return None

    return InlineKeyboardMarkup(keyboard)


async def transfermarket(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        update.effective_message is None
        or update.effective_user is None
    ):
        return

    message = update.effective_message
    user_id = update.effective_user.id

    club_data = await get_user_club_data(
        user_id
    )

    if club_data is None:
        await message.reply_text(
            "❌ You don't have a club yet."
        )
        return

    club, user, squad_size = club_data

    listings, page, total_pages = (
        await get_market_page(0)
    )

    if not listings:
        await message.reply_text(
            "❌ The Transfer Market is currently empty."
        )
        return

    market_count = await get_market_count()

    text = build_market_text(
        user,
        squad_size,
        listings,
        page,
        total_pages,
        market_count,
    )

    keyboard = build_market_keyboard(
        listings,
        page,
        total_pages,
    )

    if TRANSFER_BANNER.exists():

        with open(
            TRANSFER_BANNER,
            "rb",
        ) as photo:

            await message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard,
            )

    else:

        await message.reply_text(
            text,
            reply_markup=keyboard,
        )


async def transfermarket_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    user_id = query.from_user.id

    # ==============================
    # BUY PLAYER
    # ==============================

    if query.data.startswith("transfer_buy:"):

        try:
            listing_id = int(
                query.data.split(":")[1]
            )
        except (
            IndexError,
            ValueError,
        ):
            return

        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(TransferListing, Player)
                .join(
                    Player,
                    Player.id
                    == TransferListing.player_id,
                )
                .where(
                    TransferListing.id
                    == listing_id
                )
            )

            row = result.first()

            if row is None:

                await query.answer(
                    "❌ This listing no longer exists.",
                    show_alert=True,
                )
                return

            listing, player = row

            # Vérifie que le joueur est toujours disponible
            if listing.status != "available":

                await query.answer(
                    "❌ This player has already been sold.",
                    show_alert=True,
                )
                return

            # Récupère le club + propriétaire
            result = await session.execute(
                select(Club, User)
                .join(
                    User,
                    User.id == Club.owner_id,
                )
                .where(
                    Club.owner_id == user_id
                )
            )

            club_row = result.first()

            if club_row is None:

                await query.answer(
                    "❌ You don't have a club.",
                    show_alert=True,
                )
                return

            club, user = club_row

            # Vérifie la taille du squad
            squad_result = await session.execute(
                select(
                    func.count(ClubPlayer.id)
                ).where(
                    ClubPlayer.club_id == club.id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            squad_size = (
                squad_result.scalar() or 0
            )

            if squad_size >= MAX_SQUAD_SIZE:

                await query.answer(
                    "❌ Your squad is full (36/36).",
                    show_alert=True,
                )
                return

            # ==============================
            # Vérification du solde
            # ==============================

            if listing.currency == "GEMS":

                if user.gems < listing.price:

                    await query.answer(
                        "❌ You don't have enough Gems.",
                        show_alert=True,
                    )
                    return

                user.gems -= listing.price

            else:

                if user.coins < listing.price:

                    await query.answer(
                        "❌ You don't have enough Coins.",
                        show_alert=True,
                    )
                    return

                user.coins -= listing.price

            # ==============================
            # Ajout du joueur au club
            # ==============================

            club_player = ClubPlayer(
                club_id=club.id,
                player_id=player.id,
                joined_at=datetime.now(timezone.utc),
                is_current=True,
            )

            session.add(club_player)
            await session.flush()

            # Contrat initial automatique pour tout nouveau joueur.
            await ensure_player_contract(
                session,
                club.id,
                player.id,
            )

            # Listing vendu
            listing.status = "sold"
            listing.sold_at = datetime.now(timezone.utc)

            # Transaction
            transaction = Transaction(
                user_id=user.id,
                transaction_type="transfer_purchase",
                currency=listing.currency,
                amount=listing.price,
                description=f"Purchased {player.name}",
                reference=f"transfer_listing:{listing.id}",
            )

            session.add(transaction)

            await session.commit()

        # ==============================
        # Confirmation
        # ==============================

        await query.answer(
            f"✅ {player.name} signed!",
            show_alert=True,
        )

        await query.edit_message_caption(
            caption=(
                "✅━━━━━━━━━━━━━━━━━━━━✅\n"
                "       𝗣𝗟𝗔𝗬𝗘𝗥 𝗦𝗜𝗚𝗡𝗘𝗗\n"
                "✅━━━━━━━━━━━━━━━━━━━━✅\n\n"
                f"⚽ {player.name}\n"
                f"⭐ Overall: {player.overall}\n"
                f"📍 Position: {player.position}\n"
                f"🌍 Country: {player.country}\n\n"
                f"{currency_text(listing.price, listing.currency)}\n"
                "📄 Initial contract: 30 days\n"
                "💰 Initial salary: 100,000 Coins/day\n\n"
                "🏟️ The player has joined your club!"
            )
        )

        return

    # ==============================
    # PAGINATION
    # ==============================

    if query.data.startswith("transfer_page:"):

        try:
            page = int(
                query.data.split(":")[1]
            )
        except (
            IndexError,
            ValueError,
        ):
            return

        club_data = await get_user_club_data(
            user_id
        )

        if club_data is None:

            await query.answer(
                "❌ You don't have a club.",
                show_alert=True,
            )
            return

        club, user, squad_size = club_data

        listings, page, total_pages = (
            await get_market_page(page)
        )

        if not listings:

            await query.answer(
                "❌ No players on this page.",
                show_alert=True,
            )
            return

        market_count = await get_market_count()

        text = build_market_text(
            user,
            squad_size,
            listings,
            page,
            total_pages,
            market_count,
        )

        keyboard = build_market_keyboard(
            listings,
            page,
            total_pages,
        )

        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
        )


transfermarket_handler = CommandHandler(
    "transfer",
    transfermarket,
)


transfermarket_callback_handler = (
    CallbackQueryHandler(
        transfermarket_callback,
        pattern=r"^transfer_(page|buy):\d+$",
    )
)