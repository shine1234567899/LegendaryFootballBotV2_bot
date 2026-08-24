from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Club


SETINFO_CHOICE = 1
SETINFO_VALUE = 2


def _setinfo_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏷️ CLUB NAME",
                    callback_data="setinfo:name",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🌍 COUNTRY",
                    callback_data="setinfo:country",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏟️ STADIUM",
                    callback_data="setinfo:stadium",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🖼️ LOGO",
                    callback_data="setinfo:logo",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CANCEL",
                    callback_data="setinfo:cancel",
                ),
            ],
        ]
    )


async def _get_my_club(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )
        return result.scalar_one_or_none()


async def setinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return ConversationHandler.END

    club = await _get_my_club(user.id)

    if club is None:
        await message.reply_text(
            "❌ Create your club first."
        )
        return ConversationHandler.END

    await message.reply_text(
        (
            "⚙️ 𝐒𝐄𝐓 𝐂𝐋𝐔𝐁 𝐈𝐍𝐅𝐎\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ {club.name}\n"
            f"🌍 {club.country}\n"
            f"🏟️ {club.stadium_name}\n\n"
            "Choose what you want to change.\n"
            "💰 Coins, 💎 Gems and 👥 players are NOT touched."
        ),
        reply_markup=_setinfo_keyboard(),
    )

    return SETINFO_CHOICE


async def setinfo_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return ConversationHandler.END

    try:
        await query.answer()
    except Exception:
        pass

    action = str(query.data).split(":", 1)[1]

    if action == "cancel":
        await query.edit_message_text(
            "❌ Club information update cancelled."
        )
        return ConversationHandler.END

    prompts = {
        "name": "🏷️ Send the new club name:",
        "country": "🌍 Send the new country:",
        "stadium": "🏟️ Send the new stadium name:",
        "logo": "🖼️ Send the new club logo as a photo.",
    }

    if action not in prompts:
        return ConversationHandler.END

    context.user_data["setinfo_field"] = action

    await query.edit_message_text(
        prompts[action] + "\n\nPress /cancel to stop."
    )

    return SETINFO_VALUE


async def setinfo_value(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return ConversationHandler.END

    field = context.user_data.get("setinfo_field")

    if field is None:
        return ConversationHandler.END

    # Logo must be a Telegram photo so we store file_id, not a local file.
    if field == "logo":
        if not message.photo:
            await message.reply_text(
                "❌ Please send the logo as a photo."
            )
            return SETINFO_VALUE

        logo_file_id = message.photo[-1].file_id

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Club).where(Club.owner_id == user.id)
            )
            club = result.scalar_one_or_none()

            if club is None:
                await message.reply_text(
                    "❌ Club not found."
                )
                return ConversationHandler.END

            club.logo_file_id = logo_file_id
            await session.commit()

        await message.reply_text(
            "✅ Club logo updated.",
            reply_markup=_setinfo_keyboard(),
        )
        return SETINFO_CHOICE

    if not message.text:
        await message.reply_text(
            "❌ Please send text for this information."
        )
        return SETINFO_VALUE

    value = message.text.strip()

    if not value:
        await message.reply_text(
            "❌ The value cannot be empty."
        )
        return SETINFO_VALUE

    if len(value) > 100:
        await message.reply_text(
            "❌ Maximum length is 100 characters."
        )
        return SETINFO_VALUE

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user.id)
        )
        club = result.scalar_one_or_none()

        if club is None:
            await message.reply_text(
                "❌ Club not found."
            )
            return ConversationHandler.END

        if field == "name":
            club.name = value
        elif field == "country":
            club.country = value
        elif field == "stadium":
            club.stadium_name = value
        else:
            await message.reply_text(
                "❌ Invalid information field."
            )
            return ConversationHandler.END

        await session.commit()

    labels = {
        "name": "🏷️ Club name",
        "country": "🌍 Country",
        "stadium": "🏟️ Stadium",
    }

    await message.reply_text(
        f"✅ {labels[field]} updated successfully.",
        reply_markup=_setinfo_keyboard(),
    )

    return SETINFO_CHOICE


async def setinfo_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("setinfo_field", None)

    if update.message:
        await update.message.reply_text(
            "❌ Club information update cancelled."
        )

    return ConversationHandler.END


setinfo_handler = ConversationHandler(
    entry_points=[
        CommandHandler("setinfo", setinfo),
    ],
    states={
        SETINFO_CHOICE: [
            CallbackQueryHandler(
                setinfo_choice,
                pattern=r"^setinfo:(name|country|stadium|logo|cancel)$",
            ),
        ],
        SETINFO_VALUE: [
            MessageHandler(
                filters.PHOTO | (filters.TEXT & ~filters.COMMAND),
                setinfo_value,
            ),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", setinfo_cancel),
    ],
    allow_reentry=True,
)