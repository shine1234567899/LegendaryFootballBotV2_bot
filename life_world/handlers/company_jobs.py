"""
MANUWORLD — COMPANY JOBS HANDLER

Gestion Telegram des offres d'emploi créées par
les entreprises.

Fonctionnalités :
    - créer une offre d'emploi
    - consulter les offres d'une entreprise
    - consulter les offres d'une entreprise possédée
    - postuler à une offre
    - afficher les offres ouvertes

Commandes :
    /joboffers
    /companyjobs <company_id>
    /createjob <company_id> <titre> <salaire> [description]
    /applyjoboffer <job_id> [message]

IMPORTANT :
    - utilise business_system.py ;
    - ne crée pas de nouvelle base ;
    - ne modifie pas main.py.
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

from life_world.systems.business_system import (
    create_job_ad,
    get_job_ads,
    get_character_companies,
    apply_to_job,
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


def format_money(
    amount: int | float | None,
) -> str:

    return f"{int(amount or 0):,}".replace(
        ",",
        " ",
    )


def safe_text(
    value: Any,
    fallback: str = "—",
) -> str:

    if value is None:
        return fallback

    value = str(value).strip()

    return value if value else fallback


# ============================================================
# FORMATAGE D'UNE OFFRE
# ============================================================

def format_job_offer(
    offer: dict[str, Any],
) -> str:

    job_id = offer.get(
        "id",
        "—",
    )

    title = safe_text(
        offer.get("title"),
        "Offre d'emploi",
    )

    description = safe_text(
        offer.get("description"),
        "Aucune description.",
    )

    salary = int(
        offer.get("salary") or 0
    )

    status = safe_text(
        offer.get("status"),
        "unknown",
    )

    company_id = offer.get(
        "company_id",
        "—",
    )

    return (
        "📢━━━━━━━━━━━━━━━━━━━━📢\n"
        f"       **{title}**\n"
        "📢━━━━━━━━━━━━━━━━━━━━📢\n\n"
        f"🆔 Offre : **#{job_id}**\n"
        f"🏢 Entreprise : #{company_id}\n"
        f"💰 Salaire : **{format_money(salary)} FCFA**\n"
        f"📊 Statut : **{status}**\n\n"
        f"📝 {description}"
    )


def format_job_offers(
    offers: list[dict[str, Any]],
) -> str:

    if not offers:

        return (
            "📢 **OFFRES D'EMPLOI**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Aucune offre disponible."
        )

    lines = [
        "📢 **OFFRES D'EMPLOI**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for offer in offers:

        job_id = offer.get(
            "id",
            "—",
        )

        title = safe_text(
            offer.get("title"),
            "Offre",
        )

        salary = int(
            offer.get("salary") or 0
        )

        company_id = offer.get(
            "company_id",
            "—",
        )

        lines.extend(
            [
                f"📢 **#{job_id} — {title}**",
                f"   🏢 Entreprise : #{company_id}",
                (
                    f"   💰 Salaire : "
                    f"{format_money(salary)} FCFA"
                ),
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# CLAVIERS
# ============================================================

def offer_keyboard(
    job_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📨 Postuler",
                    callback_data=(
                        f"companyjobs:apply:{job_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data=(
                        f"companyjobs:view:{job_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "📢 Offres",
                    callback_data="companyjobs:list",
                ),
            ],
        ]
    )


def offers_keyboard(
    offers: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons = []

    for offer in offers[:10]:

        job_id = offer.get("id")

        if job_id is None:
            continue

        title = safe_text(
            offer.get("title"),
            "Offre",
        )

        if len(title) > 30:
            title = title[:27] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📢 {title}",
                    callback_data=(
                        f"companyjobs:view:{job_id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        buttons
        + [
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="companyjobs:list",
                )
            ]
        ]
    )


# ============================================================
# /JOBOFFERS
# ============================================================

async def joboffers_command(
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

    companies = await get_character_companies(
        int(actor["id"])
    )

    all_offers: list[dict[str, Any]] = []

    for company in companies:

        company_id = company.get("id")

        if company_id is None:
            continue

        offers = await get_job_ads(
            int(company_id),
            open_only=True,
        )

        all_offers.extend(
            offers
        )

    await message.reply_text(
        format_job_offers(
            all_offers
        ),
        reply_markup=offers_keyboard(
            all_offers
        ),
        parse_mode="Markdown",
    )


# ============================================================
# /COMPANYJOBS
# ============================================================

async def companyjobs_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    if len(context.args) != 1:

        await message.reply_text(
            "📢 **OFFRES D'UNE ENTREPRISE**\n\n"
            "Utilisation :\n"
            "`/companyjobs <company_id>`\n\n"
            "Exemple :\n"
            "`/companyjobs 12`",
            parse_mode="Markdown",
        )

        return

    try:

        company_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID entreprise invalide."
        )

        return

    offers = await get_job_ads(
        company_id,
        open_only=True,
    )

    await message.reply_text(
        format_job_offers(
            offers
        ),
        reply_markup=offers_keyboard(
            offers
        ),
        parse_mode="Markdown",
    )


# ============================================================
# /CREATEJOB
# ============================================================

async def createjob_command(
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

    if len(context.args) < 3:

        await message.reply_text(
            "📢 **CRÉER UNE OFFRE D'EMPLOI**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Utilisation :\n"
            "`/createjob <company_id> <titre> <salaire> [description]`\n\n"
            "Exemple :\n"
            "`/createjob 5 Developpeur 350000 Recherche Python`",
            parse_mode="Markdown",
        )

        return

    try:

        company_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID entreprise invalide."
        )

        return

    title = context.args[1]

    try:

        salary = int(
            context.args[2]
        )

    except ValueError:

        await message.reply_text(
            "❌ Le salaire doit être un nombre."
        )

        return

    description = " ".join(
        context.args[3:]
    )

    result = await create_job_ad(
        company_id=company_id,
        character_id=int(
            actor["id"]
        ),
        title=title,
        description=description,
        salary=salary,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible de créer l'offre.",
        )
    )


# ============================================================
# /APPLYJOBOFFER
# ============================================================

async def applyjoboffer_command(
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

    if len(context.args) < 1:

        await message.reply_text(
            "📨 **POSTULER À UNE OFFRE**\n\n"
            "Utilisation :\n"
            "`/applyjoboffer <job_id> [message]`\n\n"
            "Exemple :\n"
            "`/applyjoboffer 7 Je suis très motivé.`",
            parse_mode="Markdown",
        )

        return

    try:

        job_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ ID de l'offre invalide."
        )

        return

    application_message = " ".join(
        context.args[1:]
    )

    result = await apply_to_job(
        job_id=job_id,
        character_id=int(
            actor["id"]
        ),
        message=application_message,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible d'envoyer la candidature.",
        )
    )


# ============================================================
# AFFICHER UNE OFFRE
# ============================================================

async def show_offer(
    query,
    job_id: int,
):

    # On recherche l'offre parmi les entreprises
    # auxquelles l'utilisateur a accès n'est pas possible
    # ici sans le personnage ; on récupère donc l'offre
    # directement via une requête SQL locale au handler.

    from database.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT *
                FROM life_company_job_ads
                WHERE id = :job_id
                LIMIT 1
                """
            ),
            {
                "job_id": int(job_id),
            },
        )

        row = result.mappings().first()

    if row is None:

        await query.edit_message_text(
            "❌ Offre d'emploi introuvable."
        )

        return

    offer = dict(row)

    await query.edit_message_text(
        format_job_offer(
            offer
        ),
        reply_markup=offer_keyboard(
            job_id
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def companyjobs_callback(
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

        companies = await get_character_companies(
            int(actor["id"])
        )

        all_offers: list[dict[str, Any]] = []

        for company in companies:

            company_id = company.get("id")

            if company_id is None:
                continue

            offers = await get_job_ads(
                int(company_id),
                open_only=True,
            )

            all_offers.extend(
                offers
            )

        await query.edit_message_text(
            format_job_offers(
                all_offers
            ),
            reply_markup=offers_keyboard(
                all_offers
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if action == "view":

        if len(parts) < 3:

            await query.edit_message_text(
                "❌ Offre invalide."
            )

            return

        try:

            job_id = int(
                parts[2]
            )

        except ValueError:

            await query.edit_message_text(
                "❌ ID de l'offre invalide."
            )

            return

        await show_offer(
            query,
            job_id,
        )

        return

    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------

    if action == "apply":

        if len(parts) < 3:

            await query.edit_message_text(
                "❌ Offre invalide."
            )

            return

        try:

            job_id = int(
                parts[2]
            )

        except ValueError:

            await query.edit_message_text(
                "❌ ID de l'offre invalide."
            )

            return

        result = await apply_to_job(
            job_id=job_id,
            character_id=int(
                actor["id"]
            ),
            message="",
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible d'envoyer la candidature.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📢 Offres",
                            callback_data="companyjobs:list",
                        )
                    ]
                ]
            ),
        )

        return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_company_jobs_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "joboffers",
            joboffers_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "companyjobs",
            companyjobs_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "createjob",
            createjob_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "applyjoboffer",
            applyjoboffer_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            companyjobs_callback,
            pattern=r"^companyjobs:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "joboffers_command",
    "companyjobs_command",
    "createjob_command",
    "applyjoboffer_command",
    "companyjobs_callback",
    "register_company_jobs_handlers",
]