from __future__ import annotations

from datetime import date
import secrets

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from life_world.database import (
    ensure_life_tables,
    get_life_character,
    create_life_character,
    xp_required_for_next_age,
)


FIRST_NAME, NATIONALITY, GENDER, RESIDENCE = range(4)

COUNTRIES = [
    ("🇨🇲 Cameroun", "Cameroun"),
    ("🇫🇷 France", "France"),
    ("🇨🇮 Côte d'Ivoire", "Côte d'Ivoire"),
    ("🇨🇩 RD Congo", "RD Congo"),
    ("🇸🇳 Sénégal", "Sénégal"),
    ("🇬🇦 Gabon", "Gabon"),
    ("🇨🇬 Congo", "Congo"),
    ("🇬🇳 Guinée", "Guinée"),
    ("🇹🇬 Togo", "Togo"),
    ("🇳🇬 Nigeria", "Nigeria"),
    ("🇬🇭 Ghana", "Ghana"),
    ("🇧🇯 Bénin", "Bénin"),
    ("🇲🇱 Mali", "Mali"),
    ("🇧🇫 Burkina Faso", "Burkina Faso"),
    ("🇩🇪 Allemagne", "Allemagne"),
    ("🇬🇧 Royaume-Uni", "Royaume-Uni"),
    ("🇺🇸 États-Unis", "États-Unis"),
    ("🇨🇦 Canada", "Canada"),
    ("🇧🇪 Belgique", "Belgique"),
    ("🇨🇭 Suisse", "Suisse"),
]


def generated_birth_date_for_game_age(age: int = 9) -> date:
    """Birth date is generated for display; it does not drive aging."""
    today = date.today()
    try:
        return today.replace(year=today.year - age)
    except ValueError:
        return date(today.year - age, 2, 28)


def generate_life_id() -> str:
    return f"LW-{secrets.randbelow(900000) + 100000}"


def country_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []

    for label, value in COUNTRIES:
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"lwcountry:{value}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👨 Homme",
                    callback_data="lwgender:Homme",
                ),
                InlineKeyboardButton(
                    "👩 Femme",
                    callback_data="lwgender:Femme",
                ),
            ]
        ]
    )


async def life(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await ensure_life_tables()

    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return ConversationHandler.END

    character = await get_life_character(user.id)

    if character:
        age = int(character["age"] or 9)
        xp = int(character["experience"] or 0)
        required = int(
            character["experience_required"]
            or xp_required_for_next_age(age)
        )

        family = character["family_name"] or "Aucune"

        await message.reply_text(
            "🌍 𝐌𝐀𝐍𝐔𝐖𝐎𝐑𝐋𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {character['first_name']}"
            f"{' ' + family if family != 'Aucune' else ''}\n"
            f"🎂 Âge : {age} ans\n"
            f"⭐ Expérience : {xp}/{required} XP\n"
            f"📈 Niveau : {character['life_level']}\n"
            f"🇺🇳 Nationalité : {character['nationality']}\n"
            f"⚧ Sexe : {character['gender']}\n"
            f"📍 Résidence : {character['residence_country']}\n\n"
            f"💵 Balance : {character['balance']:,} LC\n"
            f"🏦 Banque : {character['balance_bank']:,} LC\n"
            f"🎓 Scolarité : {character['education_level']}\n"
            f"🪪 Carte d'identité : "
            f"{'✅' if character['identity_card'] else '❌'}\n"
            f"🆔 Life ID : `{character['life_id']}`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await message.reply_text(
        "🌍 𝐌𝐀𝐍𝐔𝐖𝐎𝐑𝐋𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Bienvenue dans MANUWORLD.\n\n"
        "🎂 Tu commences à 9 ans.\n"
        "⭐ Ton âge évoluera avec ton expérience de jeu.\n"
        "⏳ Le temps réel ne fait PAS automatiquement vieillir "
        "ton personnage.\n\n"
        "👤 Étape 1/4\n"
        "Quel est ton prénom ?"
    )
    return FIRST_NAME


async def first_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return FIRST_NAME

    name = message.text.strip()

    if not 1 <= len(name) <= 80:
        await message.reply_text("❌ Prénom invalide.")
        return FIRST_NAME

    context.user_data["lw_name"] = name

    await message.reply_text(
        "🌍 Étape 2/4\n\n"
        "Choisis ta nationalité :",
        reply_markup=country_keyboard(),
    )
    return NATIONALITY


async def nationality(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return NATIONALITY

    await query.answer()

    if not query.data.startswith("lwcountry:"):
        return NATIONALITY

    context.user_data["lw_nat"] = query.data.split(":", 1)[1]

    await query.edit_message_text(
        "⚧️ Étape 3/4\n\n"
        "Choisis ton sexe :",
        reply_markup=gender_keyboard(),
    )
    return GENDER


async def gender(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return GENDER

    await query.answer()

    if not query.data.startswith("lwgender:"):
        return GENDER

    context.user_data["lw_gender"] = query.data.split(":", 1)[1]

    await query.edit_message_text(
        "📍 Étape 4/4\n\n"
        "Dans quel pays vis-tu ?"
    )
    return RESIDENCE


async def residence(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return RESIDENCE

    residence_country = message.text.strip()

    if not 1 <= len(residence_country) <= 80:
        await message.reply_text("❌ Pays invalide.")
        return RESIDENCE

    birth_date = generated_birth_date_for_game_age(9)
    life_id = generate_life_id()

    name = context.user_data["lw_name"]
    nationality_value = context.user_data["lw_nat"]
    gender_value = context.user_data["lw_gender"]

    await create_life_character(
        telegram_id=user.id,
        first_name=name,
        nationality=nationality_value,
        gender=gender_value,
        residence_country=residence_country,
        birth_date=birth_date,
        life_id=life_id,
    )

    for key in ("lw_name", "lw_nat", "lw_gender"):
        context.user_data.pop(key, None)

    await message.reply_text(
        "🎉 𝐏𝐄𝐑𝐒𝐎𝐍𝐍𝐀𝐆𝐄 𝐂𝐑ÉÉ !\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n"
        "🎂 Âge : 9 ans\n"
        f"📅 Naissance : {birth_date.strftime('%d/%m/%Y')}\n"
        f"🇺🇳 Nationalité : {nationality_value}\n"
        f"⚧ Sexe : {gender_value}\n"
        f"📍 Résidence : {residence_country}\n\n"
        "⭐ Expérience : 0/100 XP\n"
        "📈 Niveau : 1\n"
        "👨‍👩‍👧‍👦 Famille : Aucune\n"
        "💵 Balance : 0 LC\n"
        "🏦 Balance Bank : 0 LC\n"
        "🎓 Scolarité : École primaire\n"
        "🪪 Carte d'identité : ❌\n\n"
        f"🆔 Life ID : `{life_id}`",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    for key in ("lw_name", "lw_nat", "lw_gender"):
        context.user_data.pop(key, None)

    message = update.effective_message
    if message:
        await message.reply_text(
            "❌ Création MANUWORLD annulée."
        )

    return ConversationHandler.END


life_handler = ConversationHandler(
    entry_points=[
        CommandHandler("life", life),
    ],
    states={
        FIRST_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                first_name,
            )
        ],
        NATIONALITY: [
            CallbackQueryHandler(
                nationality,
                pattern=r"^lwcountry:",
            )
        ],
        GENDER: [
            CallbackQueryHandler(
                gender,
                pattern=r"^lwgender:",
            )
        ],
        RESIDENCE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                residence,
            )
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
    ],
    per_message=False,
    allow_reentry=True,
)
