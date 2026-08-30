"""
MANUWORLD - school_enrollment.py

Inscription scolaire dynamique.

À partir du collège, le joueur choisit :
    1. son domaine d'évolution
    2. son école
    3. qui paie l'inscription :
       - lui-même
       - un parent disponible dans sa famille

Le joueur peut ensuite changer d'école avec /changeschool.

Les écoles et prix sont des données de jeu faciles à modifier.

Ce module utilise la table existante life_education et ajoute
uniquement les colonnes nécessaires si elles n'existent pas.
"""

from __future__ import annotations

from sqlalchemy import text
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character


# ============================================================
# DOMAINES
# ============================================================

DOMAINS = {
    "science": "🔬 Sciences",
    "technology": "💻 Technologie & Informatique",
    "economics": "💰 Économie & Gestion",
    "law": "⚖️ Droit",
    "medicine": "🩺 Santé & Médecine",
    "arts": "🎨 Arts & Création",
    "communication": "🎙️ Communication & Médias",
    "engineering": "⚙️ Ingénierie",
}


# ============================================================
# ÉCOLES
# ============================================================

SCHOOLS = [
    {
        "id": "public",
        "name": "🏫 Établissement Public",
        "price": 25000,
        "description": "Formation publique accessible.",
    },
    {
        "id": "municipal",
        "name": "🏛️ Institut Municipal",
        "price": 45000,
        "description": "Formation générale avec accompagnement.",
    },
    {
        "id": "private",
        "name": "🏢 Collège/Lycée Privé",
        "price": 90000,
        "description": "Formation privée standard.",
    },
    {
        "id": "elite",
        "name": "👑 Académie Privée Elite",
        "price": 180000,
        "description": "Établissement haut de gamme.",
    },
    {
        "id": "international",
        "name": "🌍 Institut International",
        "price": 350000,
        "description": "Formation internationale premium.",
    },
]


# ============================================================
# OUTILS
# ============================================================

async def get_actor(update: Update):
    user = update.effective_user
    if user is None:
        return None
    return await get_life_character(user.id)


def domain_name(key: str) -> str:
    return DOMAINS.get(key, key)


def school_by_id(school_id: str) -> dict | None:
    return next(
        (school for school in SCHOOLS if school["id"] == school_id),
        None,
    )


def school_level(character) -> str:
    education = str(character.get("education_level") or "").lower()

    if "univers" in education or "supérieur" in education:
        return "university"
    if "terminal" in education:
        return "terminal"
    if "lycée" in education or "lycee" in education:
        return "high_school"
    if "collège" in education or "college" in education:
        return "college"
    return "primary"


def requires_domain(character) -> bool:
    return school_level(character) in {
        "college",
        "high_school",
        "terminal",
        "university",
    }


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " FCFA"


# ============================================================
# MIGRATION LOCALE
# ============================================================

async def ensure_enrollment_columns() -> None:
    """
    Ajoute les champs d'inscription à life_education sans supprimer
    les données existantes.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'life_education'
                """
            )
        )

        existing = {row[0] for row in result.fetchall()}

        additions = {
            "domain": (
                "ALTER TABLE life_education "
                "ADD COLUMN domain VARCHAR(80)"
            ),
            "tuition_fee": (
                "ALTER TABLE life_education "
                "ADD COLUMN tuition_fee BIGINT NOT NULL DEFAULT 0"
            ),
            "payer_character_id": (
                "ALTER TABLE life_education "
                "ADD COLUMN payer_character_id BIGINT "
                "REFERENCES life_characters(id) ON DELETE SET NULL"
            ),
            "school_id": (
                "ALTER TABLE life_education "
                "ADD COLUMN school_id VARCHAR(80)"
            ),
        }

        for column, statement in additions.items():
            if column not in existing:
                await session.execute(text(statement))

        await session.commit()


# ============================================================
# /SCHOOLENROLL
# ============================================================

async def enroll_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Crée d'abord ton personnage MANUWORLD."
        )
        return

    await ensure_enrollment_columns()

    if not requires_domain(character):
        await message.reply_text(
            "🏫 À ce niveau, ton parcours général est encore "
            "en cours.\n\n"
            "Le choix du domaine commencera à partir du collège."
        )
        return

    # Session d'inscription stockée uniquement pour ce joueur.
    context.user_data["school_enrollment"] = {
        "step": "domain",
        "character_id": character["id"],
        "domain": None,
        "school_id": None,
        "payer_id": None,
        "changing_school": False,
    }

    await send_domain_menu(message)


async def send_domain_menu(message):
    buttons = []

    for key, name in DOMAINS.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    name,
                    callback_data=f"school_domain:{key}",
                )
            ]
        )

    await message.reply_text(
        "🎓 **CHOISIS TON DOMAINE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "À partir du collège, ton domaine influence "
        "ton orientation future.\n\n"
        "👇 Choisis le domaine dans lequel tu souhaites évoluer :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ============================================================
# CALLBACK DOMAINE
# ============================================================

async def domain_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    data = query.data or ""
    domain = data.split(":", 1)[1] if ":" in data else None

    if domain not in DOMAINS:
        await query.answer("Domaine invalide.", show_alert=True)
        return

    session = context.user_data.get("school_enrollment")

    if not session:
        await query.edit_message_text(
            "❌ Cette inscription a expiré. Utilise /schoolenroll."
        )
        return

    session["domain"] = domain
    session["step"] = "school"

    buttons = []

    for school in SCHOOLS:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{school['name']} — {money(school['price'])}",
                    callback_data=f"school_select:{school['id']}",
                )
            ]
        )

    await query.edit_message_text(
        f"🎓 **DOMAINE CHOISI**\n\n"
        f"{domain_name(domain)}\n\n"
        "🏫 **CHOISIS MAINTENANT TON ÉCOLE**\n\n"
        "Le prix d'inscription dépend de l'établissement.\n"
        "Tu pourras changer d'école plus tard.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ============================================================
# CALLBACK ÉCOLE
# ============================================================

async def school_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    school_id = (
        query.data.split(":", 1)[1]
        if ":" in query.data
        else ""
    )

    school = school_by_id(school_id)

    if school is None:
        await query.answer("École invalide.", show_alert=True)
        return

    session = context.user_data.get("school_enrollment")

    if not session or not session.get("domain"):
        await query.edit_message_text(
            "❌ Session expirée. Utilise /schoolenroll."
        )
        return

    session["school_id"] = school_id
    session["step"] = "payer"

    # Vérifier s'il existe au moins un parent.
    character = await get_actor(update)

    if character is None:
        await query.edit_message_text(
            "❌ Personnage introuvable."
        )
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT
                    c.id,
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_relationships r
                JOIN life_characters c
                  ON c.id = r.target_character_id
                WHERE r.character_id = :child_id
                  AND r.relationship_type = 'child'
                  AND r.status = 'accepted'
                ORDER BY c.id
                """
            ),
            {"child_id": character["id"]},
        )

        parents = result.mappings().all()

    buttons = [
        [
            InlineKeyboardButton(
                "💰 Je paie moi-même",
                callback_data="school_payer:self",
            )
        ]
    ]

    for parent in parents:
        name = (
            f"@{parent['username']}"
            if parent["username"]
            else (
                " ".join(
                    x for x in (
                        parent["first_name"],
                        parent["last_name"],
                    )
                    if x
                ) or "Parent"
            )
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"👨‍👩‍👧 {name} paie",
                    callback_data=f"school_payer:{parent['id']}",
                )
            ]
        )

    await query.edit_message_text(
        f"🏫 **ÉCOLE CHOISIE**\n\n"
        f"{school['name']}\n"
        f"💰 Inscription : **{money(school['price'])}**\n\n"
        "👨‍👩‍👧 **QUI PAIE L'INSCRIPTION ?**\n\n"
        "Si tu fais partie d'une famille avec un parent "
        "enregistré, celui-ci peut prendre l'inscription à sa charge.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ============================================================
# PAIEMENT / VALIDATION
# ============================================================

async def payer_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    payer_value = (
        query.data.split(":", 1)[1]
        if ":" in query.data
        else ""
    )

    session = context.user_data.get("school_enrollment")

    if not session:
        await query.edit_message_text(
            "❌ Session expirée. Utilise /schoolenroll."
        )
        return

    character = await get_actor(update)

    if character is None:
        await query.edit_message_text(
            "❌ Personnage introuvable."
        )
        return

    school = school_by_id(session["school_id"])

    if school is None:
        await query.edit_message_text(
            "❌ École introuvable."
        )
        return

    if payer_value == "self":
        payer_id = character["id"]
    else:
        try:
            payer_id = int(payer_value)
        except ValueError:
            await query.edit_message_text(
                "❌ Parent invalide."
            )
            return

        # Le payeur doit réellement être le parent du joueur.
        async with AsyncSessionLocal() as db:
            parent_check = await db.execute(
                text(
                    """
                    SELECT id
                    FROM life_relationships
                    WHERE character_id = :child_id
                      AND target_character_id = :parent_id
                      AND relationship_type = 'child'
                      AND status = 'accepted'
                    LIMIT 1
                    """
                ),
                {
                    "child_id": character["id"],
                    "parent_id": payer_id,
                },
            )

            if not parent_check.first():
                await query.edit_message_text(
                    "❌ Cette personne n'est pas un parent enregistré."
                )
                return

    # --------------------------------------------------------
    # Transaction atomique : vérifier le solde puis débiter.
    # --------------------------------------------------------

    async with AsyncSessionLocal() as db:

        payer = await db.execute(
            text(
                """
                SELECT id, coins
                FROM life_characters
                WHERE id = :payer_id
                FOR UPDATE
                """
            ),
            {"payer_id": payer_id},
        )

        payer_row = payer.mappings().first()

        if payer_row is None:
            await query.edit_message_text(
                "❌ Payeur introuvable."
            )
            return

        balance = int(payer_row["coins"] or 0)
        price = int(school["price"])

        if balance < price:
            await query.edit_message_text(
                "❌ **INSCRIPTION IMPOSSIBLE**\n\n"
                f"💰 Prix : **{money(price)}**\n"
                f"💳 Solde disponible : **{money(balance)}**\n\n"
                "Le payeur ne possède pas assez d'argent.",
                parse_mode="Markdown",
            )
            return

        # Débit.
        await db.execute(
            text(
                """
                UPDATE life_characters
                SET coins = coins - :price,
                    updated_at = NOW()
                WHERE id = :payer_id
                """
            ),
            {
                "price": price,
                "payer_id": payer_id,
            },
        )

        # Fermer l'ancienne inscription active si changement d'école.
        await db.execute(
            text(
                """
                UPDATE life_education
                SET status = 'completed',
                    ended_at = NOW()
                WHERE character_id = :character_id
                  AND status = 'active'
                """
            ),
            {"character_id": character["id"]},
        )

        # Nouvelle inscription.
        await db.execute(
            text(
                """
                INSERT INTO life_education (
                    character_id,
                    school_name,
                    level,
                    class_name,
                    year,
                    average,
                    status,
                    domain,
                    tuition_fee,
                    payer_character_id,
                    school_id
                )
                VALUES (
                    :character_id,
                    :school_name,
                    :level,
                    :class_name,
                    EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
                    0,
                    'active',
                    :domain,
                    :tuition_fee,
                    :payer_character_id,
                    :school_id
                )
                """
            ),
            {
                "character_id": character["id"],
                "school_name": school["name"],
                "level": character.get("education_level")
                or "Collège",
                "class_name": "Orientation",
                "domain": session["domain"],
                "tuition_fee": price,
                "payer_character_id": payer_id,
                "school_id": school["id"],
            },
        )

        await db.execute(
            text(
                """
                INSERT INTO life_transactions (
                    character_id,
                    type,
                    amount,
                    currency,
                    description
                )
                VALUES (
                    :character_id,
                    'school_fee',
                    :amount,
                    'coins',
                    :description
                )
                """
            ),
            {
                "character_id": payer_id,
                "amount": -price,
                "description": (
                    f"Inscription scolaire de "
                    f"{character.get('username') or character.get('first_name')}"
                ),
            },
        )

        await db.commit()

    context.user_data.pop("school_enrollment", None)

    await query.edit_message_text(
        "🎓 **INSCRIPTION CONFIRMÉE !**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📚 Domaine : **{domain_name(session['domain'])}**\n"
        f"🏫 École : **{school['name']}**\n"
        f"💰 Inscription : **{money(school['price'])}**\n\n"
        "✅ Ton inscription est maintenant active.",
        parse_mode="Markdown",
    )


# ============================================================
# /CHANGESCHOOL
# ============================================================

async def change_school_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    if message is None:
        return

    character = await get_actor(update)

    if character is None:
        await message.reply_text(
            "❌ Personnage introuvable."
        )
        return

    await ensure_enrollment_columns()

    if not requires_domain(character):
        await message.reply_text(
            "❌ Le changement d'école n'est disponible "
            "qu'à partir du collège."
        )
        return

    context.user_data["school_enrollment"] = {
        "step": "domain",
        "character_id": character["id"],
        "domain": None,
        "school_id": None,
        "payer_id": None,
        "changing_school": True,
    }

    await message.reply_text(
        "🏫 **CHANGEMENT D'ÉCOLE**\n\n"
        "Tu vas pouvoir choisir une nouvelle école.\n"
        "⚠️ L'inscription de la nouvelle école devra être payée.",
        parse_mode="Markdown",
    )

    await send_domain_menu(message)


# ============================================================
# REGISTRATION
# ============================================================

def register_school_enrollment_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "schoolenroll",
            enroll_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "changeschool",
            change_school_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            domain_callback,
            pattern=r"^school_domain:[A-Za-z0-9_]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            school_callback,
            pattern=r"^school_select:[A-Za-z0-9_]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            payer_callback,
            pattern=r"^school_payer:(self|\d+)$",
        )
    )
