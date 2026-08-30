"""
MANUWORLD — BANK HANDLER [MWL]

Interface Telegram du système bancaire.
"""
from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from life_world.database import get_life_character
from life_world.systems.bank_system import (
    seed_default_banks,
    get_banks,
    get_bank,
    get_character_accounts,
    open_account,
    deposit,
    withdraw,
    get_bank_transactions,
    format_bank,
    format_accounts,
    format_transactions,
)

async def bank_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    message=update.effective_message
    character=await get_life_character(update.effective_user.id) if update.effective_user else None
    if not message:return
    if not character:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    await seed_default_banks()
    banks=await get_banks()
    if not banks:
        await message.reply_text("❌ Aucune banque disponible.")
        return
    buttons=[[InlineKeyboardButton(b["name"],callback_data=f"mwbank:bank:{b['id']}")] for b in banks]
    buttons.append([InlineKeyboardButton("💳 Mes comptes",callback_data="mwbank:accounts")])
    await message.reply_text("🏦 **BANQUES MANUWORLD**\n\nChoisis une banque :",reply_markup=InlineKeyboardMarkup(buttons),parse_mode="Markdown")

async def bank_callback(update,context):
    query=update.callback_query
    if not query:return
    await query.answer()
    user=update.effective_user
    character=await get_life_character(user.id) if user else None
    if not character:
        await query.edit_message_text("❌ Personnage introuvable."); return
    data=(query.data or "").split(":")
    if len(data)<2:return
    action=data[1]
    if action=="accounts":
        accounts=await get_character_accounts(int(character["id"]))
        text_msg=format_accounts(accounts) if accounts else "💳 Aucun compte bancaire."
        await query.edit_message_text(text_msg,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 Banques",callback_data="mwbank:list")]]))
        return
    if action=="list":
        banks=await get_banks()
        buttons=[[InlineKeyboardButton(b["name"],callback_data=f"mwbank:bank:{b['id']}")] for b in banks]
        await query.edit_message_text("🏦 **BANQUES MANUWORLD**",reply_markup=InlineKeyboardMarkup(buttons),parse_mode="Markdown")
        return
    if action=="bank" and len(data)>=3:
        bank=await get_bank(int(data[2]))
        if not bank:
            await query.edit_message_text("❌ Banque introuvable."); return
        await query.edit_message_text(
            format_bank(bank),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Ouvrir un compte",callback_data=f"mwbank:open:{bank['id']}")],[InlineKeyboardButton("⬅️ Banques",callback_data="mwbank:list")]])
        )
        return
    if action=="open" and len(data)>=3:
        result=await open_account(int(character["id"]),int(data[2]))
        await query.edit_message_text(result.get("message","❌ Impossible d'ouvrir le compte."))
        return

def register_bank_handlers(application:Application):
    application.add_handler(CommandHandler("bank",bank_command))
    application.add_handler(CallbackQueryHandler(bank_callback,pattern=r"^mwbank:"))

__all__=["bank_command","bank_callback","register_bank_handlers"]
