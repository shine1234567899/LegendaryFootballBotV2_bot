"""
MANUWORLD — BUSINESS HANDLER

Interface Telegram du système d'entreprises.

Commandes :
    /business
    /business_create <nom> <type> <capital> [description]
    /businesses

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

from life_world.systems.business_system import (
    create_company,
    get_company,
    get_character_companies,
    get_company_members,
    get_shareholders,
    get_company_treasury,
    format_company,
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


def business_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏢 Mes entreprises",
                    callback_data="business:list",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="business:list",
                )
            ],
        ]
    )


def company_keyboard(
    company_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👥 Membres",
                    callback_data=f"business:members:{company_id}",
                ),
                InlineKeyboardButton(
                    "📊 Actionnaires",
                    callback_data=f"business:shares:{company_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "💰 Trésorerie",
                    callback_data=f"business:treasury:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Mes entreprises",
                    callback_data="business:list",
                )
            ],
        ]
    )


# ============================================================
# AFFICHAGE DES ENTREPRISES
# ============================================================

def format_companies(
    companies: list[dict[str, Any]],
) -> str:

    if not companies:

        return (
            "🏢 **MES ENTREPRISES**\n\n"
            "Tu ne possèdes aucune entreprise."
        )

    lines = [
        "🏢 **MES ENTREPRISES**",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for company in companies:

        name = company.get(
            "name",
            "Entreprise",
        )

        company_type = company.get(
            "company_type",
            "—",
        )

        status = company.get(
            "status",
            "—",
        )

        treasury = int(
            company.get("treasury") or 0
        )

        reputation = int(
            company.get("reputation") or 0
        )

        lines.extend(
            [
                f"🏢 **{name}**",
                f"   🆔 ID : {company.get('id')}",
                f"   📂 Type : {company_type}",
                f"   📊 Statut : {status}",
                (
                    f"   💰 Trésorerie : "
                    f"{treasury:,} FCFA"
                ).replace(",", " "),
                f"   ⭐ Réputation : {reputation}",
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================
# /BUSINESS
# ============================================================

async def business_command(
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

    await message.reply_text(
        format_companies(companies),
        reply_markup=business_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# /BUSINESSES
# ============================================================

async def businesses_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await business_command(
        update,
        context,
    )


# ============================================================
# /BUSINESS_CREATE
# ============================================================

async def business_create_command(
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

    if len(context.args) < 3:

        await message.reply_text(
            "🏢 **CRÉER UNE ENTREPRISE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Utilisation :\n"
            "`/business_create <nom> <type> <capital> [description]`\n\n"
            "Exemple :\n"
            "`/business_create ManuTech technology 1000000 Société informatique`",
            parse_mode="Markdown",
        )

        return

    name = context.args[0]
    company_type = context.args[1]

    try:
        initial_capital = int(
            context.args[2]
        )
    except ValueError:

        await message.reply_text(
            "❌ Le capital doit être un nombre."
        )

        return

    description = " ".join(
        context.args[3:]
    )

    result = await create_company(
        owner_character_id=int(
            actor["id"]
        ),
        name=name,
        company_type=company_type,
        description=description,
        initial_capital=initial_capital,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible de créer l'entreprise.",
        ),
        parse_mode="HTML",
    )


# ============================================================
# ENTREPRISE
# ============================================================

async def show_company(
    query,
    company_id: int,
):

    company = await get_company(
        company_id
    )

    if company is None:

        await query.edit_message_text(
            "❌ Entreprise introuvable."
        )

        return

    await query.edit_message_text(
        format_company(company),
        reply_markup=company_keyboard(
            company_id
        ),
        parse_mode="HTML",
    )


# ============================================================
# MEMBRES
# ============================================================

async def show_members(
    query,
    company_id: int,
):

    members = await get_company_members(
        company_id
    )

    if not members:

        text = (
            "👥 **MEMBRES DE L'ENTREPRISE**\n\n"
            "Aucun membre."
        )

    else:

        lines = [
            "👥 **MEMBRES DE L'ENTREPRISE**",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for member in members:

            name = (
                member.get("first_name")
                or member.get("username")
                or f"Personnage #{member.get('character_id')}"
            )

            grade = member.get(
                "grade",
                "—",
            )

            status = member.get(
                "status",
                "—",
            )

            lines.append(
                f"👤 **{name}** — "
                f"{grade} — {status}"
            )

        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Entreprise",
                        callback_data=f"business:view:{company_id}",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# ACTIONNAIRES
# ============================================================

async def show_shareholders(
    query,
    company_id: int,
):

    shareholders = await get_shareholders(
        company_id
    )

    if not shareholders:

        text = (
            "📊 **ACTIONNAIRES**\n\n"
            "Aucun actionnaire enregistré."
        )

    else:

        lines = [
            "📊 **ACTIONNAIRES**",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for shareholder in shareholders:

            name = (
                shareholder.get("first_name")
                or shareholder.get("username")
                or f"Personnage #{shareholder.get('character_id')}"
            )

            shares = int(
                shareholder.get("shares") or 0
            )

            percentage = shareholder.get(
                "ownership_percentage"
            )

            line = (
                f"👤 **{name}** — "
                f"{shares} action(s)"
            )

            if percentage is not None:

                line += (
                    f" — {percentage}%"
                )

            lines.append(line)

        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Entreprise",
                        callback_data=f"business:view:{company_id}",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# TRÉSORERIE
# ============================================================

async def show_treasury(
    query,
    company_id: int,
):

    company = await get_company(
        company_id
    )

    if company is None:

        await query.edit_message_text(
            "❌ Entreprise introuvable."
        )

        return

    treasury = await get_company_treasury(
        company_id
    )

    await query.edit_message_text(
        (
            "💰 **TRÉSORERIE DE L'ENTREPRISE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 {company.get('name', 'Entreprise')}\n\n"
            f"💵 **{treasury:,} FCFA**"
        ).replace(",", " "),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Entreprise",
                        callback_data=f"business:view:{company_id}",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def business_callback(
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

        await query.edit_message_text(
            format_companies(companies),
            reply_markup=business_keyboard(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # VUE ENTREPRISE
    # --------------------------------------------------------

    if action in {
        "view",
        "members",
        "shares",
        "treasury",
    }:

        if len(parts) < 3:

            await query.edit_message_text(
                "❌ Entreprise invalide."
            )

            return

        try:
            company_id = int(
                parts[2]
            )
        except ValueError:

            await query.edit_message_text(
                "❌ ID entreprise invalide."
            )

            return

        company = await get_company(
            company_id
        )

        if company is None:

            await query.edit_message_text(
                "❌ Entreprise introuvable."
            )

            return

        companies = await get_character_companies(
            int(actor["id"])
        )

        owned_company_ids = {
            int(
                company_item["id"]
            )
            for company_item in companies
        }

        if company_id not in owned_company_ids:

            await query.edit_message_text(
                "❌ Tu n'as pas accès à cette entreprise."
            )

            return

        if action == "view":

            await show_company(
                query,
                company_id,
            )

        elif action == "members":

            await show_members(
                query,
                company_id,
            )

        elif action == "shares":

            await show_shareholders(
                query,
                company_id,
            )

        elif action == "treasury":

            await show_treasury(
                query,
                company_id,
            )

        return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_business_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "business",
            business_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "businesses",
            businesses_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "business_create",
            business_create_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            business_callback,
            pattern=r"^business:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "business_command",
    "businesses_command",
    "business_create_command",
    "business_callback",
    "register_business_handlers",
]