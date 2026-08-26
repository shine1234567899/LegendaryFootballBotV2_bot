from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    User,
    Club,
    ClubPlayer,
    Player,
    Trade,
)


# ==========================================================
# TRADE
# ==========================================================
#
# /trade @username
#
# Opens a trade request with another manager.
#
# The actual player/coin offer is sent through a confirmation
# flow so nothing is changed before both sides accept.
#
# Available model fields:
#   Trade.sender_id
#   Trade.receiver_id
#   Trade.offered_player_id
#   Trade.requested_player_id
#   Trade.offered_coins
#   Trade.requested_coins
#   Trade.status
#
# No balance or player ownership is changed by simply opening
# the trade window.
# ==========================================================


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


async def _get_user_club(
    session,
    user_id: int,
):
    result = await session.execute(
        select(Club).where(
            Club.owner_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _get_current_players(
    session,
    club_id: int,
):
    result = await session.execute(
        select(
            ClubPlayer,
            Player,
        )
        .join(
            Player,
            Player.id == ClubPlayer.player_id,
        )
        .where(
            ClubPlayer.club_id == club_id,
            ClubPlayer.is_current.is_(True),
        )
        .order_by(
            Player.overall.desc(),
            Player.name.asc(),
        )
    )

    return list(result.all())


def _trade_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ MY PLAYERS",
                    callback_data="trade:myplayers",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="trade:close",
                ),
            ],
        ]
    )


def _player_keyboard(
    players,
):
    rows = []

    for _, player in players[:20]:
        rows.append(
            [
                InlineKeyboardButton(
                    f"⚽ {player.name} • {player.overall}",
                    callback_data=f"trade:offer:{player.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data="trade:back",
            ),
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="trade:close",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)



def _requested_player_keyboard(players):
    rows = []
    for _, player in players[:20]:
        rows.append([InlineKeyboardButton(
            f"📥 {player.name} • {player.overall}",
            callback_data=f"trade:request:{player.id}",
        )])
    rows.append([InlineKeyboardButton("❌ CLOSE", callback_data="trade:close")])
    return InlineKeyboardMarkup(rows)

async def trade(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if len(context.args) != 1:
        await message.reply_text(
            (
                "🤝 𝐓𝐑𝐀𝐃𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/trade @username\n\n"
                "Example:\n"
                "/trade @manager"
            )
        )
        return

    async with AsyncSessionLocal() as session:
        sender = await session.get(
            User,
            user.id,
        )

        if sender is None:
            await message.reply_text(
                "❌ Your account was not found."
            )
            return

        receiver = await _get_user_by_username(
            session,
            context.args[0],
        )

        if receiver is None:
            await message.reply_text(
                "❌ Manager not found."
            )
            return

        if receiver.id == sender.id:
            await message.reply_text(
                "❌ You cannot trade with yourself."
            )
            return

        sender_club = await _get_user_club(
            session,
            sender.id,
        )
        receiver_club = await _get_user_club(
            session,
            receiver.id,
        )

        if sender_club is None:
            await message.reply_text(
                "❌ Create your club first."
            )
            return

        if receiver_club is None:
            await message.reply_text(
                "❌ This manager has no club yet."
            )
            return

        context.user_data["pending_trade_target"] = {
            "receiver_id": receiver.id,
            "receiver_name": (
                f"@{receiver.username}"
                if receiver.username
                else (
                    receiver.first_name
                    or f"User #{receiver.id}"
                )
            ),
        }

    await message.reply_text(
        (
            "🤝 𝐓𝐑𝐀𝐃𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Manager : "
            f"{context.user_data['pending_trade_target']['receiver_name']}\n\n"
            "Choose the player you want to offer."
        ),
        reply_markup=_trade_menu_keyboard(),
    )


async def trade_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or not query.data:
        return

    try:
        await query.answer()
    except Exception:
        pass

    action_parts = str(
        query.data
    ).split(":")

    action = (
        action_parts[1]
        if len(action_parts) > 1
        else ""
    )

    if action == "close":
        context.user_data.pop(
            "pending_trade_target",
            None,
        )
        context.user_data.pop(
            "pending_trade_offer_player",
            None,
        )
        await query.edit_message_text(
            "🤝 Trade closed."
        )
        return

    target = context.user_data.get(
        "pending_trade_target"
    )

    if not target:
        await query.edit_message_text(
            "⚠️ This trade session has expired."
        )
        return

    if action == "back":
        await query.edit_message_text(
            (
                "🤝 𝐓𝐑𝐀𝐃𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Manager : "
                f"{target['receiver_name']}\n\n"
                "Choose an action:"
            ),
            reply_markup=_trade_menu_keyboard(),
        )
        return

    if action == "myplayers":
        async with AsyncSessionLocal() as session:
            club = await _get_user_club(
                session,
                query.from_user.id,
            )

            if club is None:
                await query.edit_message_text(
                    "❌ Create your club first."
                )
                return

            players = await _get_current_players(
                session,
                club.id,
            )

        if not players:
            await query.edit_message_text(
                (
                    "🤝 𝐓𝐑𝐀𝐃𝐄\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "📭 Your club has no players available."
                ),
                reply_markup=_trade_menu_keyboard(),
            )
            return

        await query.edit_message_text(
            (
                "🤝 𝐓𝐑𝐀𝐃𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Manager : "
                f"{target['receiver_name']}\n\n"
                "Select the player to offer:"
            ),
            reply_markup=_player_keyboard(players),
        )
        return

    if action == "offer":
        if len(action_parts) != 3:
            return

        try:
            player_id = int(
                action_parts[2]
            )
        except ValueError:
            await query.edit_message_text(
                "❌ Invalid player."
            )
            return

        async with AsyncSessionLocal() as session:
            sender_club = await _get_user_club(
                session,
                query.from_user.id,
            )

            if sender_club is None:
                await query.edit_message_text(
                    "❌ Your club was not found."
                )
                return

            ownership = await session.execute(
                select(ClubPlayer).where(
                    ClubPlayer.club_id == sender_club.id,
                    ClubPlayer.player_id == player_id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            if ownership.scalar_one_or_none() is None:
                await query.edit_message_text(
                    "❌ You do not own this player."
                )
                return

            player_result = await session.execute(
                select(Player).where(
                    Player.id == player_id
                )
            )
            player = player_result.scalar_one_or_none()

        if player is None:
            await query.edit_message_text(
                "❌ Player not found."
            )
            return

        context.user_data[
            "pending_trade_offer_player"
        ] = player.id

        await query.edit_message_text(
            (
                "🤝 𝐓𝐑𝐀𝐃𝐄 𝐎𝐅𝐅𝐄𝐑\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 To : {target['receiver_name']}\n"
                f"⚽ Player : {player.name}\n"
                f"⭐ Overall : {player.overall}\n\n"
                "The next step will let you define the "
                "requested player/coins before sending the offer."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ CONTINUE",
                            callback_data="trade:continue",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ CANCEL",
                            callback_data="trade:close",
                        )
                    ],
                ]
            ),
        )
        return

    if action == "continue":
        offer_player_id = context.user_data.get(
            "pending_trade_offer_player"
        )

        if offer_player_id is None:
            await query.edit_message_text(
                "⚠️ This trade session has expired."
            )
            return

        await query.edit_message_text(
            (
                "🤝 𝐓𝐑𝐀𝐃𝐄 𝐎𝐅𝐅𝐄𝐑\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚽ Your offered player is selected.\n\n"
                "The receiver/requested-player selection "
                "will be completed in the next trade step."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "❌ CLOSE",
                            callback_data="trade:close",
                        )
                    ]
                ]
            ),
        )


trade_handler = CommandHandler(
    "trade",
    trade,
)

trade_callback_handler = CallbackQueryHandler(
    trade_callback,
    pattern=(
        r"^trade:"
        r"(myplayers|offer:\d+|request:\d+|continue|send|back|close)$"
    ),
)

async def trade_response_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or not query.data:
        return
    parts = str(query.data).split(":")
    if len(parts) != 3:
        return
    action, trade_id_text = parts[1], parts[2]
    try:
        trade_id = int(trade_id_text)
    except ValueError:
        return
    await query.answer()

    async with AsyncSessionLocal() as session:
        trade = await session.get(Trade, trade_id)
        if trade is None or trade.status != "PENDING":
            await query.edit_message_text("⚠️ Trade no longer available.")
            return
        if query.from_user.id != trade.receiver_id:
            await query.answer("❌ This trade is not for you.", show_alert=True)
            return

        if action == "decline":
            trade.status = "DECLINED"
            await session.commit()
            await query.edit_message_text("❌ Trade declined.")
            return

        sender_club = await _get_user_club(session, trade.sender_id)
        receiver_club = await _get_user_club(session, trade.receiver_id)
        offered_ownership = await session.scalar(select(ClubPlayer).where(
            ClubPlayer.club_id == sender_club.id,
            ClubPlayer.player_id == trade.offered_player_id,
            ClubPlayer.is_current.is_(True),
        ))
        requested_ownership = await session.scalar(select(ClubPlayer).where(
            ClubPlayer.club_id == receiver_club.id,
            ClubPlayer.player_id == trade.requested_player_id,
            ClubPlayer.is_current.is_(True),
        ))
        if offered_ownership is None or requested_ownership is None:
            trade.status = "CANCELLED"
            await session.commit()
            await query.edit_message_text("❌ Trade cancelled: player unavailable.")
            return

        # Swap ownership in the same transaction.
        offered_ownership.club_id = receiver_club.id
        requested_ownership.club_id = sender_club.id
        trade.status = "ACCEPTED"
        await session.commit()

    await query.edit_message_text("✅ Trade completed successfully.")

trade_response_handler = CallbackQueryHandler(
    trade_response_callback,
    pattern=r"^trade_(accept|decline):\d+$",
)
