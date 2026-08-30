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


# ============================================================
# ÉTAPES DE CRÉATION
# ============================================================

FIRST_NAME, NATIONALITY, GENDER, RESIDENCE = range(4)


# ============================================================
# PAYS
# ============================================================

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


# ============================================================
# DATE DE NAISSANCE
# ============================================================

def generated_birth_date_for_game_age(
    age: int = 9,
) -> date:
    """
    Génère une date de naissance correspondant à l'âge
    de départ du personnage.

    Le temps réel ne contrôle pas le vieillissement.
    """

    today = date.today()

    try:

        return today.replace(
            year=today.year - age
        )

    except ValueError:

        return date(
            today.year - age,
            2,
            28,
        )


# ============================================================
# LIFE ID
# ============================================================

def generate_life_id() -> str:

    return (
        f"LW-"
        f"{secrets.randbelow(900000) + 100000}"
    )


# ============================================================
# CLAVIER PAYS
# ============================================================

def country_keyboard() -> InlineKeyboardMarkup:

    rows = []
    row = []

    for label, value in COUNTRIES:

        row.append(
            InlineKeyboardButton(
                label,
                callback_data=(
                    f"lwcountry:{value}"
                ),
            )
        )

        if len(row) == 2:

            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(
        rows
    )


# ============================================================
# CLAVIER PAYS DE RÉSIDENCE
# ============================================================

def residence_country_keyboard() -> InlineKeyboardMarkup:

    rows = []
    row = []

    for label, value in COUNTRIES:

        row.append(
            InlineKeyboardButton(
                label,
                callback_data=(
                    f"lwresidence:{value}"
                ),
            )
        )

        if len(row) == 2:

            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(
        rows
    )


# ============================================================
# CLAVIER SEXE
# ============================================================

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


# ============================================================
# /LIFE
# ============================================================

async def life(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await ensure_life_tables()

    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:

        return ConversationHandler.END

    character = await get_life_character(
        user.id
    )

    # --------------------------------------------------------
    # PERSONNAGE EXISTANT
    # --------------------------------------------------------

    if character:

        age = int(
            character["age"] or 9
        )

        xp = int(
            character["experience"] or 0
        )

        required = int(
            character["experience_required"]
            or xp_required_for_next_age(age)
        )

        family = (
            character["family_name"]
            or "Aucune"
        )

        await message.reply_text(
            "🌍 𝐌𝐀𝐍𝐔𝐖𝐎𝐑𝐋𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            f"👤 {character['first_name']}"
            f"{' ' + family if family != 'Aucune' else ''}\n"

            f"🎂 Âge : {age} ans\n"

            f"⭐ Expérience : "
            f"{xp}/{required} XP\n"

            f"📈 Niveau : "
            f"{character['life_level']}\n"

            f"🇺🇳 Nationalité : "
            f"{character['nationality']}\n"

            f"⚧ Sexe : "
            f"{character['gender']}\n"

            f"📍 Résidence : "
            f"{character['residence_country']}\n\n"

            f"💵 Balance : "
            f"{character['balance']:,} LC\n"

            f"🏦 Banque : "
            f"{character['balance_bank']:,} LC\n"

            f"🎓 Scolarité : "
            f"{character['education_level']}\n"

            f"🪪 Carte d'identité : "
            f"{'✅' if character['identity_card'] else '❌'}\n"

            f"🆔 Life ID : "
            f"`{character['life_id']}`",

            parse_mode="Markdown",
        )

        return ConversationHandler.END

    # --------------------------------------------------------
    # NOUVEAU PERSONNAGE
    # --------------------------------------------------------

    await message.reply_text(
        "🌍 𝐌𝐀𝐍𝐔𝐖𝐎𝐑𝐋𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "Bienvenue dans MANUWORLD.\n\n"

        "🎂 Tu commences à 9 ans.\n"
        "⭐ Ton âge évoluera avec ton "
        "expérience de jeu.\n"

        "⏳ Le temps réel ne fait PAS "
        "automatiquement vieillir ton personnage.\n\n"

        "👤 Étape 1/4\n"
        "Quel est ton prénom ?"
    )

    return FIRST_NAME


# ============================================================
# PRÉNOM
# ============================================================

async def first_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:

        return FIRST_NAME

    name = (
        message.text or ""
    ).strip()

    if not 1 <= len(name) <= 80:

        await message.reply_text(
            "❌ Prénom invalide.\n\n"
            "Entre un prénom de 1 à 80 caractères."
        )

        return FIRST_NAME

    context.user_data[
        "lw_name"
    ] = name

    await message.reply_text(
        "🌍 Étape 2/4\n\n"
        "Choisis ta nationalité :",
        reply_markup=country_keyboard(),
    )

    return NATIONALITY


# ============================================================
# NATIONALITÉ
# ============================================================

async def nationality(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:

        return NATIONALITY

    await query.answer()

    data = query.data or ""

    if not data.startswith(
        "lwcountry:"
    ):

        return NATIONALITY

    nationality_value = data.split(
        ":",
        1,
    )[1].strip()

    if not nationality_value:

        return NATIONALITY

    context.user_data[
        "lw_nat"
    ] = nationality_value

    await query.edit_message_text(
        "⚧️ Étape 3/4\n\n"
        "Choisis ton sexe :",
        reply_markup=gender_keyboard(),
    )

    return GENDER


# ============================================================
# SEXE
# ============================================================

async def gender(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:

        return GENDER

    await query.answer()

    data = query.data or ""

    if not data.startswith(
        "lwgender:"
    ):

        return GENDER

    gender_value = data.split(
        ":",
        1,
    )[1].strip()

    if not gender_value:

        return GENDER

    context.user_data[
        "lw_gender"
    ] = gender_value

    # IMPORTANT :
    # Avant, l'étape résidence demandait du texte libre.
    # Maintenant, elle utilise un clavier pays comme
    # la nationalité.

    await query.edit_message_text(
        "📍 Étape 4/4\n\n"
        "Dans quel pays vis-tu ?\n\n"
        "Choisis ton pays de résidence :",
        reply_markup=(
            residence_country_keyboard()
        ),
    )

    return RESIDENCE


# ============================================================
# RÉSIDENCE
# ============================================================

async def residence(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:

        return RESIDENCE

    await query.answer()

    data = query.data or ""

    if not data.startswith(
        "lwresidence:"
    ):

        return RESIDENCE

    residence_country = data.split(
        ":",
        1,
    )[1].strip()

    if not residence_country:

        await query.answer(
            "❌ Pays invalide.",
            show_alert=True,
        )

        return RESIDENCE

    user = update.effective_user

    if user is None:

        return ConversationHandler.END

    # --------------------------------------------------------
    # RÉCUPÉRATION DES DONNÉES
    # --------------------------------------------------------

    name = context.user_data.get(
        "lw_name"
    )

    nationality_value = (
        context.user_data.get(
            "lw_nat"
        )
    )

    gender_value = (
        context.user_data.get(
            "lw_gender"
        )
    )

    if not name or not nationality_value or not gender_value:

        await query.edit_message_text(
            "❌ Les données de création "
            "sont incomplètes.\n\n"
            "Utilise à nouveau /life."
        )

        for key in (
            "lw_name",
            "lw_nat",
            "lw_gender",
        ):

            context.user_data.pop(
                key,
                None,
            )

        return ConversationHandler.END

    # --------------------------------------------------------
    # CRÉATION
    # --------------------------------------------------------

    birth_date = (
        generated_birth_date_for_game_age(
            9
        )
    )

    life_id = generate_life_id()

    telegram_username = (
        user.username
        if user.username
        else None
    )

    telegram_last_name = (
        user.last_name
        if user.last_name
        else None
    )

    try:

        await create_life_character(

            telegram_id=user.id,

            username=telegram_username,

            first_name=name,

            last_name=telegram_last_name,

            nationality=nationality_value,

            gender=gender_value,

            residence_country=(
                residence_country
            ),

            residence_city=None,

            birth_date=birth_date,

            life_id=life_id,
        )

    except Exception as error:

        print(
            "❌ [MWL] Character creation error:",
            type(error).__name__,
            error,
        )

        await query.edit_message_text(
            "❌ Une erreur est survenue "
            "pendant la création de ton personnage.\n\n"
            "Réessaie avec /life."
        )

        return ConversationHandler.END

    # --------------------------------------------------------
    # NETTOYAGE
    # --------------------------------------------------------

    for key in (
        "lw_name",
        "lw_nat",
        "lw_gender",
    ):

        context.user_data.pop(
            key,
            None,
        )

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    await query.edit_message_text(
        "🎉 𝐏𝐄𝐑𝐒𝐎𝐍𝐍𝐀𝐆𝐄 𝐂𝐑ÉÉ !\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 {name}\n"

        "🎂 Âge : 9 ans\n"

        f"📅 Naissance : "
        f"{birth_date.strftime('%d/%m/%Y')}\n"

        f"🇺🇳 Nationalité : "
        f"{nationality_value}\n"

        f"⚧ Sexe : "
        f"{gender_value}\n"

        f"📍 Résidence : "
        f"{residence_country}\n\n"

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


# ============================================================
# ANNULATION
# ============================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    for key in (
        "lw_name",
        "lw_nat",
        "lw_gender",
    ):

        context.user_data.pop(
            key,
            None,
        )

    message = update.effective_message

    if message:

        await message.reply_text(
            "❌ Création MANUWORLD annulée."
        )

    return ConversationHandler.END


# ============================================================
# CONVERSATION HANDLER
# ============================================================

life_handler = ConversationHandler(

    entry_points=[
        CommandHandler(
            "life",
            life,
        ),
    ],

    states={

        # ----------------------------------------------------
        # PRÉNOM
        # ----------------------------------------------------

        FIRST_NAME: [

            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND,
                first_name,
            ),

        ],

        # ----------------------------------------------------
        # NATIONALITÉ
        # ----------------------------------------------------

        NATIONALITY: [

            CallbackQueryHandler(
                nationality,
                pattern=r"^lwcountry:",
            ),

        ],

        # ----------------------------------------------------
        # SEXE
        # ----------------------------------------------------

        GENDER: [

            CallbackQueryHandler(
                gender,
                pattern=r"^lwgender:",
            ),

        ],

        # ----------------------------------------------------
        # RÉSIDENCE
        # ----------------------------------------------------

        RESIDENCE: [

            CallbackQueryHandler(
                residence,
                pattern=r"^lwresidence:",
            ),

        ],

    },

    fallbacks=[

        CommandHandler(
            "cancel",
            cancel,
        ),

    ],

    per_message=False,

    allow_reentry=True,
)