"""MANUWORLD — Hôpital handler [MWL]."""
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,ContextTypes
from life_world.database import get_life_character
from life_world.systems.hospital_system import create_visit,pay_part,get_visit

def kb(v):
    rows=[]
    if not v["consultation_paid"]:
        rows.append([InlineKeyboardButton(f"💳 Consultation ({v['consultation_fee']:,} FCFA)",callback_data=f"mwh:pay:consultation:{v['id']}")])
    if not v["treatment_paid"] and int(v["treatment_fee"] or 0):
        rows.append([InlineKeyboardButton(f"💊 Soins ({v['treatment_fee']:,} FCFA)",callback_data=f"mwh:pay:treatment:{v['id']}")])
    if not v["operation_paid"] and int(v["operation_fee"] or 0):
        rows.append([InlineKeyboardButton(f"🏥 Opération ({v['operation_fee']:,} FCFA)",callback_data=f"mwh:pay:operation:{v['id']}")])
    return InlineKeyboardMarkup(rows) if rows else None

async def hospital_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    c=await get_life_character(update.effective_user.id)
    if not c: await update.effective_message.reply_text("❌ Crée d'abord ton personnage avec /life."); return
    r=await create_visit(int(c["id"]))
    if not r["success"]: await update.effective_message.reply_text(r["message"]); return
    v={"id":r["id"],"consultation_paid":False,"treatment_paid":False,"operation_paid":False,
       "consultation_fee":r["consultation_fee"],"treatment_fee":r["treatment_fee"],"operation_fee":r["operation_fee"]}
    txt=(f"🏥 **HÔPITAL MANUWORLD**\n━━━━━━━━━━━━━━━━━━━━\n\n"
         f"👨‍⚕️ Diagnostic : **{r['diagnosis']}**\n"
         f"⚠️ Gravité : **{r['severity']}**\n"
         f"❤️ Conseil : {r['advice']}\n\n"
         f"🧾 Consultation : **{r['consultation_fee']:,} FCFA**\n"
         f"💊 Soins : **{r['treatment_fee']:,} FCFA**")
    if r["operation_fee"]: txt+=f"\n🏥 Opération : **{r['operation_fee']:,} FCFA**"
    await update.effective_message.reply_text(txt,parse_mode="Markdown",reply_markup=kb(v))

async def hospital_callback(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    _,_,part,vid=q.data.split(":")
    c=await get_life_character(update.effective_user.id)
    if not c: return
    r=await pay_part(int(c["id"]),int(vid),part)
    v=await get_visit(int(c["id"]),int(vid))
    await q.edit_message_text(r["message"]+(f"\n❤️ Santé +{r['heal']}" if r.get("heal") else ""),reply_markup=kb(v) if v else None)

def register_hospital_handlers(application:Application):
    application.add_handler(CommandHandler("hospital",hospital_command))
    application.add_handler(CallbackQueryHandler(hospital_callback,pattern=r"^mwh:"))
