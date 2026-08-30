"""
MANUWORLD - marriage.py

Commandes :
    /marry @username
    /marry username
    /marry              (en réponse à un message)

    /marriage           (voir son mariage + demandes reçues)
    /divorce             (mettre fin au mariage)

La cible peut être fournie avec @username ou par réponse
au message du joueur.
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
    """Retourne le personnage MANUWORLD de l'utilisateur courant."""
    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)


async def get_marriage(session, character_id: int):
    """Retourne le mariage actif du personnage, s'il existe."""
    result = await session.execute(
        text(
            """
            SELECT
                r.id,
                r.character_id,
                r.target_character_id
            FROM life_relationships r
            WHERE r.character_id = :character_id
              AND r.relationship_type = 'spouse'
              AND r.status = 'accepted'
            LIMIT 1
            """
        ),
        {"character_id": character_id},
    )

    return result.mappings().first()


def get_age(character) -> int:
    """Récupère l'âge du personnage sans provoquer d'erreur."""
    try:
        return int(character.get("age") or 0)
    except (TypeError, ValueError):
        return 0


def display_name(character) -> str:
    """Nom d'affichage avec priorité au username."""
    if character.get("username"):
        return f"@{character['username']}"

    name = " ".join(
        value
        for value in (
            character.get("first_name"),
            character.get("last_name"),
        )
        if value
    )

    return name or "Joueur"


# ============================================================
# DEMANDE DE MARIAGE
# ============================================================

async def marry_command(
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
    # CIBLE : @username / username / réponse
    # --------------------------------------------------------

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

    sender_id = actor["id"]
    receiver_id = target["id"]

    if sender_id == receiver_id:
        await message.reply_text(
            "❌ Tu ne peux pas te demander en mariage."
        )
        return

    # --------------------------------------------------------
    # AGE MINIMUM
    # --------------------------------------------------------

    if get_age(actor) < 18:
        await message.reply_text(
            "❌ Tu dois avoir au moins 18 ans dans MANUWORLD."
        )
        return

    if get_age(target) < 18:
        await message.reply_text(
            "❌ Cette personne doit avoir au moins 18 ans "
            "dans MANUWORLD."
        )
        return

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Vérification des mariages actuels
        # ----------------------------------------------------

        actor_marriage = await get_marriage(
            session,
            sender_id,
        )

        if actor_marriage:
            await message.reply_text(
                "💍 Tu es déjà marié(e)."
            )
            return

        target_marriage = await get_marriage(
            session,
            receiver_id,
        )

        if target_marriage:
            await message.reply_text(
                "💍 Cette personne est déjà mariée."
            )
            return

        # ----------------------------------------------------
        # Demande déjà envoyée
        # ----------------------------------------------------

        existing = await session.execute(
            text(
                """
                SELECT id
                FROM life_marriage_requests
                WHERE sender_character_id = :sender
                  AND receiver_character_id = :receiver
                  AND status = 'pending'
                LIMIT 1
                """
            ),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        if existing.first():
            await message.reply_text(
                "⏳ Une demande en mariage est déjà en attente."
            )
            return

        # ----------------------------------------------------
        # Demande inverse
        # ----------------------------------------------------

        inverse = await session.execute(
            text(
                """
                SELECT id
                FROM life_marriage_requests
                WHERE sender_character_id = :receiver
                  AND receiver_character_id = :sender
                  AND status = 'pending'
                LIMIT 1
                """
            ),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        if inverse.first():
            await message.reply_text(
                "💍 Cette personne t'a déjà envoyé une demande "
                "en mariage.\n\n"
                "Utilise /marriage pour la traiter."
            )
            return

        # ----------------------------------------------------
        # Création de la demande
        # ----------------------------------------------------

        await session.execute(
            text(
                """
                INSERT INTO life_marriage_requests (
                    sender_character_id,
                    receiver_character_id,
                    status
                )
                VALUES (
                    :sender,
                    :receiver,
                    'pending'
                )
                """
            ),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        await session.commit()

    await message.reply_text(
        f"💍 Demande en mariage envoyée à {display_name(target)}."
    )


# ============================================================
# VOIR SON MARIAGE + DEMANDES
# ============================================================

async def marriage_command(
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

    async with AsyncSessionLocal() as session:

        marriage = await get_marriage(
            session,
            actor["id"],
        )

        requests_result = await session.execute(
            text(
                """
                SELECT
                    r.id,
                    r.sender_character_id,
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_marriage_requests r
                JOIN life_characters c
                  ON c.id = r.sender_character_id
                WHERE r.receiver_character_id = :receiver
                  AND r.status = 'pending'
                ORDER BY r.created_at DESC
                """
            ),
            {"receiver": actor["id"]},
        )

        requests = requests_result.mappings().all()

        spouse = None

        if marriage:
            spouse_id = marriage["target_character_id"]

            spouse_result = await session.execute(
                text(
                    """
                    SELECT
                        first_name,
                        last_name,
                        username
                    FROM life_characters
                    WHERE id = :id
                    LIMIT 1
                    """
                ),
                {"id": spouse_id},
            )

            spouse = spouse_result.mappings().first()

    lines = [
        "💍 **MARIAGE MANUWORLD**",
        "",
    ]

    if spouse:
        spouse_name = display_name(spouse)

        lines.extend(
            [
                f"❤️ Conjoint(e) : **{spouse_name}**",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "💔 Statut : Célibataire",
                "",
            ]
        )

    keyboard = []

    if requests:
        lines.append("📨 **Demandes reçues**")
        lines.append("")

        for request in requests:

            if request["username"]:
                name = f"@{request['username']}"
            else:
                name = " ".join(
                    value
                    for value in (
                        request["first_name"],
                        request["last_name"],
                    )
                    if value
                ) or "Joueur"

            lines.append(f"👤 {name}")

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"💍 Accepter • {name}",
                        callback_data=(
                            f"marry_accept:{request['id']}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ Refuser",
                        callback_data=(
                            f"marry_reject:{request['id']}"
                        ),
                    ),
                ]
            )
    else:
        lines.append("📭 Aucune demande en attente.")

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
# ACCEPTATION / REFUS
# ============================================================

async def marriage_callback(
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
                FROM life_marriage_requests
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

        # Seul le destinataire peut répondre.
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

        if action == "marry_accept":

            sender_marriage = await get_marriage(
                session,
                request["sender_character_id"],
            )

            receiver_marriage = await get_marriage(
                session,
                request["receiver_character_id"],
            )

            if sender_marriage or receiver_marriage:

                await session.execute(
                    text(
                        """
                        UPDATE life_marriage_requests
                        SET status = 'rejected',
                            responded_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": request_id},
                )

                await session.commit()

                await query.edit_message_text(
                    "❌ Le mariage n'est plus possible : "
                    "l'un des deux joueurs est déjà marié."
                )
                return

            # Accepter la demande.
            await session.execute(
                text(
                    """
                    UPDATE life_marriage_requests
                    SET status = 'accepted',
                        responded_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": request_id},
            )

            # Relation dans les deux sens.
            await session.execute(
                text(
                    """
                    INSERT INTO life_relationships (
                        character_id,
                        target_character_id,
                        relationship_type,
                        status
                    )
                    VALUES
                        (
                            :sender,
                            :receiver,
                            'spouse',
                            'accepted'
                        ),
                        (
                            :receiver,
                            :sender,
                            'spouse',
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
                    "sender": request["sender_character_id"],
                    "receiver": request["receiver_character_id"],
                },
            )

            # Synchroniser le statut du personnage.
            await session.execute(
                text(
                    """
                    UPDATE life_characters
                    SET relationship_status = 'married',
                        updated_at = NOW()
                    WHERE id IN (:sender, :receiver)
                    """
                ),
                {
                    "sender": request["sender_character_id"],
                    "receiver": request["receiver_character_id"],
                },
            )

            await session.commit()

            await query.edit_message_text(
                "💍 **Mariage accepté !**\n\n"
                "Félicitations ! Vous êtes maintenant mariés "
                "dans MANUWORLD. ❤️",
                parse_mode="Markdown",
            )
            return

        # ----------------------------------------------------
        # REFUS
        # ----------------------------------------------------

        if action == "marry_reject":

            await session.execute(
                text(
                    """
                    UPDATE life_marriage_requests
                    SET status = 'rejected',
                        responded_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": request_id},
            )

            await session.commit()

            await query.edit_message_text(
                "❌ Demande en mariage refusée."
            )
            return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# DIVORCE
# ============================================================

async def divorce_command(
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

        marriage = await get_marriage(
            session,
            actor["id"],
        )

        if not marriage:
            await message.reply_text(
                "❌ Tu n'es pas marié(e)."
            )
            return

        spouse_id = marriage["target_character_id"]

        await session.execute(
            text(
                """
                UPDATE life_relationships
                SET status = 'ended'
                WHERE relationship_type = 'spouse'
                  AND status = 'accepted'
                  AND (
                        (
                            character_id = :actor
                            AND target_character_id = :spouse
                        )
                        OR
                        (
                            character_id = :spouse
                            AND target_character_id = :actor
                        )
                  )
                """
            ),
            {
                "actor": actor["id"],
                "spouse": spouse_id,
            },
        )

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET relationship_status = 'single',
                    updated_at = NOW()
                WHERE id IN (:actor, :spouse)
                """
            ),
            {
                "actor": actor["id"],
                "spouse": spouse_id,
            },
        )

        await session.commit()

    await message.reply_text(
        "💔 Le mariage a été terminé.\n\n"
        "Vous êtes maintenant célibataires dans MANUWORLD."
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_marriage_handlers(
    application: Application,
) -> None:
    """Enregistre tous les handlers du système de mariage."""

    application.add_handler(
        CommandHandler(
            "marry",
            marry_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "marriage",
            marriage_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "divorce",
            divorce_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            marriage_callback,
            pattern=r"^marry_(accept|reject):\d+$",
        )
    )
