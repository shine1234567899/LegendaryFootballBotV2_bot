from datetime import date
import secrets

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ConversationHandler,
    ContextTypes, MessageHandler, filters
)

from life_world.database import (
    ensure_life_tables, get_life_character, create_life_character
)

FIRST_NAME,NATIONALITY,GENDER,RESIDENCE=range(4)

COUNTRIES=[
("🇨🇲 Cameroun","Cameroun"),("🇫🇷 France","France"),
("🇨🇮 Côte d'Ivoire","Côte d'Ivoire"),
("🇨🇩 RD Congo","RD Congo"),("🇸🇳 Sénégal","Sénégal"),
("🇬🇦 Gabon","Gabon"),("🇨🇬 Congo","Congo"),
("🇬🇳 Guinée","Guinée"),("🇹🇬 Togo","Togo"),
("🇳🇬 Nigeria","Nigeria"),("🇬🇭 Ghana","Ghana"),
("🇧🇯 Bénin","Bénin"),("🇲🇱 Mali","Mali"),
("🇧🇫 Burkina Faso","Burkina Faso"),
("🇩🇪 Allemagne","Allemagne"),("🇬🇧 Royaume-Uni","Royaume-Uni"),
("🇺🇸 États-Unis","États-Unis"),("🇨🇦 Canada","Canada"),
("🇧🇪 Belgique","Belgique"),("🇨🇭 Suisse","Suisse")
]

def birth_date_for_9yo():
    t=date.today()
    try: return t.replace(year=t.year-9)
    except ValueError: return date(t.year-9,2,28)

def age(b):
    t=date.today()
    return t.year-b.year-((t.month,t.day)<(b.month,b.day))

def life_id():
    return f"LW-{secrets.randbelow(900000)+100000}"

def country_keyboard():
    rows=[]; row=[]
    for label,value in COUNTRIES:
        row.append(InlineKeyboardButton(label,callback_data=f"lwcountry:{value}"))
        if len(row)==2: rows.append(row); row=[]
    if row: rows.append(row)
    return InlineKeyboardMarkup(rows)

def gender_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👨 Homme",callback_data="lwgender:Homme"),
        InlineKeyboardButton("👩 Femme",callback_data="lwgender:Femme")
    ]])

async def life(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await ensure_life_tables()
    u=update.effective_user
    c=await get_life_character(u.id)
    if c:
        b=c["birth_date"]
        if hasattr(b,"date"): b=b.date()
        family=c["family_name"] or "Aucune"
        await update.effective_message.reply_text(
            "🌍 𝐋𝐈𝐅𝐄 𝐖𝐎𝐑𝐋𝐃\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {c['first_name']}{' '+family if family!='Aucune' else ''}\n"
            f"🎂 Âge : {age(b)} ans\n"
            f"🇺🇳 Nationalité : {c['nationality']}\n"
            f"⚧ Sexe : {c['gender']}\n"
            f"📍 Résidence : {c['residence_country']}\n\n"
            f"💵 Balance : {c['balance']:,} LC\n"
            f"🏦 Balance Bank : {c['balance_bank']:,} LC\n"
            f"🎓 Scolarité : {c['education_level']}\n"
            f"🪪 Carte d'identité : {'✅' if c['identity_card'] else '❌'}\n"
            f"🆔 Life ID : `{c['life_id']}`",parse_mode="Markdown")
        return ConversationHandler.END
    await update.effective_message.reply_text(
        "🌍 𝐋𝐈𝐅𝐄 𝐖𝐎𝐑𝐋𝐃\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Bienvenue dans Life World.\n"
        "Tu commences automatiquement à 🎂 9 ans.\n"
        "Le bot génère ta date de naissance.\n\n"
        "👤 Étape 1/4\nQuel est ton prénom ?")
    return FIRST_NAME

async def first_name(update,context):
    name=update.effective_message.text.strip()
    if not 1<=len(name)<=80:
        await update.effective_message.reply_text("❌ Prénom invalide.")
        return FIRST_NAME
    context.user_data["lw_name"]=name
    await update.effective_message.reply_text("🌍 Étape 2/4\n\nChoisis ta nationalité :",reply_markup=country_keyboard())
    return NATIONALITY

async def nationality(update,context):
    q=update.callback_query; await q.answer()
    if not q.data.startswith("lwcountry:"): return NATIONALITY
    context.user_data["lw_nat"]=q.data.split(":",1)[1]
    await q.edit_message_text("⚧️ Étape 3/4\n\nChoisis ton sexe :",reply_markup=gender_keyboard())
    return GENDER

async def gender(update,context):
    q=update.callback_query; await q.answer()
    if not q.data.startswith("lwgender:"): return GENDER
    context.user_data["lw_gender"]=q.data.split(":",1)[1]
    await q.edit_message_text("📍 Étape 4/4\n\nDans quel pays vis-tu ?")
    return RESIDENCE

async def residence(update,context):
    u=update.effective_user; r=update.effective_message.text.strip()
    if not 1<=len(r)<=80:
        await update.effective_message.reply_text("❌ Pays invalide.")
        return RESIDENCE
    b=birth_date_for_9yo(); lid=life_id()
    name=context.user_data["lw_name"]; nat=context.user_data["lw_nat"]; gender_=context.user_data["lw_gender"]
    await create_life_character(
        telegram_id=u.id,first_name=name,nationality=nat,gender=gender_,
        residence_country=r,birth_date=b,life_id=lid
    )
    for k in ("lw_name","lw_nat","lw_gender"): context.user_data.pop(k,None)
    await update.effective_message.reply_text(
        "🎉 𝐏𝐄𝐑𝐒𝐎𝐍𝐍𝐀𝐆𝐄 𝐂𝐑ÉÉ !\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {name}\n🎂 Âge : 9 ans\n📅 Naissance : {b.strftime('%d/%m/%Y')}\n"
        f"🇺🇳 Nationalité : {nat}\n⚧ Sexe : {gender_}\n📍 Résidence : {r}\n\n"
        "👨‍👩‍👧‍👦 Famille : Aucune\n💵 Balance : 0 LC\n🏦 Balance Bank : 0 LC\n"
        "🎓 Scolarité : École primaire\n🪪 Carte d'identité : ❌\n\n"
        f"🆔 Life ID : `{lid}`",parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update,context):
    for k in ("lw_name","lw_nat","lw_gender"): context.user_data.pop(k,None)
    await update.effective_message.reply_text("❌ Création Life World annulée.")
    return ConversationHandler.END

life_handler=ConversationHandler(
    entry_points=[CommandHandler("life",life)],
    states={
        FIRST_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND,first_name)],
        NATIONALITY:[CallbackQueryHandler(nationality,pattern=r"^lwcountry:")],
        GENDER:[CallbackQueryHandler(gender,pattern=r"^lwgender:")],
        RESIDENCE:[MessageHandler(filters.TEXT & ~filters.COMMAND,residence)],
    },
    fallbacks=[CommandHandler("cancel",cancel)],
    per_message=False,allow_reentry=True
)
