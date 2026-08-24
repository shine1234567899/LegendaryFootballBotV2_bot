import asyncio
from pathlib import Path

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
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    User,
    Transaction,
)


# ==========================================================
# PATH
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRAINING_BANNER = (
    BASE_DIR / "assets" / "TRAINING.jpg"
)


# ==========================================================
# TRAINING CONFIG
# ==========================================================

TRAINING_COST_COINS = 2_000_000
TRAINING_COST_GEMS = 20

TRAINING_GAIN = 1


# ==========================================================
# USER LOCKS
# ==========================================================

_training_locks = {}


def get_training_lock(user_id: int):

    if user_id not in _training_locks:
        _training_locks[user_id] = asyncio.Lock()

    return _training_locks[user_id]


# ==========================================================
# GET CLUB + PLAYERS
# ==========================================================

async def get_club_players(user_id: int):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )

        club = result.scalar_one_or_none()

        if club is None:
            return None, []

        result = await session.execute(
            select(Player)
            .join(
                ClubPlayer,
                ClubPlayer.player_id == Player.id,
            )
            .where(
                ClubPlayer.club_id == club.id,
                ClubPlayer.is_current.is_(True),
            )
            .order_by(
                Player.overall.desc()
            )
        )

        players = result.scalars().all()

        return club, players


# ==========================================================
# TRAINING TEXT
# ==========================================================

def training_text():

    return (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗟𝗘𝗚𝗘𝗡𝗗𝗔𝗥𝗬 𝗧𝗥𝗔𝗜𝗡𝗜𝗡𝗚\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        "🏋️ TRAINING CENTER\n\n"
        "Select a player to begin training.\n\n"
        "📈 +1 OVR per training\n"
        "🎯 Limited by player potential\n"
        "💰 2,000,000 Coins\n"
        "💎 20 Gems\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ==========================================================
# PLAYER LIST
# ==========================================================

def training_keyboard(players):

    keyboard = []

    for player in players:

        keyboard.append([
            InlineKeyboardButton(
                (
                    f"⚽ {player.name} "
                    f"• ⭐ {player.overall}"
                ),
                callback_data=(
                    f"training_player:{player.id}"
                ),
            )
        ])

    return InlineKeyboardMarkup(
        keyboard
    )


# ==========================================================
# SAFE EDIT
# ==========================================================

async def edit_training_message(
    query,
    text,
    keyboard,
):

    message = query.message

    if message is None:
        return

    if message.photo:

        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
        )

    else:

        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
        )


# ==========================================================
# /TRAINING
# ==========================================================

async def training(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.message is None:
        return

    if update.effective_user is None:
        return

    user_id = update.effective_user.id

    club, players = await get_club_players(
        user_id
    )

    if club is None:

        await update.message.reply_text(
            "❌ You don't have a club yet."
        )

        return

    if not players:

        await update.message.reply_text(
            "❌ Your club has no players."
        )

        return

    context.user_data[
        "training_player"
    ] = None

    context.user_data[
        "training_type"
    ] = None

    text = training_text()

    keyboard = training_keyboard(
        players
    )

    if TRAINING_BANNER.exists():

        with open(
            TRAINING_BANNER,
            "rb",
        ) as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                reply_markup=keyboard,
            )

    else:

        await update.message.reply_text(
            text,
            reply_markup=keyboard,
        )


# ==========================================================
# PLAYER SELECTION
# ==========================================================

async def show_training_player(
    query,
    context,
    player_id: int,
):

    user_id = query.from_user.id

    club, players = await get_club_players(
        user_id
    )

    if club is None:
        return

    player = next(
        (
            player
            for player in players
            if player.id == player_id
        ),
        None,
    )

    if player is None:

        await query.answer(
            "❌ Player not found.",
            show_alert=True,
        )

        return

    context.user_data[
        "training_player"
    ] = player.id

    position = player.position.upper()

    training_options = {
        "GK": (
            "🧤 GOALKEEPING",
            "GK",
        ),
        "DEF": (
            "🛡️ DEFENCE",
            "DEF",
        ),
        "MID": (
            "⚙️ MIDFIELD",
            "MID",
        ),
        "ATT": (
            "⚡ ATTACK",
            "ATT",
        ),
    }

    option = training_options.get(
        position
    )

    if option is None:

      await query.answer(
            f"❌ Unsupported position: {position}",
            show_alert=True,
        )

      return

    training_name, training_type = option

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                training_name,
                callback_data=(
                    f"training_type:"
                    f"{player.id}:"
                    f"{training_type}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=(
                    "training_back"
                ),
            )
        ],
    ])
    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗧𝗥𝗔𝗜𝗡𝗜𝗡𝗚 𝗖𝗘𝗡𝗧𝗘𝗥\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"⚽ {player.name}\n"
        f"📍 Position : {position}\n"
        f"⭐ Overall : {player.overall}\n"
        f"📈 Potential : {player.potential}\n\n"
        f"🎯 Available training : "
        f"{training_name}\n\n"
        "Choose your training program."
    )

    await edit_training_message(
        query,
        text,
        keyboard,
    )


# ==========================================================
# TRAINING PROGRAM
# ==========================================================

async def show_training_program(
    query,
    context,
    player_id: int,
    training_type: str,
):

    user_id = query.from_user.id

    club, players = await get_club_players(
        user_id
    )

    if club is None:
        return

    player = next(
        (
            player
            for player in players
            if player.id == player_id
        ),
        None,
    )

    if player is None:

        await query.answer(
            "❌ Player not found.",
            show_alert=True,
        )

        return

    context.user_data[
        "training_player"
    ] = player.id

    context.user_data[
        "training_type"
    ] = training_type

    if player.overall >= player.potential:

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ BACK",
                    callback_data=(
                        f"training_player:"
                        f"{player.id}"
                    ),
                )
            ]
        ])

        text = (
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
            "       𝗧𝗥𝗔𝗜𝗡𝗜𝗡𝗚 𝗖𝗘𝗡𝗧𝗘𝗥\n"
            "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
            f"⚽ {player.name}\n"
            f"⭐ Overall : {player.overall}\n"
            f"📈 Potential : {player.potential}\n\n"
            "🏆 MAXIMUM POTENTIAL REACHED\n\n"
            "This player cannot gain any "
            "more overall."
        )

        await edit_training_message(
            query,
            text,
            keyboard,
        )

        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 PAY 2,000,000 COINS",
                callback_data=(
                    f"training_pay:"
                    f"{player.id}:"
                    f"{training_type}:COINS"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                "💎 PAY 20 GEMS",
                callback_data=(
                    f"training_pay:"
                    f"{player.id}:"
                    f"{training_type}:GEMS"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=(
                    f"training_player:"
                    f"{player.id}"
                ),
            ),
        ],
    ])

    text = (
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "       𝗧𝗥𝗔𝗜𝗡𝗜𝗡𝗚 𝗖𝗘𝗡𝗧𝗘𝗥\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        f"⚽ {player.name}\n"
        f"⭐ Current OVR : {player.overall}\n"
        f"📈 Potential : {player.potential}\n\n"
        f"🎯 Program : {training_type}\n\n"
        "📈 Training reward : +1 OVR\n\n"
        "💰 2,000,000 Coins\n"
        "💎 20 Gems\n\n"
        "Choose your payment method."
    )

    await edit_training_message(
        query,
        text,
        keyboard,
    )


# ==========================================================
# EXECUTE PAYMENT + TRAINING
# ==========================================================

async def execute_training(
    query,
    player_id: int,
    training_type: str,
    currency: str,
):

    user_id = query.from_user.id

    lock = get_training_lock(
        user_id
    )

    if lock.locked():

        await query.answer(
            "⏳ Training already processing.",
            show_alert=True,
        )

        return

    async with lock:

        async with AsyncSessionLocal() as session:

            # ----------------------------------------------
            # LOCK USER
            # ----------------------------------------------

            user_result = await session.execute(
                select(User)
                .where(
                    User.id == user_id
                )
                .with_for_update()
            )

            user = (
                user_result.scalar_one_or_none()
            )

            if user is None:

                await query.answer(
                    "❌ User not found.",
                    show_alert=True,
                )

                return

            # ----------------------------------------------
            # LOCK PLAYER
            # ----------------------------------------------

            player_result = await session.execute(
                select(Player)
                .join(
                    ClubPlayer,
                    ClubPlayer.player_id
                    == Player.id,
                )
                .join(
                    Club,
                    Club.id
                    == ClubPlayer.club_id,
                )
                .where(
                    Player.id == player_id,
                    Club.owner_id == user_id,
                    ClubPlayer.is_current.is_(True),
                )
                .with_for_update()
            )

            player = (
                player_result.scalar_one_or_none()
            )

            if player is None:

                await query.answer(
                    "❌ This player isn't in your club.",
                    show_alert=True,
                )

                return
            player_position = player.position.upper()

            if player_position != training_type:

             await query.answer(
            (
                f"❌ {player.name} is a "
                f"{player_position}."
            ),
            show_alert=True,
        )

             return

            # ----------------------------------------------
            # POTENTIAL CHECK
            # ----------------------------------------------

            if player.overall >= player.potential:

                await query.answer(
                    "🏆 Player already reached potential.",
                    show_alert=True,
                )

                return

            # ----------------------------------------------
            # PRICE
            # ----------------------------------------------

            if currency == "COINS":

                price = TRAINING_COST_COINS
                balance = user.coins

            elif currency == "GEMS":

                price = TRAINING_COST_GEMS
                balance = user.gems

            else:

                await query.answer(
                    "❌ Invalid payment method.",
                    show_alert=True,
                )

                return

            # ----------------------------------------------
            # BALANCE CHECK
            # ----------------------------------------------

            if balance < price:

                if currency == "COINS":

                    message = (
                        "❌ Not enough Coins.\n\n"
                        f"Required: {price:,}\n"
                        f"Your balance: {balance:,}"
                    )

                else:

                    message = (
                        "❌ Not enough Gems.\n\n"
                        f"Required: {price}\n"
                        f"Your balance: {balance}"
                    )

                await query.answer(
                    message,
                    show_alert=True,
                )

                return

            # ----------------------------------------------
            # PAYMENT
            # ----------------------------------------------

            if currency == "COINS":

                user.coins -= price

            else:

                user.gems -= price

            # ----------------------------------------------
            # TRAINING
            # ----------------------------------------------

            old_overall = player.overall

            new_overall = min(
                old_overall + TRAINING_GAIN,
                player.potential,
            )

            player.overall = new_overall

            # ----------------------------------------------
            # TRANSACTION
            # ----------------------------------------------

            transaction = Transaction(
                user_id=user_id,
                transaction_type="training",
                currency=currency,
                amount=price,
                description=(
                    f"Training {player.name} "
                    f"({training_type})"
                ),
                reference=(
                    f"training:"
                    f"{player.id}:"
                    f"{old_overall}:"
                    f"{new_overall}"
                ),
            )

            session.add(transaction)

            await session.commit()

            # ----------------------------------------------
            # SUCCESS
            # ----------------------------------------------

            remaining = (
                user.coins
                if currency == "COINS"
                else user.gems
            )

            text = (
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
                "       𝗧𝗥𝗔𝗜𝗡𝗜𝗡𝗚 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘\n"
                "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
                f"⚽ {player.name}\n\n"
                f"🎯 Program : {training_type}\n\n"
                f"⭐ OVR : "
                f"{old_overall} → {new_overall}\n"
                f"📈 Potential : {player.potential}\n\n"
                f"💳 Paid : "
                f"{price:,} {currency}\n"
                f"💰 Remaining : {remaining:,}\n\n"
                "🔥 Your player has improved!"
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🏋️ TRAIN AGAIN",
                        callback_data=(
                            f"training_player:"
                            f"{player.id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ TRAINING CENTER",
                        callback_data=(
                            "training_back"
                        ),
                    )
                ],
            ])

            await edit_training_message(
                query,
                text,
                keyboard,
            )


# ==========================================================
# MAIN CALLBACK
# ==========================================================

async def training_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    data = query.data

    if not data:
        return

    # ======================================================
    # PLAYER
    # ======================================================

    if data.startswith(
        "training_player:"
    ):

        try:

            player_id = int(
                data.split(":")[1]
            )

        except (
            IndexError,
            ValueError,
        ):

            await query.answer(
                "❌ Invalid player.",
                show_alert=True,
            )

            return

        await show_training_player(
            query,
            context,
            player_id,
        )

        return

    # ======================================================
    # BACK
    # ======================================================

    if data == "training_back":

        user_id = query.from_user.id

        club, players = (
            await get_club_players(
                user_id
            )
        )

        if club is None:
            return

        context.user_data[
            "training_player"
        ] = None

        context.user_data[
            "training_type"
        ] = None

        await edit_training_message(
            query,
            training_text(),
            training_keyboard(
                players
            ),
        )

        return

    # ======================================================
    # TRAINING TYPE
    # ======================================================

    if data.startswith(
        "training_type:"
    ):

        parts = data.split(":")

        if len(parts) != 3:
            return

        try:

            player_id = int(
                parts[1]
            )

        except ValueError:

            await query.answer(
                "❌ Invalid player.",
                show_alert=True,
            )

            return

        training_type = parts[2]

        if training_type not in {
            "ATT",
            "DEF",
            "MID",
            "GK",
        }:

            await query.answer(
                "❌ Invalid training.",
                show_alert=True,
            )

            return

        await show_training_program(
            query,
            context,
            player_id,
            training_type,
        )

        return

    # ======================================================
    # PAYMENT
    # ======================================================

    if data.startswith(
        "training_pay:"
    ):

        parts = data.split(":")

        if len(parts) != 4:
            return

        try:

            player_id = int(
                parts[1]
            )

        except ValueError:

            await query.answer(
                "❌ Invalid player.",
                show_alert=True,
            )

            return

        training_type = parts[2]
        currency = parts[3]

        if training_type not in {
            "ATT",
            "DEF",
            "MID",
            "GK",
        }:

            await query.answer(
                "❌ Invalid training.",
                show_alert=True,
            )

            return

        if currency not in {
            "COINS",
            "GEMS",
        }:

            await query.answer(
                "❌ Invalid currency.",
                show_alert=True,
            )

            return

        await execute_training(
            query,
            player_id,
            training_type,
            currency,
        )

        return


# ==========================================================
# HANDLERS
# ==========================================================

training_handler = CommandHandler(
    "training",
    training,
)


training_callback_handler = (
    CallbackQueryHandler(
        training_callback,
        pattern=(
            r"^training_"
            r"(player:\d+|"
            r"type:\d+:(ATT|DEF|MID|GK)|"
            r"pay:\d+:(ATT|DEF|MID|GK):(COINS|GEMS)|"
            r"back)$"
        ),
    )
)