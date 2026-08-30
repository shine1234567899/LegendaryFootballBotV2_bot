"""
MANUWORLD - family.py

Arbre généalogique du personnage.

Commande :
    /family
    /family @username
    /family username
    /family          (en réponse au message)

Affiche :
    👴 Parents
    👶 Enfants
    💍 Conjoint(e)

Le système utilise les relations déjà enregistrées dans
life_relationships par les systèmes d'amitié, mariage et adoption.
"""

from __future__ import annotations

from sqlalchemy import text
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character
from life_world.utils.targeting import resolve_target


# ============================================================
# OUTILS
# ============================================================

async def get_actor(update: Update):
    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)


def format_person(row) -> str:
    """Retourne le nom d'un personnage."""
    if row["username"]:
        return f"@{row['username']}"

    name = " ".join(
        value
        for value in (
            row["first_name"],
            row["last_name"],
        )
        if value
    )

    return name or "Joueur"


async def get_family_data(session, character_id: int):
    """Récupère parents, enfants et conjoint."""

    parents_result = await session.execute(
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
            WHERE r.character_id = :character_id
              AND r.relationship_type = 'child'
              AND r.status = 'accepted'
            ORDER BY LOWER(
                COALESCE(c.username, c.first_name)
            )
            """
        ),
        {"character_id": character_id},
    )

    children_result = await session.execute(
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
            WHERE r.character_id = :character_id
              AND r.relationship_type = 'parent'
              AND r.status = 'accepted'
            ORDER BY LOWER(
                COALESCE(c.username, c.first_name)
            )
            """
        ),
        {"character_id": character_id},
    )

    spouse_result = await session.execute(
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
            WHERE r.character_id = :character_id
              AND r.relationship_type = 'spouse'
              AND r.status = 'accepted'
            LIMIT 1
            """
        ),
        {"character_id": character_id},
    )

    return (
        parents_result.mappings().all(),
        children_result.mappings().all(),
        spouse_result.mappings().first(),
    )


# ============================================================
# ARBRE GÉNÉALOGIQUE
# ============================================================

async def family_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:
        await message.reply_text(
            "❌ Tu n'as pas encore créé ton personnage MANUWORLD."
        )
        return

    # --------------------------------------------------------
    # Cible facultative
    # --------------------------------------------------------

    target_username = (
        message.text.split()[1]
        if len(message.text.split()) >= 2
        else None
    )

    if target_username or message.reply_to_message:

        target_result = await resolve_target(
            update,
            allow_self=True,
        )

        if target_result.character is None:
            await message.reply_text(
                target_result.error or "❌ Joueur introuvable."
            )
            return

        target = target_result.character

    else:
        target = actor

    target_id = target["id"]

    async with AsyncSessionLocal() as session:
        parents, children, spouse = await get_family_data(
            session,
            target_id,
        )

    target_name = (
        f"@{target['username']}"
        if target.get("username")
        else " ".join(
            value
            for value in (
                target.get("first_name"),
                target.get("last_name"),
            )
            if value
        ) or "Joueur"
    )

    lines = [
        "🌳 **ARBRE GÉNÉALOGIQUE**",
        "",
        f"👤 **{target_name}**",
        "",
    ]

    # --------------------------------------------------------
    # CONJOINT
    # --------------------------------------------------------

    lines.append("💍 **CONJOINT(E)**")

    if spouse:
        lines.append(
            f"   └─ ❤️ {format_person(spouse)}"
        )
    else:
        lines.append(
            "   └─ Aucun"
        )

    lines.append("")

    # --------------------------------------------------------
    # PARENTS
    # --------------------------------------------------------

    lines.append("👨‍👩‍👧 **PARENTS**")

    if parents:
        for parent in parents:
            lines.append(
                f"   ├─ 👤 {format_person(parent)}"
            )
    else:
        lines.append(
            "   └─ Aucun parent enregistré"
        )

    lines.append("")

    # --------------------------------------------------------
    # ENFANTS
    # --------------------------------------------------------

    lines.append("👶 **ENFANTS**")

    if children:
        for child in children:
            lines.append(
                f"   ├─ 👤 {format_person(child)}"
            )
    else:
        lines.append(
            "   └─ Aucun enfant enregistré"
        )

    lines.append("")
    lines.append(
        "ℹ️ Les relations affichées correspondent aux "
        "relations familiales validées dans MANUWORLD."
    )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_family_handlers(
    application: Application,
) -> None:
    """Enregistre la commande /family."""

    application.add_handler(
        CommandHandler(
            "family",
            family_command,
        )
    )
