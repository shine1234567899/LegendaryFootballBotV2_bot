from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import select
from telegram.ext import CallbackQueryHandler
from datetime import datetime, timezone
from database.models import TransferListing

from database.database import AsyncSessionLocal
from database.models import Player
from config import OWNER_IDS


NAME, COUNTRY, POSITION, AGE, OVERALL, POTENTIAL, CURRENCY, VALUE, IMAGE = range(9)


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


async def addplayer_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ You are not authorized to use this command."
        )
        return ConversationHandler.END

    context.user_data.pop("addplayer", None)

    await update.message.reply_text(
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n"
        "        𝗔𝗗𝗗 𝗣𝗟𝗔𝗬𝗘𝗥\n"
        "⚜️━━━━━━━━━━━━━━━━━━━━⚜️\n\n"
        "👤 Enter the player's name:"
    )

    return NAME


async def addplayer_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["addplayer"] = {
        "name": update.message.text.strip()
    }

    await update.message.reply_text(
        "🌍 Enter the player's country:"
    )

    return COUNTRY


async def addplayer_country(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["addplayer"]["country"] = update.message.text.strip()

    await update.message.reply_text(
        "📍 Enter the player's position:\n\n"
        "GK / DEF / MID / ATT"
    )

    return POSITION


async def addplayer_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    position = update.message.text.strip().upper()

    if position not in {"GK", "DEF", "MID", "ATT"}:
        await update.message.reply_text(
            "❌ Invalid position.\n\n"
            "Use: GK, DEF, MID or ATT."
        )
        return POSITION

    context.user_data["addplayer"]["position"] = position

    await update.message.reply_text(
        "🎂 Enter the player's age:"
    )

    return AGE


async def addplayer_age(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        age = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Age must be a number."
        )
        return AGE

    if age < 15 or age > 50:
        await update.message.reply_text(
            "❌ Enter a valid age between 15 and 50."
        )
        return AGE

    context.user_data["addplayer"]["age"] = age

    await update.message.reply_text(
        "⭐ Enter the player's Overall:"
    )

    return OVERALL


async def addplayer_overall(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        overall = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Overall must be a number."
        )
        return OVERALL

    if overall < 1 or overall > 99:
        await update.message.reply_text(
            "❌ Overall must be between 1 and 99."
        )
        return OVERALL

    context.user_data["addplayer"]["overall"] = overall

    await update.message.reply_text(
        "📈 Enter the player's Potential:"
    )

    return POTENTIAL


async def addplayer_potential(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        potential = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Potential must be a number."
        )
        return POTENTIAL

    if potential < 1 or potential > 99:
        await update.message.reply_text(
            "❌ Potential must be between 1 and 99."
        )
        return POTENTIAL

    context.user_data["addplayer"]["potential"] = potential

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 COINS",
                callback_data="addplayer_currency_coins",
            ),
            InlineKeyboardButton(
                "💎 GEMS",
                callback_data="addplayer_currency_gems",
            ),
        ]
    ])

    await update.message.reply_text(
        "💳 Choose the player's selling currency:",
        reply_markup=keyboard,
    )

    return CURRENCY
async def addplayer_currency(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return ConversationHandler.END

    await query.answer()

    if query.data == "addplayer_currency_coins":
        currency = "COINS"
        message = "💰 Enter the player's value in Coins:"

    elif query.data == "addplayer_currency_gems":
        currency = "GEMS"
        message = "💎 Enter the player's value in Gems:"

    else:
        return CURRENCY

    context.user_data["addplayer"]["currency"] = currency

    await query.edit_message_text(message)

    return VALUE


async def addplayer_value(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        value = int(update.message.text.strip().replace(",", ""))
    except ValueError:
        await update.message.reply_text(
            "❌ Value must be a number."
        )
        return VALUE

    if value <= 0:
        await update.message.reply_text(
            "❌ Value must be greater than 0."
        )
        return VALUE

    context.user_data["addplayer"]["value"] = value

    await update.message.reply_text(
        "🖼️ Send the player's photo now.\n\n"
        "Or type /skip if you don't want to add a photo."
    )

    return IMAGE


async def addplayer_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.message.photo:
        context.user_data["addplayer"]["image_file_id"] = (
            update.message.photo[-1].file_id
        )
    else:
        await update.message.reply_text(
            "❌ Please send a photo or use /skip."
        )
        return IMAGE

    return await save_player(update, context)


async def addplayer_skip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["addplayer"]["image_file_id"] = None

    return await save_player(update, context)


async def save_player(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    data = context.user_data.get("addplayer")

    if not data:
        await update.message.reply_text(
            "❌ Player data was lost. Please use /addplayer again."
        )
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(Player).where(
                Player.name.ilike(data["name"])
            )
        )

        if existing.scalar_one_or_none():
            await update.message.reply_text(
                "❌ A player with this name already exists."
            )
            context.user_data.pop("addplayer", None)
            return ConversationHandler.END

        player = Player(
            name=data["name"],
            country=data["country"],
            position=data["position"],
            age=data["age"],
            overall=data["overall"],
            potential=data["potential"],
            value=data["value"],
            image_file_id=data.get("image_file_id"),
            starter_pool=False,
        )

        session.add(player)
        await session.commit()
        await session.refresh(player)

        # Create the transfer-market listing with the same active session.
        # The previous version tried to use `session` after the async
        # session context had already been closed.
        listing = TransferListing(
            player_id=player.id,
            price=player.value,
            currency=data["currency"],
            status="available",
            listed_at=datetime.now(timezone.utc),
        )

        session.add(listing)
        await session.commit()

    context.user_data.pop("addplayer", None)

    market_status = (
        "🔥 Eligible for Transfer Market"
        if player.overall >= 78
        else "ℹ️ Not eligible for Transfer Market (OVR below 78)"
    )

    await update.message.reply_text(
        "✅ 𝗣𝗟𝗔𝗬𝗘𝗥 𝗔𝗗𝗗𝗘𝗗\n\n"
        f"👤 {player.name}\n"
        f"🌍 {player.country}\n"
        f"📍 {player.position}\n"
        f"🎂 Age: {player.age}\n"
        f"⭐ Overall: {player.overall}\n"
        f"📈 Potential: {player.potential}\n"
        f"{'💰 Coins' if data['currency'] == 'COINS' else '💎 Gems'}: "
f"{player.value:,}\n\n"
        f"🔒 Starter Pool: FALSE\n"
        f"{market_status}"
    )

    return ConversationHandler.END


addplayer_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Regex(r"^/addplayer$"),
            addplayer_start,
        )
    ],
    states={
        NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_name,
            )
        ],
        COUNTRY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_country,
            )
        ],
        POSITION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_position,
            )
        ],
        AGE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_age,
            )
        ],
        OVERALL: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_overall,
            )
        ],
        POTENTIAL: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_potential,
            )
        ],
        CURRENCY: [
            CallbackQueryHandler(
                addplayer_currency,
                pattern=r"^addplayer_currency_(coins|gems)$",
    ),
],
        VALUE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                addplayer_value,
            )
        ],
        IMAGE: [
            MessageHandler(
                filters.PHOTO,
                addplayer_image,
            ),
            MessageHandler(
                filters.Regex(r"^/skip$"),
                addplayer_skip,
            ),
        ],
    },
    fallbacks=[],
)