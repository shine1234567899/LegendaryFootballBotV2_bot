"""
MANUWORLD - friendship.py

Commandes :
    /addfriend @username
    /addfriend username
    /addfriend      -> en réponse à un message

    /friends
    /friendrequests

Les demandes peuvent être envoyées à plusieurs personnes
indépendamment.
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

from life_world.database import (
    AsyncSessionLocal,
    get_life_character,
)
from life_world.utils.targeting import resolve_target


# ============================================================
# PERSONNAGE ACTUEL
# ============================================================

async def get_actor(update: Update):
    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)


# ============================================================
# ENVOYER UNE DEMANDE
# ============================================================

async def addfriend_command(
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

    sender_id = actor["id"]
    receiver_id = target["id"]

    if sender_id == receiver_id:
        await message.reply_text(
            "❌ Tu ne peux pas t'envoyer une demande d'amitié."
        )
        return

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Déjà amis ?
        # ----------------------------------------------------

        friendship = await session.execute(
            text("""
                SELECT id
                FROM life_relationships
                WHERE (
                    character_id = :sender
                    AND target_character_id = :receiver
                )
                OR (
                    character_id = :receiver
                    AND target_character_id = :sender
                )
                AND relationship_type = 'friend'
                AND status = 'accepted'
                LIMIT 1
            """),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        if friendship.first():
            await message.reply_text(
                "🤝 Vous êtes déjà amis."
            )
            return

        # ----------------------------------------------------
        # Demande déjà envoyée ?
        # ----------------------------------------------------

        existing = await session.execute(
            text("""
                SELECT id
                FROM life_friend_requests
                WHERE sender_character_id = :sender
                  AND receiver_character_id = :receiver
                  AND status = 'pending'
                LIMIT 1
            """),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        if existing.first():
            await message.reply_text(
                "⏳ Une demande d'amitié est déjà en attente."
            )
            return

        # ----------------------------------------------------
        # Demande inverse ?
        # ----------------------------------------------------

        inverse = await session.execute(
            text("""
                SELECT id
                FROM life_friend_requests
                WHERE sender_character_id = :receiver
                  AND receiver_character_id = :sender
                  AND status = 'pending'
                LIMIT 1
            """),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        if inverse.first():
            await message.reply_text(
                "🤝 Cette personne t'a déjà envoyé une demande "
                "d'amitié.\n\n"
                "Utilise /friendrequests pour l'accepter."
            )
            return

        # ----------------------------------------------------
        # Création
        # ----------------------------------------------------

        await session.execute(
            text("""
                INSERT INTO life_friend_requests (
                    sender_character_id,
                    receiver_character_id,
                    status
                )
                VALUES (
                    :sender,
                    :receiver,
                    'pending'
                )
            """),
            {
                "sender": sender_id,
                "receiver": receiver_id,
            },
        )

        await session.commit()

    target_name = (
        f"@{target['username']}"
        if target.get("username")
        else target.get("first_name", "Joueur")
    )

    await message.reply_text(
        f"🤝 Demande d'amitié envoyée à {target_name}."
    )


# ============================================================
# DEMANDES RECUES
# ============================================================

async def friendrequests_command(
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

        result = await session.execute(
            text("""
                SELECT
                    r.id,
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_friend_requests r
                JOIN life_characters c
                    ON c.id = r.sender_character_id
                WHERE r.receiver_character_id = :receiver
                  AND r.status = 'pending'
                ORDER BY r.created_at DESC
            """),
            {
                "receiver": actor["id"],
            },
        )

        requests = result.mappings().all()

    if not requests:
        await message.reply_text(
            "🤝 Tu n'as aucune demande d'amitié en attente."
        )
        return

    lines = [
        "🤝 **DEMANDES D'AMITIÉ**",
        "",
    ]

    keyboard = []

    for request in requests:

        if request["username"]:
            name = f"@{request['username']}"
        else:
            name = " ".join(
                x
                for x in [
                    request["first_name"],
                    request["last_name"],
                ]
                if x
            )

        lines.append(f"👤 {name}")

        keyboard.append([
            InlineKeyboardButton(
                f"✅ {name}",
                callback_data=f"friend_accept:{request['id']}",
            ),
            InlineKeyboardButton(
                "❌ Refuser",
                callback_data=f"friend_reject:{request['id']}",
            ),
        ])

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ============================================================
# ACCEPTATION / REFUS
# ============================================================

async def friend_request_callback(
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
            text("""
                SELECT
                    id,
                    sender_character_id,
                    receiver_character_id,
                    status
                FROM life_friend_requests
                WHERE id = :id
                LIMIT 1
            """),
            {
                "id": request_id,
            },
        )

        request = result.mappings().first()

        if request is None:
            await query.edit_message_text(
                "❌ Cette demande n'existe plus."
            )
            return

        # ----------------------------------------------------
        # Seul le destinataire peut répondre
        # ----------------------------------------------------

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

        if action == "friend_accept":

            await session.execute(
                text("""
                    UPDATE life_friend_requests
                    SET status = 'accepted',
                        responded_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": request_id,
                },
            )

            # Une amitié est bidirectionnelle.
            await session.execute(
                text("""
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
                            'friend',
                            'accepted'
                        ),
                        (
                            :receiver,
                            :sender,
                            'friend',
                            'accepted'
                        )
                    ON CONFLICT (
                        character_id,
                        target_character_id,
                        relationship_type
                    )
                    DO UPDATE SET status = 'accepted'
                """),
                {
                    "sender": request["sender_character_id"],
                    "receiver": request["receiver_character_id"],
                },
            )

            await session.commit()

            await query.edit_message_text(
                "🤝 **Demande acceptée !**\n\n"
                "Vous êtes maintenant amis sur MANUWORLD.",
                parse_mode="Markdown",
            )
            return

        # ----------------------------------------------------
        # REFUS
        # ----------------------------------------------------

        if action == "friend_reject":

            await session.execute(
                text("""
                    UPDATE life_friend_requests
                    SET status = 'rejected',
                        responded_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": request_id,
                },
            )

            await session.commit()

            await query.edit_message_text(
                "❌ Demande d'amitié refusée."
            )
            return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# LISTE DES AMIS
# ============================================================

async def friends_command(
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

        result = await session.execute(
            text("""
                SELECT
                    c.first_name,
                    c.last_name,
                    c.username
                FROM life_relationships r
                JOIN life_characters c
                    ON c.id = r.target_character_id
                WHERE r.character_id = :character_id
                  AND r.relationship_type = 'friend'
                  AND r.status = 'accepted'
                ORDER BY LOWER(
                    COALESCE(c.username, c.first_name)
                )
            """),
            {
                "character_id": actor["id"],
            },
        )

        friends = result.mappings().all()

    if not friends:
        await message.reply_text(
            "🤝 Tu n'as encore aucun ami."
        )
        return

    lines = [
        "🤝 **MES AMIS**",
        "",
    ]

    for index, friend in enumerate(friends, 1):

        if friend["username"]:
            name = f"@{friend['username']}"
        else:
            name = " ".join(
                x
                for x in [
                    friend["first_name"],
                    friend["last_name"],
                ]
                if x
            )

        lines.append(
            f"{index}. 👤 {name}"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_friendship_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "addfriend",
            addfriend_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "friendrequests",
            friendrequests_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "friends",
            friends_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            friend_request_callback,
            pattern=r"^friend_(accept|reject):\d+$",
        )
    )