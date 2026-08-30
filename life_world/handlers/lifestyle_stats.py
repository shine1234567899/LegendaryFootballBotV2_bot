"""
MANUWORLD — LIFESTYLE STATS HANDLER

Interface Telegram des statistiques de style de vie.

Commande :
    /lifestyle

Affiche les statistiques calculées par
lifestyle_stats_system.py.

IMPORTANT :
    main.py n'est pas modifié ici.
"""

from __future__ import annotations

from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from life_world.database import get_life_character

from life_world.systems.lifestyle_stats_system import (
    get_stats,
    ensure_player_stats,
)


# ============================================================
# UTILITAIRES
# ============================================================

async def get_actor(
    update: Update,
) -> dict[str, Any] | None:

    user = update.effective_user

    if user is None:
        return None

    character = await get_life_character(
        user.id
    )

    if character is None:
        return None

    return dict(character)


def clamp(
    value: int | float | None,
    minimum: int = 0,
    maximum: int = 100,
) -> int:

    return max(
        minimum,
        min(
            maximum,
            int(value or 0),
        ),
    )


# ============================================================
# BARRE DE PROGRESSION
# ============================================================

def progress_bar(
    value: int | float | None,
    size: int = 10,
) -> str:

    value = clamp(value)

    filled = round(
        value / 100 * size
    )

    filled = max(
        0,
        min(
            size,
            filled,
        ),
    )

    return (
        "🟩" * filled
        + "⬜" * (size - filled)
    )


# ============================================================
# FORMATAGE
# ============================================================

def format_stat_line(
    label: str,
    value: int | float | None,
    icon: str,
) -> str:

    value = clamp(value)

    return (
        f"{icon} **{label}** : {value}/100\n"
        f"   {progress_bar(value)}"
    )


def format_lifestyle_stats(
    stats: dict[str, Any],
) -> str:

    lines = [
        "🌍━━━━━━━━━━━━━━━━━━━━🌍",
        "       𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗤𝗨𝗘𝗦 𝗗𝗘 𝗩𝗜𝗘",
        "🌍━━━━━━━━━━━━━━━━━━━━🌍",
        "",
    ]

    # --------------------------------------------------------
    # Les clés sont volontairement récupérées de manière
    # tolérante afin de fonctionner avec les différentes
    # structures possibles déjà utilisées par le système.
    # --------------------------------------------------------

    health = stats.get(
        "health",
        stats.get(
            "health_score",
            0,
        ),
    )

    happiness = stats.get(
        "happiness",
        stats.get("joy", 0),
    )

    energy = stats.get(
        "energy",
        stats.get("health", 0),
    )

    social = stats.get(
        "social",
        stats.get("reputation", 0),
    )

    finance = stats.get(
        "finance",
        stats.get("wealth", 0),
    )

    education = stats.get(
        "education",
        stats.get("education_score", 0),
    )

    career = stats.get(
        "career",
        stats.get("career_score", 0),
    )

    # Le système de base ne possède pas encore tous les sous-scores.
    # On calcule donc un score global cohérent avec les statistiques
    # réellement disponibles.
    lifestyle = stats.get(
        "lifestyle",
        stats.get("overall", 0),
    )

    if not lifestyle:
        lifestyle = round(
            (
                clamp(stats.get("health"))
                + clamp(stats.get("joy"))
                + clamp(stats.get("reputation"))
                + ((clamp(stats.get("karma"), -100, 100) + 100) / 2)
            ) / 4
        )

    lines.extend(
        [
            format_stat_line(
                "Santé",
                health,
                "❤️",
            ),
            "",
            format_stat_line(
                "Bonheur",
                happiness,
                "😊",
            ),
            "",
            format_stat_line(
                "Énergie",
                energy,
                "⚡",
            ),
            "",
            format_stat_line(
                "Vie sociale",
                social,
                "👥",
            ),
            "",
            format_stat_line(
                "Finance",
                finance,
                "💰",
            ),
            "",
            format_stat_line(
                "Éducation",
                education,
                "🎓",
            ),
            "",
            format_stat_line(
                "Carrière",
                career,
                "💼",
            ),
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            format_stat_line(
                "Score global",
                lifestyle,
                "🌟",
            ),
        ]
    )

    return "\n".join(lines)


# ============================================================
# CLAVIER
# ============================================================

def lifestyle_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="lifestyle:refresh",
                )
            ]
        ]
    )


# ============================================================
# RÉCUPÉRATION DES STATISTIQUES
# ============================================================
async def get_life_character_by_id(
    character_id: int,
) -> dict[str, Any] | None:
    """Récupère le personnage à partir de son identifiant interne."""
    from life_world.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id, telegram_id, username
                FROM life_characters
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": int(character_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None



async def load_stats(
    character_id: int,
) -> dict[str, Any] | None:

    # lifestyle_stats_system.py utilise le username comme clé.
    # Le handler recevait auparavant character_id, ce qui empêchait
    # de retrouver les statistiques du joueur.
    actor = None

    result = await get_life_character_by_id(
        character_id
    )

    if result is None:
        return None

    username = (
        str(result.get("username") or "").strip().lstrip("@").lower()
    )

    if not username:
        username = f"telegram_{result.get('telegram_id', character_id)}"

    stats = ensure_player_stats(username)

    return dict(stats) if stats else None


# ============================================================
# /LIFESTYLE
# ============================================================

async def lifestyle_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:

        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

        return

    stats = await load_stats(
        int(actor["id"])
    )

    if stats is None:

        await message.reply_text(
            "❌ Impossible de récupérer "
            "tes statistiques de vie."
        )

        return

    await message.reply_text(
        format_lifestyle_stats(stats),
        reply_markup=lifestyle_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def lifestyle_callback(
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

    stats = await load_stats(
        int(actor["id"])
    )

    if stats is None:

        await query.edit_message_text(
            "❌ Impossible de récupérer "
            "tes statistiques."
        )

        return

    await query.edit_message_text(
        format_lifestyle_stats(stats),
        reply_markup=lifestyle_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_lifestyle_stats_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "lifestyle",
            lifestyle_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            lifestyle_callback,
            pattern=r"^lifestyle:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "lifestyle_command",
    "lifestyle_callback",
    "register_lifestyle_stats_handlers",
]