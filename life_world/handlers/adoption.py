"""
MANUWORLD - adoption.py

Système d'adoption.

Commandes :
    /adopt @username
    /adopt username
    /adopt                 (en réponse à un message)

    /adoption              (voir les demandes + ses enfants)
    /children              (voir ses enfants)
"""

from __future__ import annotations

from sqlalchemy import text
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

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


def display_name(character) -> str:
    username = character.get("username")

    if username:
        return f"@{username}"

    name = " ".join(
        value
        for value in (
            character.get("first_name"),
            character.get("last_name"),
        )
        if value
    )

    return name or "Joueur"


def get_age(character) -> int:
    try:
        return int(character.get("age") or 0)
    except (TypeError, ValueError):
        return 0


# ============================================================
# DEMANDE D'ADOPTION
# ============================================================

async def adopt_command(
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

    target_result = await resolve_target(
        update,
        allow_self=False,
    )

    if target_result.character is None:
        await message.reply_text(
            target_result.error or "❌ Joueur introuvable."
        )
        return

    target = target_result.character

    parent_id = actor["id"]
    child_id = target["id"]

    if parent_id == child_id:
        await message.reply_text(
            "❌ Tu ne peux pas t'adopter toi-même."
        )
        return

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    if get_age(actor) < 18:
        await message.reply_text(
            "❌ Tu dois avoir au moins 18 ans dans MANUWORLD "
            "pour adopter."
        )
        return

    if get_age(target) >= 18:
        await message.reply_text(
            "❌ L'adoption concerne uniquement un personnage "
            "mineur dans MANUWORLD."
        )
        return

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Demande déjà existante
        # ----------------------------------------------------

        existing = await session.execute(
            text(
                """
                SELECT id
                FROM life_adoption_requests
                WHERE sender_character_id = :parent
                  AND receiver_character_id = :child
                  AND status = 'pending'
                LIMIT 1
                """
            ),
            {
                "parent": parent_id,
                "child": child_id,
            },
        )

        if existing.first():
            await message.reply_text(
                "⏳ Une demande d'adoption est déjà en attente."
            )
            return

        # ----------------------------------------------------
        # Relation déjà existante
        # ----------------------------------------------------

        relation = await session.execute(
            text(
                """
                SELECT id
                FROM life_relationships
                WHERE character_id = :parent
                  AND target_character_id = :child
                  AND relationship_type = 'parent'
                  AND status = 'accepted'
                LIMIT 1
                """
            ),
            {
                "parent": parent_id,
                "child": child_id,
            },
        )

        if relation.first():
            await message.reply_text(
                "👨‍👩‍👧 Cette personne fait déjà partie "
                "de ta famille."
            )
            return

        # ----------------------------------------------------
        # Création
        # ----------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_adoption_requests (
                    sender_character_id,
                    receiver_character_id,
                    status
                )
                VALUES (
                    :parent,
                    :child,
                    'pending'
                )
                """
            ),
            {
                "parent": parent_id,
                "child": child_id,
            },
        )

        await session.commit()

    await message.reply_text(
        f"👶 Demande d'adoption envoyée à {display_name(target)}."
    )


# ============================================================
# ADOPTION + DEMANDES
# ============================================================

async def adoption_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    async with AsyncSessionLocal() as session:

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
                WHERE r.character_id = :parent
                  AND r.relationship_type = 'parent'
                  AND r.status = 'accepted'
                ORDER BY LOWER(
                    COALESCE(c.username, c.first_name)
                )
                """
            ),
            {"parent": actor["id"]},
        )

        children = children_result.mappings().all()

        requests_result = await session.execute(
            text(
                """
                SELECT
                    r.id,
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_adoption_requests r
                JOIN life_characters c
                  ON c.id = r.sender_character_id
                WHERE r.receiver_character_id = :child
                  AND r.status = 'pending'
                ORDER BY r.created_at DESC
                """
            ),
            {"child": actor["id"]},
        )

        requests = requests_result.mappings().all()

    lines = [
        "👨‍👩‍👧 **ADOPTION MANUWORLD**",
        "",
    ]

    if children:
        lines.extend([
            "👶 **MES ENFANTS**",
            "",
        ])

        for index, child in enumerate(children, 1):
            name = (
                f"@{child['username']}"
                if child["username"]
                else " ".join(
                    value
                    for value in (
                        child["first_name"],
                        child["last_name"],
                    )
                    if value
                ) or "Joueur"
            )

            lines.append(
                f"{index}. 👤 {name}"
            )

        lines.append("")

    else:
        lines.extend([
            "👶 Tu n'as encore aucun enfant adopté.",
            "",
        ])

    keyboard = []

    if requests:
        lines.extend([
            "📨 **DEMANDES D'ADOPTION**",
            "",
        ])

        for request in requests:

            name = (
                f"@{request['username']}"
                if request["username"]
                else " ".join(
                    value
                    for value in (
                        request["first_name"],
                        request["last_name"],
                    )
                    if value
                ) or "Joueur"
            )

            lines.append(f"👤 {name}")

            keyboard.append([
                InlineKeyboardButton(
                    f"✅ Accepter • {name}",
                    callback_data=f"adopt_accept:{request['id']}",
                ),
                InlineKeyboardButton(
                    "❌ Refuser",
                    callback_data=f"adopt_reject:{request['id']}",
                ),
            ])

    else:
        lines.append(
            "📭 Aucune demande d'adoption en attente."
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=(
            InlineKeyboardMarkup(keyboard)
            if keyboard
            else None
        ),
    )


# ============================================================
# ENFANTS
# ============================================================

async def children_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:
        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_relationships r
                JOIN life_characters c
                  ON c.id = r.target_character_id
                WHERE r.character_id = :parent
                  AND r.relationship_type = 'parent'
                  AND r.status = 'accepted'
                ORDER BY LOWER(
                    COALESCE(c.username, c.first_name)
                )
                """
            ),
            {"parent": actor["id"]},
        )

        children = result.mappings().all()

    if not children:
        await message.reply_text(
            "👶 Tu n'as encore aucun enfant adopté."
        )
        return

    lines = [
        "👶 **MES ENFANTS**",
        "",
    ]

    for index, child in enumerate(children, 1):

        name = (
            f"@{child['username']}"
            if child["username"]
            else " ".join(
                value
                for value in (
                    child["first_name"],
                    child["last_name"],
                )
                if value
            ) or "Joueur"
        )

        lines.append(
            f"{index}. 👤 {name}"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK ACCEPTATION / REFUS
# ============================================================

async def adoption_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    actor = await get_actor(update)

    if actor is None:
        await query.edit_message_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    try:
        action, request_id_text = query.data.split(":", 1)
        request_id = int(request_id_text)
    except (ValueError, AttributeError):
        await query.edit_message_text(
            "❌ Demande invalide."
        )
        return

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    sender_character_id,
                    receiver_character_id,
                    status
                FROM life_adoption_requests
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": request_id},
        )

        request = result.mappings().first()

        if request is None:
            await query.edit_message_text(
                "❌ Cette demande n'existe plus."
            )
            return

        if request["receiver_character_id"] != actor["id"]:
            await query.edit_message_text(
                "❌ Cette demande ne t'est pas destinée."
            )
            return

        if request["status"] != "pending":
            await query.edit_message_text(
                "ℹ️ Cette demande a déjà été traitée."
            )
            return

        # ----------------------------------------------------
        # ACCEPTATION
        # ----------------------------------------------------

        if action == "adopt_accept":

            child_result = await session.execute(
                text(
                    """
                    SELECT age
                    FROM life_characters
                    WHERE id = :id
                    LIMIT 1
                    """
                ),
                {
                    "id": request["receiver_character_id"],
                },
            )

            child = child_result.mappings().first()

            if child is None:
                await query.edit_message_text(
                    "❌ Le personnage n'existe plus."
                )
                return

            try:
                child_age = int(child["age"] or 0)
            except (TypeError, ValueError):
                child_age = 0

            if child_age >= 18:

                await session.execute(
                    text(
                        """
                        UPDATE life_adoption_requests
                        SET status = 'rejected',
                            responded_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": request_id},
                )

                await session.commit()

                await query.edit_message_text(
                    "❌ L'adoption n'est plus possible : "
                    "le personnage est maintenant majeur."
                )
                return

            # ------------------------------------------------
            # Vérification finale
            # ------------------------------------------------

            relation = await session.execute(
                text(
                    """
                    SELECT id
                    FROM life_relationships
                    WHERE character_id = :parent
                      AND target_character_id = :child
                      AND relationship_type = 'parent'
                      AND status = 'accepted'
                    LIMIT 1
                    """
                ),
                {
                    "parent": request["sender_character_id"],
                    "child": request["receiver_character_id"],
                },
            )

            if relation.first():

                await session.execute(
                    text(
                        """
                        UPDATE life_adoption_requests
                        SET status = 'accepted',
                            responded_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": request_id},
                )

                await session.commit()

                await query.edit_message_text(
                    "👨‍👩‍👧 Cette relation familiale existe déjà."
                )
                return

            # ------------------------------------------------
            # Demande acceptée
            # ------------------------------------------------

            await session.execute(
                text(
                    """
                    UPDATE life_adoption_requests
                    SET status = 'accepted',
                        responded_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": request_id},
            )

            # Parent -> enfant
            await session.execute(
                text(
                    """
                    INSERT INTO life_relationships (
                        character_id,
                        target_character_id,
                        relationship_type,
                        status
                    )
                    VALUES (
                        :parent,
                        :child,
                        'parent',
                        'accepted'
                    )
                    ON CONFLICT (
                        character_id,
                        target_character_id,
                        relationship_type
                    )
                    DO UPDATE SET status = 'accepted'
                    """
                ),
                {
                    "parent": request["sender_character_id"],
                    "child": request["receiver_character_id"],
                },
            )

            # Enfant -> parent
            await session.execute(
                text(
                    """
                    INSERT INTO life_relationships (
                        character_id,
                        target_character_id,
                        relationship_type,
                        status
                    )
                    VALUES (
                        :child,
                        :parent,
                        'child',
                        'accepted'
                    )
                    ON CONFLICT (
                        character_id,
                        target_character_id,
                        relationship_type
                    )
                    DO UPDATE SET status = 'accepted'
                    """
                ),
                {
                    "parent": request["sender_character_id"],
                    "child": request["receiver_character_id"],
                },
            )

            await session.commit()

            await query.edit_message_text(
                "👨‍👩‍👧 **Adoption acceptée !**\n\n"
                "La nouvelle relation familiale est maintenant "
                "enregistrée dans MANUWORLD. ❤️",
                parse_mode="Markdown",
            )
            return

        # ----------------------------------------------------
        # REFUS
        # ----------------------------------------------------

        if action == "adopt_reject":

            await session.execute(
                text(
                    """
                    UPDATE life_adoption_requests
                    SET status = 'rejected',
                        responded_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": request_id},
            )

            await session.commit()

            await query.edit_message_text(
                "❌ Demande d'adoption refusée."
            )
            return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_adoption_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "adopt",
            adopt_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "adoption",
            adoption_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "children",
            children_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            adoption_callback,
            pattern=r"^adopt_(accept|reject):\d+$",
        )
    )