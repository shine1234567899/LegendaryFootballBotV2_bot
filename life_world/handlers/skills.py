"""
MANUWORLD — SKILLS HANDLER

Interface Telegram du système de compétences.

Commande :
    /skills
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

from life_world.systems.skills_system import (
    get_character_skills,
    get_skill,
    format_skill,
    format_skills,
    get_skill_leaderboard,
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


# ============================================================
# MENU
# ============================================================

def skills_menu() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎯 Mes compétences",
                    callback_data="skills:list",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏆 Classement",
                    callback_data="skills:leaderboard",
                )
            ],
        ]
    )


# ============================================================
# /SKILLS
# ============================================================

async def skills_command(
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

    skills = await get_character_skills(
        int(actor["id"])
    )

    await message.reply_text(
        format_skills(skills),
        reply_markup=skills_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# LISTE
# ============================================================

async def show_skills(
    query,
    character_id: int,
):

    skills = await get_character_skills(
        character_id
    )

    if not skills:

        await query.edit_message_text(
            (
                "🎯 **COMPÉTENCES**\n\n"
                "Aucune compétence enregistrée."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Retour",
                            callback_data="skills:home",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return

    buttons = []

    for skill in skills:

        skill_name = str(
            skill["skill_name"]
        )

        level = int(
            skill.get("level") or 1
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    (
                        f"🎯 {skill_name[:22]} "
                        f"— Niv. {level}"
                    ),
                    callback_data=(
                        "skills:view:"
                        f"{skill_name}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data="skills:home",
            )
        ]
    )

    await query.edit_message_text(
        format_skills(skills),
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown",
    )


# ============================================================
# DÉTAIL
# ============================================================

async def show_skill(
    query,
    character_id: int,
    skill_name: str,
):

    skill = await get_skill(
        character_id,
        skill_name,
    )

    if skill is None:

        await query.edit_message_text(
            "❌ Compétence introuvable.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Compétences",
                            callback_data="skills:list",
                        )
                    ]
                ]
            ),
        )

        return

    leaderboard = await get_skill_leaderboard(
        skill_name,
        limit=5,
    )

    text = format_skill(
        skill
    )

    if leaderboard:

        text += (
            "\n\n"
            "🏆 **TOP 5**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )

        for index, player in enumerate(
            leaderboard,
            start=1,
        ):

            username = (
                player.get("username")
                or player.get("first_name")
                or "Joueur"
            )

            level = int(
                player.get("level") or 1
            )

            text += (
                f"{index}. {username} "
                f"— Niv. {level}\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Compétences",
                        callback_data="skills:list",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CLASSEMENT
# ============================================================

async def show_leaderboard(
    query,
):

    await query.edit_message_text(
        (
            "🏆 **CLASSEMENT DES COMPÉTENCES**\n\n"
            "Pour afficher un classement précis, "
            "sélectionne une compétence depuis "
            "ta liste."
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎯 Mes compétences",
                        callback_data="skills:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Retour",
                        callback_data="skills:home",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def skills_callback(
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

    character_id = int(
        actor["id"]
    )

    data = str(
        query.data or ""
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "skills:home":

        skills = await get_character_skills(
            character_id
        )

        await query.edit_message_text(
            format_skills(skills),
            reply_markup=skills_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if data == "skills:list":

        await show_skills(
            query,
            character_id,
        )

        return

    # --------------------------------------------------------
    # LEADERBOARD
    # --------------------------------------------------------

    if data == "skills:leaderboard":

        await show_leaderboard(
            query
        )

        return

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if data.startswith(
        "skills:view:"
    ):

        skill_name = data[
            len("skills:view:") :
        ]

        if not skill_name:

            await query.edit_message_text(
                "❌ Compétence invalide."
            )

            return

        await show_skill(
            query,
            character_id,
            skill_name,
        )

        return

    await query.edit_message_text(
        "❌ Action de compétence inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_skills_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "skills",
            skills_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            skills_callback,
            pattern=r"^skills:",
        )
    )


__all__ = [
    "skills_command",
    "skills_callback",
    "register_skills_handlers",
]