from __future__ import annotations

from datetime import datetime, timezone

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
        offer_player_id = context.user_data.get("pending_trade_offer_player")
        if offer_player_id is None:
            await query.edit_message_text("⚠️ This trade session has expired.")
            return

        async with AsyncSessionLocal() as session:
            receiver_club = await _get_user_club(session, target["receiver_id"])
            if receiver_club is None:
                await query.edit_message_text("❌ The other manager has no club.")
                return
            players = await _get_current_players(session, receiver_club.id)

        if not players:
            await query.edit_message_text("❌ The other manager has no players available.")
            return

        await query.edit_message_text(
            "🤝 𝐓𝐑𝐀𝐃𝐄\n━━━━━━━━━━━━━━━━━━━━\n"
            "📥 Choose the player you want from the other manager:",
            reply_markup=_requested_player_keyboard(players),
        )
        return

    if action == "request":
        if len(action_parts) != 3:
            return

        try:
            requested_player_id = int(action_parts[2])
        except ValueError:
            await query.edit_message_text("❌ Invalid player.")
            return

        offered_player_id = context.user_data.get("pending_trade_offer_player")
        if offered_player_id is None:
            await query.edit_message_text("⚠️ This trade session has expired.")
            return

        async with AsyncSessionLocal() as session:
            sender_club = await _get_user_club(session, query.from_user.id)
            receiver_club = await _get_user_club(session, target["receiver_id"])

            if sender_club is None or receiver_club is None:
                await query.edit_message_text("❌ One of the clubs no longer exists.")
                return

            offered_ownership = await session.scalar(select(ClubPlayer).where(
                ClubPlayer.club_id == sender_club.id,
                ClubPlayer.player_id == offered_player_id,
                ClubPlayer.is_current.is_(True),
            ))
            requested_ownership = await session.scalar(select(ClubPlayer).where(
                ClubPlayer.club_id == receiver_club.id,
                ClubPlayer.player_id == requested_player_id,
                ClubPlayer.is_current.is_(True),
            ))

            if offered_ownership is None:
                await query.edit_message_text("❌ You no longer own the offered player.")
                return
            if requested_ownership is None:
                await query.edit_message_text("❌ The requested player is no longer available.")
                return

            existing = await session.scalar(select(Trade).where(
                Trade.sender_id == query.from_user.id,
                Trade.receiver_id == target["receiver_id"],
                Trade.offered_player_id == offered_player_id,
                Trade.requested_player_id == requested_player_id,
                Trade.status.in_(["pending", "PENDING"]),
            ))
            if existing is not None:
                await query.edit_message_text("❌ This trade offer is already pending.")
                return

            offered_player = await session.get(Player, offered_player_id)
            requested_player = await session.get(Player, requested_player_id)

            trade_obj = Trade(
                sender_id=query.from_user.id,
                receiver_id=target["receiver_id"],
                offered_player_id=offered_player_id,
                requested_player_id=requested_player_id,
                offered_coins=0,
                requested_coins=0,
                status="pending",
            )
            session.add(trade_obj)
            await session.flush()
            trade_id = trade_obj.id
            await session.commit()

        await query.edit_message_text(
            "✅ 𝐓𝐑𝐀𝐃𝐄 𝐒𝐄𝐍𝐓\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 To : {target['receiver_name']}\n"
            f"⚽ You offer : {offered_player.name}\n"
            f"📥 You request : {requested_player.name}\n\n"
            "⏳ Waiting for acceptance."
        )

        sender_label = (
            f"@{query.from_user.username}"
            if query.from_user.username
            else (query.from_user.first_name or str(query.from_user.id))
        )

        try:
            await context.bot.send_message(
                chat_id=target["receiver_id"],
                text=(
                    "🤝 𝐍𝐄𝐖 𝐓𝐑𝐀𝐃𝐄 𝐎𝐅𝐅𝐄𝐑\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 From : {sender_label}\n"
                    f"⚽ Offered : {offered_player.name}\n"
                    f"📥 Requested : {requested_player.name}\n\n"
                    "Do you accept this trade?"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ ACCEPT", callback_data=f"trade_accept:{trade_id}"),
                    InlineKeyboardButton("❌ DECLINE", callback_data=f"trade_decline:{trade_id}"),
                ]]),
            )
        except Exception:
            async with AsyncSessionLocal() as session:
                failed = await session.get(Trade, trade_id)
                if failed is not None:
                    failed.status = "cancelled"
                    await session.commit()
        return


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

def _trade_status_value(trade, desired: str):
    """
    Keep compatibility with either a plain VARCHAR status or a SQLAlchemy
    Enum whose values/names may be uppercase.
    """
    desired_upper = desired.upper()
    desired_lower = desired.lower()

    try:
        column = Trade.__table__.c.status
        enum_class = getattr(column.type, "enum_class", None)
        if enum_class is not None:
            for member in enum_class:
                if (
                    getattr(member, "name", "").upper() == desired_upper
                    or str(getattr(member, "value", "")).lower() == desired_lower
                ):
                    return member
    except Exception:
        pass

    return desired_lower


async def trade_response_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None or not query.data:
        return

    data = str(query.data)

    # Only this callback handler should receive these two actions.
    if not data.startswith("trade_accept:") and not data.startswith("trade_decline:"):
        return

    try:
        await query.answer()
    except Exception:
        pass

    try:
        action, trade_id_text = data.split(":", 1)
        trade_id = int(trade_id_text)
    except (ValueError, TypeError):
        try:
            await query.edit_message_text("❌ Invalid trade request.")
        except Exception:
            pass
        return

    async with AsyncSessionLocal() as session:
        try:
            trade = await session.get(Trade, trade_id)

            if trade is None:
                await query.edit_message_text(
                    "⚠️ This trade no longer exists."
                )
                return

            if str(getattr(trade.status, "value", trade.status)).lower() != "pending":
                await query.edit_message_text(
                    "⚠️ This trade is no longer pending."
                )
                return

            if query.from_user.id != trade.receiver_id:
                try:
                    await query.answer(
                        "❌ This trade is not for you.",
                        show_alert=True,
                    )
                except Exception:
                    pass
                return

            # ------------------------------
            # DECLINE
            # ------------------------------
            if action == "trade_decline":
                trade.status = _trade_status_value(trade, "declined")
                await session.commit()

                await query.edit_message_text(
                    "❌ 𝐓𝐑𝐀𝐃𝐄 𝐃𝐄𝐂𝐋𝐈𝐍𝐄𝐃\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "The trade offer has been declined."
                )

                try:
                    await context.bot.send_message(
                        chat_id=trade.sender_id,
                        text=(
                            "❌ 𝐓𝐑𝐀𝐃𝐄 𝐃𝐄𝐂𝐋𝐈𝐍𝐄𝐃\n"
                            "━━━━━━━━━━━━━━━━━━━━\n"
                            "The other manager declined your trade offer."
                        ),
                    )
                except Exception:
                    pass

                return

            # ------------------------------
            # ACCEPT
            # ------------------------------
            sender_club = await _get_user_club(
                session,
                trade.sender_id,
            )
            receiver_club = await _get_user_club(
                session,
                trade.receiver_id,
            )

            if sender_club is None or receiver_club is None:
                trade.status = _trade_status_value(trade, "cancelled")
                await session.commit()
                await query.edit_message_text(
                    "❌ Trade cancelled: one of the clubs no longer exists."
                )
                return

            offered_ownership = await session.scalar(
                select(ClubPlayer).where(
                    ClubPlayer.club_id == sender_club.id,
                    ClubPlayer.player_id == trade.offered_player_id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            requested_ownership = await session.scalar(
                select(ClubPlayer).where(
                    ClubPlayer.club_id == receiver_club.id,
                    ClubPlayer.player_id == trade.requested_player_id,
                    ClubPlayer.is_current.is_(True),
                )
            )

            if offered_ownership is None or requested_ownership is None:
                trade.status = _trade_status_value(trade, "cancelled")
                await session.commit()
                await query.edit_message_text(
                    "❌ Trade cancelled: one of the players is no longer available."
                )
                return

            offered_player = await session.get(
                Player,
                trade.offered_player_id,
            )
            requested_player = await session.get(
                Player,
                trade.requested_player_id,
            )

            # Swap ownership atomically.
            offered_ownership.club_id = receiver_club.id
            requested_ownership.club_id = sender_club.id
            trade.status = _trade_status_value(trade, "accepted")

            if hasattr(trade, "completed_at"):
                trade.completed_at = datetime.now(timezone.utc)

            await session.commit()

            await query.edit_message_text(
                "✅ 𝐓𝐑𝐀𝐃𝐄 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"⚽ You received : "
                f"{requested_player.name if requested_player else 'Player'}\n"
                f"📤 You gave : "
                f"{offered_player.name if offered_player else 'Player'}"
            )

            # Notify the sender too.
            try:
                await context.bot.send_message(
                    chat_id=trade.sender_id,
                    text=(
                        "✅ 𝐓𝐑𝐀𝐃𝐄 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "The other manager accepted your trade.\n"
                        f"⚽ You gave : "
                        f"{offered_player.name if offered_player else 'Player'}\n"
                        f"📥 You received : "
                        f"{requested_player.name if requested_player else 'Player'}"
                    ),
                )
            except Exception:
                pass

        except Exception:
            await session.rollback()

            # The button must never appear completely dead.
            try:
                await query.edit_message_text(
                    "❌ An error occurred while processing this trade."
                )
            except Exception:
                pass

            raise


trade_response_handler = CallbackQueryHandler(
    trade_response_callback,
    pattern=r"^trade_(accept|decline):[0-9]+$",
)
