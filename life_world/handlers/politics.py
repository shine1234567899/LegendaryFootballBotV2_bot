"""MANUWORLD — Politique handler [MWL]."""
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,ContextTypes
from life_world.database import get_life_character
from life_world.systems.politics_system import ensure_open_election,get_parties,candidates,run_for,meeting,cast_vote

async def politics_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    c=await get_life_character(update.effective_user.id)
    if not c:return
    e=await ensure_open_election(); ps=await get_parties()
    txt="🏛️ **POLITIQUE MANUWORLD**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    txt+=f"🗳️ Élection : **{e['office']}**\n\n🏛️ **Partis**\n"
    txt+="\n".join(f"• {p['name']} ({p['abbreviation']}) — {p['platform']}" for p in ps)
    await update.effective_message.reply_text(txt,parse_mode="Markdown",reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🗳️ Candidats",callback_data=f"mwp:c:{e['id']}")],
        [InlineKeyboardButton("📣 Candidater",callback_data=f"mwp:r:{e['id']}")],
    ]))

async def politics_callback(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer(); parts=q.data.split(":")
    c=await get_life_character(update.effective_user.id)
    if not c:return
    if parts[1]=="r":
        await run_for(int(parts[2]),int(c["id"]))
        await q.edit_message_text("📣 Candidature enregistrée.",reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📣 Meeting",callback_data=f"mwp:m:{parts[2]}")],
            [InlineKeyboardButton("🗳️ Candidats",callback_data=f"mwp:c:{parts[2]}")]]));return
    if parts[1]=="m":
        r=await meeting(int(parts[2]),int(c["id"]));await q.edit_message_text(r["message"]);return
    if parts[1]=="c":
        cs=await candidates(int(parts[2]))
        if not cs:
            await q.edit_message_text("🗳️ Aucun candidat.",reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📣 Candidater",callback_data=f"mwp:r:{parts[2]}")]]));return
        rows=[]
        for x in cs:
            name=x.get("username") or x.get("first_name") or "Candidat"
            rows.append([InlineKeyboardButton(f"🗳️ {name} — {x['votes']} voix",
                                              callback_data=f"mwp:v:{parts[2]}:{x['id']}")])
        await q.edit_message_text("🗳️ **CANDIDATS**",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(rows));return
    if parts[1]=="v":
        r=await cast_vote(int(parts[2]),int(c["id"]),int(parts[3]));await q.edit_message_text(r["message"])

def register_politics_handlers(application:Application):
    application.add_handler(CommandHandler("politics",politics_command))
    application.add_handler(CallbackQueryHandler(politics_callback,pattern=r"^mwp:"))
