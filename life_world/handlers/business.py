"""
MANUWORLD — BUSINESS [MWL]

Commandes simples :
/business
/business_create <nom> <type> <capital> [description]
/business_withdraw <company_id> <montant>
/business_payroll <company_id>
/business_destroy <company_id>

Les opérations sensibles sont réservées au PDG.
"""

from __future__ import annotations

from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from life_world.database import get_life_character
from life_world.systems.business_system import (
    create_company,
    destroy_company,
    format_company,
    get_character_companies,
    get_company,
    get_company_members,
    get_company_treasury,
    get_shareholders,
    pay_company_salaries,
    withdraw_from_company,
    set_employee_salary,
    fire_employee,
)


async def get_actor(update: Update) -> dict[str, Any] | None:
    user = update.effective_user
    if user is None:
        return None
    character = await get_life_character(user.id)
    return dict(character) if character else None


def format_money(value: int) -> str:
    return f"{int(value or 0):,}".replace(",", " ")


def business_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏢 Mes entreprises", callback_data="business:list")]
    ])


def company_keyboard(company_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Membres", callback_data=f"business:members:{company_id}"),
            InlineKeyboardButton("💰 Trésorerie", callback_data=f"business:treasury:{company_id}"),
        ],
        [
            InlineKeyboardButton("💵 Retirer", callback_data=f"business:withdraw_help:{company_id}"),
            InlineKeyboardButton("💸 Salaires", callback_data=f"business:payroll:{company_id}"),
        ],
        [
            InlineKeyboardButton("🗑️ Détruire", callback_data=f"business:destroy:{company_id}"),
        ],
        [InlineKeyboardButton("⬅️ Mes entreprises", callback_data="business:list")],
    ])


def format_companies(companies: list[dict]) -> str:
    if not companies:
        return (
            "🏢 **MES ENTREPRISES**\n\n"
            "Aucune entreprise.\n"
            "Utilise `/business_create` pour en créer une."
        )
    lines = ["🏢 **MES ENTREPRISES**", "━━━━━━━━━━━━━━━━━━━━", ""]
    for c in companies:
        lines += [
            f"🏢 **{c.get('name', 'Entreprise')}**",
            f"🆔 ID : `{c.get('id')}`",
            f"💰 Trésorerie : {format_money(c.get('treasury'))} FCFA",
            f"📊 Statut : {c.get('status') or ('active' if c.get('active') else 'closed')}",
            "",
        ]
    return "\n".join(lines)


async def business_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    actor = await get_actor(update)
    if message is None:
        return
    if actor is None:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    companies = await get_character_companies(int(actor["id"]))
    await message.reply_text(
        format_companies(companies),
        reply_markup=business_keyboard(),
        parse_mode="Markdown",
    )


async def businesses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await business_command(update, context)


async def business_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    actor = await get_actor(update)
    if message is None:
        return
    if actor is None:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    if len(context.args) < 3:
        await message.reply_text(
            "🏢 **CRÉER UNE ENTREPRISE**\n\n"
            "`/business_create <nom> <type> <capital> [description]`\n\n"
            "Exemple :\n"
            "`/business_create ManuTech tech 1000000 Société informatique`",
            parse_mode="Markdown",
        )
        return
    try:
        capital = int(context.args[2])
    except ValueError:
        await message.reply_text("❌ Le capital doit être un nombre.")
        return
    if capital < 0:
        await message.reply_text("❌ Le capital ne peut pas être négatif.")
        return

    result = await create_company(
        int(actor["id"]),
        context.args[0],
        context.args[1],
        " ".join(context.args[3:]),
        capital,
    )
    await message.reply_text(result["message"])


async def business_withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    actor = await get_actor(update)
    if message is None:
        return
    if actor is None:
        await message.reply_text("❌ Personnage introuvable.")
        return
    if len(context.args) != 2:
        await message.reply_text("Utilisation : `/business_withdraw <company_id> <montant>`", parse_mode="Markdown")
        return
    try:
        company_id, amount = int(context.args[0]), int(context.args[1])
    except ValueError:
        await message.reply_text("❌ ID et montant doivent être numériques.")
        return
    result = await withdraw_from_company(company_id, int(actor["id"]), amount)
    await message.reply_text(result["message"])


async def business_payroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    actor = await get_actor(update)
    if message is None:
        return
    if actor is None:
        await message.reply_text("❌ Personnage introuvable.")
        return
    if len(context.args) != 1:
        await message.reply_text("Utilisation : `/business_payroll <company_id>`", parse_mode="Markdown")
        return
    try:
        company_id = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ ID entreprise invalide.")
        return
    result = await pay_company_salaries(company_id, int(actor["id"]))
    await message.reply_text(result["message"], parse_mode="Markdown")


async def business_destroy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    actor = await get_actor(update)
    if message is None:
        return
    if actor is None:
        await message.reply_text("❌ Personnage introuvable.")
        return
    if len(context.args) != 1:
        await message.reply_text("Utilisation : `/business_destroy <company_id>`", parse_mode="Markdown")
        return
    try:
        company_id = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ ID entreprise invalide.")
        return
    result = await destroy_company(company_id, int(actor["id"]))
    await message.reply_text(result["message"], parse_mode="Markdown")


async def show_company(query, company_id: int):
    company = await get_company(company_id)
    if company is None:
        await query.edit_message_text("❌ Entreprise introuvable.")
        return
    await query.edit_message_text(
        format_company(company),
        reply_markup=company_keyboard(company_id),
        parse_mode="HTML",
    )


async def show_members(query, company_id: int):
    members = await get_company_members(company_id)
    if not members:
        text = "👥 **MEMBRES**\n\nAucun membre."
    else:
        text = "👥 **MEMBRES**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "\n".join(
            f"• {m.get('username') or m.get('virtual_name') or m.get('first_name') or 'Employé'} — "
            f"{m.get('position') or 'Employee'} — {format_money(m.get('salary'))} FCFA"
            for m in members
        )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Entreprise", callback_data=f"business:view:{company_id}")]]),
        parse_mode="Markdown",
    )


async def show_treasury(query, company_id: int):
    company = await get_company(company_id)
    if company is None:
        await query.edit_message_text("❌ Entreprise introuvable.")
        return
    treasury = await get_company_treasury(company_id)
    await query.edit_message_text(
        f"💰 **TRÉSORERIE**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏢 {company.get('name')}\n"
        f"💵 **{format_money(treasury)} FCFA**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Entreprise", callback_data=f"business:view:{company_id}")]]),
        parse_mode="Markdown",
    )


async def business_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor = await get_actor(update)
    if query is None or actor is None:
        return
    await query.answer()
    parts = str(query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "list":
        companies = await get_character_companies(int(actor["id"]))
        buttons = [
            [InlineKeyboardButton(c["name"], callback_data=f"business:view:{c['id']}")]
            for c in companies
        ]
        buttons.append([InlineKeyboardButton("🔄 Actualiser", callback_data="business:list")])
        await query.edit_message_text(
            format_companies(companies),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    if len(parts) < 3:
        await query.edit_message_text("❌ Entreprise invalide.")
        return
    try:
        company_id = int(parts[2])
    except ValueError:
        await query.edit_message_text("❌ ID entreprise invalide.")
        return

    company = await get_company(company_id)
    if company is None:
        await query.edit_message_text("❌ Entreprise introuvable.")
        return

    if int(company.get("owner_character_id") or -1) != int(actor["id"]):
        await query.edit_message_text("❌ Seul le PDG peut gérer cette entreprise.")
        return

    if action == "view":
        await show_company(query, company_id)
    elif action == "members":
        await show_members(query, company_id)
    elif action == "treasury":
        await show_treasury(query, company_id)
    elif action == "payroll":
        result = await pay_company_salaries(company_id, int(actor["id"]))
        await query.edit_message_text(result["message"], parse_mode="Markdown")
    elif action == "withdraw_help":
        await query.edit_message_text(
            "💵 **RETIRER DE LA TRÉSORERIE**\n\n"
            f"Utilise : `/business_withdraw {company_id} <montant>`\n\n"
            "L'argent est versé directement sur le compte du PDG.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Entreprise", callback_data=f"business:view:{company_id}")]
            ]),
            parse_mode="Markdown",
        )
    elif action == "destroy":
        await query.edit_message_text(
            "⚠️ **DÉTRUIRE L'ENTREPRISE ?**\n\n"
            "Cette action supprime définitivement l'entreprise.\n"
            "La trésorerie restante sera versée au PDG.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirmer", callback_data=f"business:destroy_confirm:{company_id}"),
                    InlineKeyboardButton("❌ Annuler", callback_data=f"business:view:{company_id}"),
                ]
            ]),
            parse_mode="Markdown",
        )
    elif action == "destroy_confirm":
        result = await destroy_company(company_id, int(actor["id"]))
        await query.edit_message_text(result["message"], parse_mode="Markdown")


def register_business_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("business", business_command))
    application.add_handler(CommandHandler("businesses", businesses_command))
    application.add_handler(CommandHandler("business_create", business_create_command))
    application.add_handler(CommandHandler("business_withdraw", business_withdraw_command))
    application.add_handler(CommandHandler("business_payroll", business_payroll_command))
    application.add_handler(CommandHandler("business_destroy", business_destroy_command))
    application.add_handler(CommandHandler("business_setsalary", business_setsalary_command))
    application.add_handler(CommandHandler("business_fire", business_fire_command))
    application.add_handler(CallbackQueryHandler(business_callback, pattern=r"^business:"))


__all__ = [
    "business_command", "businesses_command", "business_create_command",
    "business_withdraw_command", "business_payroll_command", "business_destroy_command",
    "business_callback", "register_business_handlers",
]


async def _company_target(update: Update):
    from life_world.utils.targeting import resolve_target
    return await resolve_target(update, allow_self=False)


async def business_setsalary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message=update.effective_message; actor=await get_actor(update)
    if not message:return
    if not actor:return await message.reply_text("❌ Personnage introuvable.")
    if len(context.args)<1:
        return await message.reply_text("Réponds à l'employé : `/business_setsalary 50000`\nou utilise `/business_setsalary @username 50000`",parse_mode="Markdown")
    try: salary=int(context.args[-1].replace(" ","").replace(",",""))
    except ValueError:return await message.reply_text("❌ Salaire invalide.")
    target=await _company_target(update)
    if not target.character:return await message.reply_text(target.error or "❌ Employé introuvable.")
    companies=await get_character_companies(int(actor["id"]))
    if not companies:return await message.reply_text("❌ Tu n'as pas d'entreprise.")
    company_id=int(context.args[0]) if context.args[0].isdigit() and len(context.args)>1 else int(companies[0]["id"])
    result=await set_employee_salary(company_id,int(actor["id"]),int(target.character["id"]),salary)
    await message.reply_text(result["message"],parse_mode="Markdown")


async def business_fire_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message=update.effective_message; actor=await get_actor(update)
    if not message:return
    if not actor:return await message.reply_text("❌ Personnage introuvable.")
    target=await _company_target(update)
    if not target.character:return await message.reply_text(target.error or "❌ Employé introuvable.")
    companies=await get_character_companies(int(actor["id"]))
    if not companies:return await message.reply_text("❌ Tu n'as pas d'entreprise.")
    company_id=int(context.args[0]) if context.args and context.args[0].isdigit() else int(companies[0]["id"])
    result=await fire_employee(company_id,int(actor["id"]),int(target.character["id"]))
    await message.reply_text(result["message"],parse_mode="Markdown")
