"""
MANUWORLD - school_profile.py

Profil scolaire et orientation.

Ce module centralise la lecture de l'inscription scolaire active.
Il évite de dépendre d'un champ `domain` qui ne serait pas présent
dans life_characters : le domaine officiel est lu depuis
life_education.

Commandes :
    /schoolprofile
    /orientation

Le module est conçu pour être utilisé par education.py,
school_enrollment.py et domain_exams.py.
"""

from __future__ import annotations

from sqlalchemy import text
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character


DOMAIN_NAMES = {
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
# OUTILS
# ============================================================

async def get_active_education(character_id: int):
    """
    Retourne l'inscription scolaire active la plus récente.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id,
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
                FROM life_education
                WHERE character_id = :character_id
                  AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"character_id": character_id},
        )

        return result.mappings().first()


async def get_active_domain(character_id: int) -> str | None:
    """
    Domaine officiel de l'inscription active.
    """

    education = await get_active_education(character_id)

    if not education:
        return None

    domain = education.get("domain")

    return str(domain).strip().lower() if domain else None


async def get_school_domain_for_character(character) -> str | None:
    """
    Compatibilité avec les autres handlers.

    On préfère toujours life_education.
    Le fallback sur character est uniquement destiné aux anciennes
    données qui n'ont pas encore d'inscription active.
    """

    domain = await get_active_domain(character["id"])

    if domain:
        return domain

    for key in ("domain", "school_domain"):
        value = character.get(key)

        if value:
            value = str(value).strip().lower()

            if value in DOMAIN_NAMES:
                return value

    return None


async def ensure_domain_column() -> None:
    """
    Vérifie que life_education possède le champ domain.

    Cette migration ne supprime aucune donnée.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'life_education'
                  AND column_name = 'domain'
                LIMIT 1
                """
            )
        )

        if result.first() is None:
            await session.execute(
                text(
                    """
                    ALTER TABLE life_education
                    ADD COLUMN domain VARCHAR(80)
                    """
                )
            )

            await session.commit()


# ============================================================
# /SCHOOLPROFILE
# ============================================================

async def school_profile_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None or update.effective_user is None:
        return

    character = await get_life_character(
        update.effective_user.id
    )

    if character is None:
        await message.reply_text(
            "❌ Tu dois d'abord créer ton personnage MANUWORLD."
        )
        return

    await ensure_domain_column()

    education = await get_active_education(
        character["id"]
    )

    if not education:
        await message.reply_text(
            "🎓 **AUCUNE INSCRIPTION ACTIVE**\n\n"
            "À partir du collège, utilise `/schoolenroll` "
            "pour choisir ton orientation et ton établissement.",
            parse_mode="Markdown",
        )
        return

    domain = education.get("domain")
    domain_display = DOMAIN_NAMES.get(
        str(domain).lower(),
        "Non défini",
    ) if domain else "Non défini"

    average = education.get("average")

    if average is None:
        average_display = "0.00/100"
    else:
        average_display = f"{float(average):.2f}/100"

    payer_id = education.get("payer_character_id")

    if payer_id == character["id"]:
        payer_display = "Moi-même"
    elif payer_id:
        payer_display = f"Parent #{payer_id}"
    else:
        payer_display = "Non renseigné"

    fee = int(education.get("tuition_fee") or 0)

    await message.reply_text(
        "🎓 **MON PROFIL SCOLAIRE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏫 École : **{education['school_name']}**\n"
        f"📚 Niveau : **{education['level']}**\n"
        f"📝 Classe : **{education['class_name']}**\n"
        f"📅 Année : **{education['year']}**\n"
        f"🎯 Domaine : **{domain_display}**\n"
        f"📊 Moyenne : **{average_display}**\n\n"
        f"💰 Inscription : **{fee:,} FCFA**\n"
        f"👨‍👩‍👧 Payeur : **{payer_display}**\n\n"
        "✅ Statut : **Inscrit**",
        parse_mode="Markdown",
    )


# ============================================================
# /ORIENTATION
# ============================================================

async def orientation_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None or update.effective_user is None:
        return

    character = await get_life_character(
        update.effective_user.id
    )

    if character is None:
        await message.reply_text(
            "❌ Personnage introuvable."
        )
        return

    domain = await get_school_domain_for_character(
        character
    )

    if domain:
        await message.reply_text(
            "🎯 **MON ORIENTATION**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📚 Domaine actuel : **"
            f"{DOMAIN_NAMES.get(domain, domain)}**\n\n"
            "Tu peux changer d'établissement avec "
            "`/changeschool`.",
            parse_mode="Markdown",
        )
        return

    buttons = []

    for key, name in DOMAIN_NAMES.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    name,
                    callback_data=f"orientation:{key}",
                )
            ]
        )

    await message.reply_text(
        "🎯 **CHOISIS TON ORIENTATION**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "À partir du collège, ton domaine détermine "
        "les questions spécialisées de tes examens.\n\n"
        "👇 Choisis ton domaine :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def orientation_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or update.effective_user is None:
        return

    await query.answer()

    data = query.data or ""

    if ":" not in data:
        return

    domain = data.split(":", 1)[1]

    if domain not in DOMAIN_NAMES:
        await query.answer(
            "Domaine invalide.",
            show_alert=True,
        )
        return

    character = await get_life_character(
        update.effective_user.id
    )

    if character is None:
        await query.edit_message_text(
            "❌ Personnage introuvable."
        )
        return

    await query.edit_message_text(
        "🎯 **ORIENTATION SÉLECTIONNÉE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📚 Domaine : **{DOMAIN_NAMES[domain]}**\n\n"
        "🏫 Tu dois maintenant choisir ton établissement "
        "avec `/schoolenroll`.\n\n"
        "Le domaine sera enregistré avec ton inscription "
        "scolaire et utilisé pour tes futurs examens.",
        parse_mode="Markdown",
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_school_profile_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "schoolprofile",
            school_profile_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "orientation",
            orientation_command,
        )
    )

