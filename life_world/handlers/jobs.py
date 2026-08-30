"""
MANUWORLD — JOBS HANDLER

Interface Telegram du système des emplois.

Commandes :
    /jobs
    /job
    /jobsearch <recherche>
    /applyjob <job_id>
    /resign

Fonctionnalités :
    - consulter les métiers disponibles
    - rechercher un métier
    - voir les conditions
    - voir l'emploi actuel
    - postuler à un métier
    - démissionner
    - consulter l'historique professionnel

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

from life_world.systems.job_system import (
    get_jobs,
    search_jobs,
    get_job,
    get_current_employment,
    get_employment_history,
    check_job_requirements,
    hire_character,
    leave_job,
    format_job,
    format_jobs,
    format_employment,
    format_employment_history,
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


def jobs_keyboard(
    jobs: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons = []

    for job in jobs[:10]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"💼 {job['name']}",
                    callback_data=(
                        f"jobs:view:{job['id']}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "👔 Mon emploi",
                callback_data="jobs:current",
            ),
            InlineKeyboardButton(
                "📜 Historique",
                callback_data="jobs:history",
            ),
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


def job_keyboard(
    job_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Vérifier conditions",
                    callback_data=(
                        f"jobs:requirements:{job_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "📨 Postuler",
                    callback_data=(
                        f"jobs:apply:{job_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Métiers",
                    callback_data="jobs:list",
                )
            ],
        ]
    )


def current_job_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📜 Historique",
                    callback_data="jobs:history",
                )
            ],
            [
                InlineKeyboardButton(
                    "🚪 Démissionner",
                    callback_data="jobs:resign",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Métiers",
                    callback_data="jobs:list",
                )
            ],
        ]
    )


# ============================================================
# /JOBS
# ============================================================

async def jobs_command(
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

    jobs = await get_jobs(
        active_only=True,
        limit=20,
    )

    await message.reply_text(
        format_jobs(jobs),
        reply_markup=jobs_keyboard(jobs),
        parse_mode="Markdown",
    )


# ============================================================
# /JOB
# ============================================================

async def job_command(
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

    employment = await get_current_employment(
        int(actor["id"])
    )

    if employment is None:

        await message.reply_text(
            "👔 **EMPLOI ACTUEL**\n\n"
            "Tu n'as actuellement aucun emploi.\n\n"
            "Utilise `/jobs` pour consulter "
            "les métiers disponibles.",
            parse_mode="Markdown",
        )

        return

    await message.reply_text(
        format_employment(
            employment
        ),
        reply_markup=current_job_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# /JOBSEARCH
# ============================================================

async def jobsearch_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    if not context.args:

        await message.reply_text(
            "🔎 **RECHERCHE DE MÉTIER**\n\n"
            "Utilisation :\n"
            "`/jobsearch développeur`",
            parse_mode="Markdown",
        )

        return

    query = " ".join(
        context.args
    )

    jobs = await search_jobs(
        query,
        limit=20,
    )

    if not jobs:

        await message.reply_text(
            f"❌ Aucun métier trouvé pour : "
            f"`{query}`",
            parse_mode="Markdown",
        )

        return

    await message.reply_text(
        format_jobs(jobs),
        reply_markup=jobs_keyboard(jobs),
        parse_mode="Markdown",
    )


# ============================================================
# /APPLYJOB
# ============================================================

async def applyjob_command(
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

    if len(context.args) != 1:

        await message.reply_text(
            "📨 **POSTULER À UN MÉTIER**\n\n"
            "Utilisation :\n"
            "`/applyjob <job_id>`\n\n"
            "Exemple :\n"
            "`/applyjob 4`",
            parse_mode="Markdown",
        )

        return

    try:

        job_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ L'ID du métier doit être numérique."
        )

        return

    result = await hire_character(
        character_id=int(
            actor["id"]
        ),
        job_id=job_id,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible de traiter la candidature.",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# /RESIGN
# ============================================================

async def resign_command(
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

    result = await leave_job(
        int(actor["id"])
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible de quitter cet emploi.",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# AFFICHAGE D'UN MÉTIER
# ============================================================

async def show_job(
    query,
    job_id: int,
):

    job = await get_job(
        job_id
    )

    if job is None:

        await query.edit_message_text(
            "❌ Métier introuvable."
        )

        return

    await query.edit_message_text(
        format_job(job),
        reply_markup=job_keyboard(
            job_id
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CONDITIONS
# ============================================================

async def show_requirements(
    query,
    character_id: int,
    job_id: int,
):

    result = await check_job_requirements(
        character_id,
        job_id,
    )

    job = result.get(
        "job"
    )

    if job is None:

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible de vérifier les conditions.",
            )
        )

        return

    if result.get(
        "eligible"
    ):

        text = (
            "✅ **TU ES ÉLIGIBLE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💼 {job['name']}\n\n"
            "Tu remplis toutes les conditions "
            "pour postuler à ce métier."
        )

    else:

        text = (
            "❌ **TU N'ES PAS ÉLIGIBLE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💼 {job['name']}\n\n"
            f"{result.get('message', 'Condition non remplie.')}"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Métier",
                        callback_data=(
                            f"jobs:view:{job_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# EMPLOI ACTUEL
# ============================================================

async def show_current_job(
    query,
    character_id: int,
):

    employment = await get_current_employment(
        character_id
    )

    if employment is None:

        await query.edit_message_text(
            (
                "👔 **EMPLOI ACTUEL**\n\n"
                "Tu n'as actuellement aucun emploi."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💼 Voir les métiers",
                            callback_data="jobs:list",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return

    await query.edit_message_text(
        format_employment(
            employment
        ),
        reply_markup=current_job_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# HISTORIQUE
# ============================================================

async def show_history(
    query,
    character_id: int,
):

    history = await get_employment_history(
        character_id,
        limit=20,
    )

    await query.edit_message_text(
        format_employment_history(
            history
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👔 Emploi actuel",
                        callback_data="jobs:current",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Métiers",
                        callback_data="jobs:list",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def jobs_callback(
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

    parts = data.split(":")

    if len(parts) < 2:

        await query.edit_message_text(
            "❌ Action inconnue."
        )

        return

    action = parts[1]

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    if action == "list":

        jobs = await get_jobs(
            active_only=True,
            limit=20,
        )

        await query.edit_message_text(
            format_jobs(jobs),
            reply_markup=jobs_keyboard(jobs),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # EMPLOI ACTUEL
    # --------------------------------------------------------

    if action == "current":

        await show_current_job(
            query,
            character_id,
        )

        return

    # --------------------------------------------------------
    # HISTORIQUE
    # --------------------------------------------------------

    if action == "history":

        await show_history(
            query,
            character_id,
        )

        return

    # --------------------------------------------------------
    # DÉMISSION
    # --------------------------------------------------------

    if action == "resign":

        result = await leave_job(
            character_id
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible de démissionner.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💼 Métiers",
                            callback_data="jobs:list",
                        )
                    ]
                ]
            ),
        )

        return

    # --------------------------------------------------------
    # ACTIONS AVEC JOB ID
    # --------------------------------------------------------

    if action in {
        "view",
        "requirements",
        "apply",
    }:

        if len(parts) < 3:

            await query.edit_message_text(
                "❌ Métier invalide."
            )

            return

        try:

            job_id = int(
                parts[2]
            )

        except ValueError:

            await query.edit_message_text(
                "❌ ID du métier invalide."
            )

            return

        if action == "view":

            await show_job(
                query,
                job_id,
            )

            return

        if action == "requirements":

            await show_requirements(
                query,
                character_id,
                job_id,
            )

            return

        if action == "apply":

            result = await hire_character(
                character_id=character_id,
                job_id=job_id,
            )

            await query.edit_message_text(
                result.get(
                    "message",
                    "❌ Impossible de traiter la candidature.",
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "💼 Métiers",
                                callback_data="jobs:list",
                            )
                        ]
                    ]
                ),
                parse_mode="Markdown",
            )

            return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_jobs_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "jobs",
            jobs_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "job",
            job_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "jobsearch",
            jobsearch_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "applyjob",
            applyjob_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "resign",
            resign_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            jobs_callback,
            pattern=r"^jobs:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "jobs_command",
    "job_command",
    "jobsearch_command",
    "applyjob_command",
    "resign_command",
    "jobs_callback",
    "register_jobs_handlers",
]