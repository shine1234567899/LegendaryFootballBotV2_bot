"""
MANUWORLD - targeting.py

Système central de ciblage d'un joueur.

Une commande peut cibler :
    /commande @username
    /commande username

ou être utilisée en réponse au message du joueur :
    /commande

Ce fichier permet aux autres handlers de ne pas
réécrire cette logique à chaque fois.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from life_world.database import (
    get_life_character,
    get_life_character_by_username,
)


# ============================================================
# RESULTAT DU CIBLAGE
# ============================================================

@dataclass
class TargetResult:
    character: Optional[object] = None
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    error: Optional[str] = None

    @property
    def found(self) -> bool:
        return self.character is not None


# ============================================================
# UTILITAIRES
# ============================================================

def normalize_username(username: str | None) -> str:
    """
    Transforme :

        @Shine
        Shine
        @shine

    en :

        shine
    """
    return (username or "").strip().lstrip("@").strip()


# ============================================================
# RECUPERER LA CIBLE
# ============================================================

def get_target_username(update: Update) -> str:
    """
    Cherche la cible dans cet ordre :

    1. /commande @username
    2. /commande username
    3. réponse au message d'un joueur
    """

    message = update.effective_message

    if message is None:
        return ""

    text = message.text or message.caption or ""
    parts = text.split()

    # --------------------------------------------------------
    # /commande @username
    # --------------------------------------------------------

    if len(parts) >= 2:
        candidate = normalize_username(parts[1])

        if candidate:
            return candidate

    # --------------------------------------------------------
    # /commande en réponse à un message
    # --------------------------------------------------------

    reply = message.reply_to_message

    if reply and reply.from_user:

        username = reply.from_user.username

        if username:
            return normalize_username(username)

    return ""


# ============================================================
# RESOLUTION DE LA CIBLE
# ============================================================

async def resolve_target(
    update: Update,
    *,
    allow_self: bool = False,
) -> TargetResult:
    """
    Recherche le personnage MANUWORLD correspondant
    au joueur ciblé.
    """

    actor = update.effective_user

    if actor is None:
        return TargetResult(
            error="❌ Impossible de déterminer l'utilisateur."
        )

    username = get_target_username(update)

    # --------------------------------------------------------
    # AUCUNE CIBLE
    # --------------------------------------------------------

    if not username:

        if allow_self:

            character = await get_life_character(actor.id)

            if character:

                return TargetResult(
                    character=character,
                    telegram_id=actor.id,
                    username=normalize_username(actor.username),
                )

        return TargetResult(
            error=(
                "❌ Aucun joueur ciblé.\n\n"
                "Utilise `@username` ou réponds "
                "au message du joueur."
            )
        )

    # --------------------------------------------------------
    # RECHERCHE DANS MANUWORLD
    # --------------------------------------------------------

    character = await get_life_character_by_username(username)

    if character is None:

        return TargetResult(
            username=username,
            error=(
                f"❌ Aucun personnage MANUWORLD trouvé "
                f"pour @{username}."
            ),
        )

    # --------------------------------------------------------
    # TELEGRAM ID
    # --------------------------------------------------------

    target_id = character.get("telegram_id")

    # --------------------------------------------------------
    # EMPECHE L'AUTO-CIBLAGE
    # --------------------------------------------------------

    if not allow_self and target_id == actor.id:

        return TargetResult(
            character=character,
            telegram_id=target_id,
            username=username,
            error=(
                "❌ Tu ne peux pas utiliser "
                "cette action sur toi-même."
            ),
        )

    return TargetResult(
        character=character,
        telegram_id=target_id,
        username=username,
    )


# ============================================================
# HELPER POUR LES HANDLERS
# ============================================================

async def require_target(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_self: bool = False,
):
    """
    Fonction pratique pour les handlers.

    Exemple :

        target = await require_target(
            update,
            context
        )

        if target is None:
            return

        target_id = target["telegram_id"]
    """

    result = await resolve_target(
        update,
        allow_self=allow_self,
    )

    # --------------------------------------------------------
    # ERREUR
    # --------------------------------------------------------

    if not result.found or result.error:

        if update.effective_message and result.error:

            await update.effective_message.reply_text(
                result.error
            )

        return None

    # --------------------------------------------------------
    # SAUVEGARDE TEMPORAIRE
    # --------------------------------------------------------

    context.user_data["life_target_id"] = result.telegram_id

    context.user_data["life_target_username"] = (
        result.username
    )

    return result.character


# ============================================================
# PERSONNAGE DU JOUEUR ACTUEL
# ============================================================

async def get_actor_character(update: Update):
    """
    Récupère le personnage MANUWORLD
    de l'utilisateur qui exécute la commande.
    """

    user = update.effective_user

    if user is None:
        return None

    return await get_life_character(user.id)