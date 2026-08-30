"""
MANUWORLD - education.py

Système scolaire compatible avec la database MANUWORLD actuelle.

Parcours :
    École primaire / CM2  -> CEP
    Collège / 3e          -> BEPC
    Lycée / Première      -> Probatoire
    Lycée / Terminale     -> Baccalauréat
    Études supérieures    -> Université
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from life_world.database import AsyncSessionLocal, get_life_character


# ============================================================
# PARCOURS SCOLAIRE
# ============================================================

SCHOOL_LEVELS = [
    {
        "key": "primary",
        "education_level": "École primaire",
        "class_name": "CM2",
        "diploma": "CEP",
        "next_level": "Collège",
        "next_class": "3e",
        "next_diploma": "BEPC",
        "min_age": 9,
        "max_age": 13,
    },
    {
        "key": "college",
        "education_level": "Collège",
        "class_name": "3e",
        "diploma": "BEPC",
        "next_level": "Lycée",
        "next_class": "Première",
        "next_diploma": "Probatoire",
        "min_age": 14,
        "max_age": 17,
    },
    {
        "key": "high_school",
        "education_level": "Lycée",
        "class_name": "Première",
        "diploma": "Probatoire",
        "next_level": "Lycée",
        "next_class": "Terminale",
        "next_diploma": "Baccalauréat",
        "min_age": 16,
        "max_age": 19,
    },
    {
        "key": "terminal",
        "education_level": "Lycée",
        "class_name": "Terminale",
        "diploma": "Baccalauréat",
        "next_level": "Études supérieures",
        "next_class": "Université",
        "next_diploma": None,
        "min_age": 17,
        "max_age": 21,
    },
    {
        "key": "university",
        "education_level": "Études supérieures",
        "class_name": "Université",
        "diploma": None,
        "next_level": None,
        "next_class": None,
        "next_diploma": None,
        "min_age": 18,
        "max_age": 99,
    },
]


# ============================================================
# DOMAINES + CONFIGURATION DES EXAMENS
# ============================================================

EDUCATION_DOMAINS = {
    "general": "📚 Général",
    "science": "🔬 Sciences",
    "technology": "💻 Technologie",
    "economics": "📊 Économie",
    "law": "⚖️ Droit",
    "medicine": "🩺 Médecine",
    "literature": "📖 Littérature",
    "engineering": "⚙️ Ingénierie",
}

EXAM_QUESTION_COUNT = {
    "primary": 5,
    "college": 7,
    "high_school": 10,
    "terminal": 12,
    "university": 15,
}

EXAM_PASS_REQUIRED = {
    "primary": 4,
    "college": 5,
    "high_school": 8,
    "terminal": 10,
    "university": 15,
}


def normalize_domain(domain: str) -> str:
    aliases = {
        "general": "general",
        "général": "general",
        "science": "science",
        "sciences": "science",
        "technology": "technology",
        "technologie": "technology",
        "economics": "economics",
        "economie": "economics",
        "économie": "economics",
        "law": "law",
        "droit": "law",
        "medicine": "medicine",
        "medecine": "medicine",
        "médecine": "medicine",
        "literature": "literature",
        "litterature": "literature",
        "littérature": "literature",
        "engineering": "engineering",
        "ingenierie": "engineering",
        "ingénierie": "engineering",
    }

    value = str(domain).strip().lower()

    if value not in aliases:
        raise ValueError("Domaine scolaire inconnu.")

    return aliases[value]


def get_character_domain(character) -> str | None:
    value = character.get("education_domain")

    if not value:
        return None

    try:
        return normalize_domain(value)
    except ValueError:
        return None


def build_domain_keyboard() -> InlineKeyboardMarkup:
    keys = list(EDUCATION_DOMAINS)
    rows = []

    for index in range(0, len(keys), 2):
        rows.append([
            InlineKeyboardButton(
                EDUCATION_DOMAINS[key],
                callback_data=f"edu_domain:{key}",
            )
            for key in keys[index:index + 2]
        ])

    return InlineKeyboardMarkup(rows)


async def save_education_domain(
    character_id: int,
    domain: str,
) -> bool:
    domain = normalize_domain(domain)

    async with AsyncSessionLocal() as session:
        # Migration légère : les anciens personnages sont conservés.
        await session.execute(
            text(
                """
                ALTER TABLE life_characters
                ADD COLUMN IF NOT EXISTS education_domain VARCHAR(80)
                """
            )
        )

        result = await session.execute(
            text(
                """
                UPDATE life_characters
                SET education_domain = :domain,
                    updated_at = NOW()
                WHERE id = :character_id
                RETURNING id
                """
            ),
            {
                "domain": domain,
                "character_id": character_id,
            },
        )

        ok = result.first() is not None
        await session.commit()

    return ok


# ============================================================
# OUTILS
# ============================================================

async def get_actor(update: Update):
    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)


def current_level(character) -> dict:
    education = str(
        character.get("education_level")
        or "École primaire"
    ).strip().lower()

    diploma = str(
        character.get("diploma_level")
        or ""
    ).strip().lower()

    if "univers" in education or "supérieur" in education:
        return SCHOOL_LEVELS[4]

    if "terminal" in education or "baccalauréat" in diploma:
        return SCHOOL_LEVELS[3]

    if "lycée" in education or "lycee" in education:
        return SCHOOL_LEVELS[2]

    if "collège" in education or "college" in education:
        return SCHOOL_LEVELS[1]

    return SCHOOL_LEVELS[0]


def character_age(character) -> int:
    try:
        return int(character.get("age") or 0)
    except (TypeError, ValueError):
        return 0


def safe_name(character) -> str:
    username = character.get("username")

    if username:
        return f"@{username}"

    return " ".join(
        value
        for value in (
            character.get("first_name"),
            character.get("last_name"),
        )
        if value
    ) or "Joueur"


# ============================================================
# ANNÉE SCOLAIRE
# ============================================================

async def ensure_active_school_year(
    session,
    character_id: int,
    level: dict,
):
    result = await session.execute(
        text(
            """
            SELECT id
            FROM life_school_years
            WHERE character_id = :character_id
              AND result = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"character_id": character_id},
    )

    existing = result.first()

    if existing:
        return existing[0]

    result = await session.execute(
        text(
            """
            INSERT INTO life_school_years (
                character_id,
                class_name,
                academic_year,
                result
            )
            VALUES (
                :character_id,
                :class_name,
                :academic_year,
                'in_progress'
            )
            RETURNING id
            """
        ),
        {
            "character_id": character_id,
            "class_name": level["class_name"],
            "academic_year": datetime.now(
                timezone.utc
            ).year,
        },
    )

    row = result.first()

    return row[0] if row else None


async def get_active_school_year(
    session,
    character_id: int,
):
    result = await session.execute(
        text(
            """
            SELECT
                id,
                class_name,
                academic_year,
                average,
                result
            FROM life_school_years
            WHERE character_id = :character_id
              AND result = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"character_id": character_id},
    )

    return result.mappings().first()


# ============================================================
# /SCHOOL
# ============================================================

async def school_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Tu n'as pas encore créé ton personnage MANUWORLD."
        )
        return

    level = current_level(character)

    async with AsyncSessionLocal() as session:

        school_year = await get_active_school_year(
            session,
            character["id"],
        )

        if school_year is None:
            await ensure_active_school_year(
                session,
                character["id"],
                level,
            )
            await session.commit()

            school_year = await get_active_school_year(
                session,
                character["id"],
            )

    average = (
        float(school_year["average"])
        if school_year
        and school_year["average"] is not None
        else 0.0
    )

    diploma = (
        level["diploma"]
        or character.get("diploma_level")
        or "Aucun"
    )

    lines = [
        "🎓 **PARCOURS SCOLAIRE**",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 Élève : **{safe_name(character)}**",
        f"🏫 Niveau : **{level['education_level']}**",
        f"📚 Classe : **{level['class_name']}**",
        f"📜 Diplôme : **{diploma}**",
        f"📊 Moyenne actuelle : **{average:.2f}/100**",
        "",
    ]

    if level["next_level"]:
        lines.extend(
            [
                "➡️ **Prochaine étape**",
                f"🏫 {level['next_level']}",
                f"📚 {level['next_class']}",
            ]
        )

        if level["next_diploma"]:
            lines.append(
                f"📜 Diplôme : {level['next_diploma']}"
            )
    else:
        lines.append(
            "🎓 Tu es arrivé aux études supérieures."
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# ============================================================
# /STUDY
# ============================================================

async def study_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    level = current_level(character)

    if level["key"] == "university":
        await message.reply_text(
            "🎓 Tu es déjà dans les études supérieures."
        )
        return

    age = character_age(character)

    if age < level["min_age"]:
        await message.reply_text(
            "❌ Ton âge actuel ne correspond pas encore "
            "à ce niveau scolaire."
        )
        return

    async with AsyncSessionLocal() as session:

        school_year = await get_active_school_year(
            session,
            character["id"],
        )

        if school_year is None:
            await ensure_active_school_year(
                session,
                character["id"],
                level,
            )

            await session.commit()

            school_year = await get_active_school_year(
                session,
                character["id"],
            )

        current_average = (
            float(school_year["average"])
            if school_year
            and school_year["average"] is not None
            else 0.0
        )

        increase = 5.0

        new_average = min(
            100.0,
            current_average + increase,
        )

        await session.execute(
            text(
                """
                UPDATE life_school_years
                SET average = :average
                WHERE id = :id
                """
            ),
            {
                "average": new_average,
                "id": school_year["id"],
            },
        )

        await session.commit()

    await message.reply_text(
        "📚 **SESSION D'ÉTUDE TERMINÉE**\n\n"
        f"✨ Progression : **+{increase:.0f} points**\n"
        f"📊 Moyenne : **{new_average:.2f}/100**\n\n"
        "Continue à étudier avant de passer ton examen.",
        parse_mode="Markdown",
    )


# ============================================================
# /EXAM
# ============================================================

async def exam_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Prépare l'examen correspondant au niveau.

    CEP        : 5 questions, 4 requises
    BEPC       : 7 questions, 5 requises
    Probatoire : 10 questions, 8 requises
    BACC       : 12 questions, 10 requises
    Université : 15 questions, 15 requises

    Les questions seront ensuite tirées de la banque
    correspondant au niveau + domaine.
    """
    message = update.effective_message

    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    level = current_level(character)

    if level["key"] == "university":
        await message.reply_text(
            "🎓 Tu es déjà dans les études supérieures."
        )
        return

    age = character_age(character)

    if age < level["min_age"]:
        await message.reply_text(
            "❌ Tu es encore trop jeune pour passer cet examen."
        )
        return

    domain = get_character_domain(character)

    if level["key"] != "primary" and domain is None:
        await message.reply_text(
            "🎯 <b>DOMAINE REQUIS</b>\n\n"
            "À partir du collège, choisis le domaine dans lequel "
            "tu souhaites évoluer avant de passer l'examen.",
            reply_markup=build_domain_keyboard(),
            parse_mode="HTML",
        )
        return

    async with AsyncSessionLocal() as session:
        school_year = await get_active_school_year(
            session,
            character["id"],
        )

        if school_year is None:
            await ensure_active_school_year(
                session,
                character["id"],
                level,
            )
            await session.commit()

            school_year = await get_active_school_year(
                session,
                character["id"],
            )

        average = (
            float(school_year["average"])
            if school_year
            and school_year["average"] is not None
            else 0.0
        )

    if average < 50:
        await message.reply_text(
            "❌ <b>EXAMEN NON AUTORISÉ</b>\n\n"
            f"📊 Moyenne : <b>{average:.2f}/100</b>\n"
            "🎯 Minimum requis : <b>50/100</b>\n\n"
            "Continue tes études.",
            parse_mode="HTML",
        )
        return

    question_count = EXAM_QUESTION_COUNT[level["key"]]
    required_score = EXAM_PASS_REQUIRED[level["key"]]

    domain_label = (
        EDUCATION_DOMAINS[domain]
        if domain
        else EDUCATION_DOMAINS["general"]
    )

    await message.reply_text(
        "📝 <b>EXAMEN PRÊT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 Diplôme : <b>{level['diploma']}</b>\n"
        f"🎯 Domaine : <b>{domain_label}</b>\n"
        f"❓ Questions : <b>{question_count}</b>\n"
        f"✅ Réussite : <b>{required_score}/{question_count}</b>\n\n"
        "Les questions seront différentes selon le niveau "
        "et sélectionnées dans la banque correspondant au domaine.",
        parse_mode="HTML",
    )


async def domain_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    level = current_level(character)

    if level["key"] == "primary":
        await message.reply_text(
            "📚 Le choix du domaine commence à partir du collège."
        )
        return

    await message.reply_text(
        "🎯 <b>CHOISIS TON DOMAINE</b>\n\n"
        "Ce choix déterminera les questions de tes prochains "
        "examens.\n\n"
        "Tu pourras conserver ton domaine ou en choisir un "
        "autre lorsque tu changeras de niveau.",
        reply_markup=build_domain_keyboard(),
        parse_mode="HTML",
    )


async def domain_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    data = query.data or ""

    if not data.startswith("edu_domain:"):
        return

    domain = data.split(":", 1)[1]

    try:
        domain = normalize_domain(domain)
    except ValueError:
        await query.edit_message_text(
            "❌ Domaine invalide."
        )
        return

    character = await get_actor(update)

    if character is None:
        await query.edit_message_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    level = current_level(character)

    if level["key"] == "primary":
        await query.edit_message_text(
            "📚 Le choix du domaine commence à partir du collège."
        )
        return

    if not await save_education_domain(
        character["id"],
        domain,
    ):
        await query.edit_message_text(
            "❌ Impossible d'enregistrer ton domaine."
        )
        return

    await query.edit_message_text(
        "✅ <b>DOMAINE ENREGISTRÉ</b>\n\n"
        f"🎯 {EDUCATION_DOMAINS[domain]}\n\n"
        "Tes prochains examens utiliseront la banque de "
        "questions de ce domaine.",
        parse_mode="HTML",
    )




# REGISTRATION
# ============================================================

def register_education_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "school",
            school_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "study",
            study_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "domain",
            domain_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            domain_callback,
            pattern=r"^edu_domain:",
        )
    )

    application.add_handler(
        CommandHandler(
            "exam",
            exam_command,
        )
    )
