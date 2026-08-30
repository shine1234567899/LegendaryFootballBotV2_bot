"""
MANUWORLD — EDUCATION [MWL]

Parcours :
    École primaire / CM2 -> CEP
    Collège / 3e -> BEPC
    Lycée / Première -> Probatoire
    Lycée / Terminale -> Baccalauréat
    Études supérieures -> Université

[MWL] /school
[MWL] /study
[MWL] /domain
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import text
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from life_world.database import AsyncSessionLocal, get_life_character

STUDY_COOLDOWN_SECONDS = 5 * 60 * 60
STUDY_XP_REWARD = 25

SCHOOL_LEVELS = [
    {"key":"primary","education_level":"École primaire","class_name":"CM2","diploma":"CEP","next_level":"Collège","next_class":"3e","next_diploma":"BEPC"},
    {"key":"college","education_level":"Collège","class_name":"3e","diploma":"BEPC","next_level":"Lycée","next_class":"Première","next_diploma":"Probatoire"},
    {"key":"high_school","education_level":"Lycée","class_name":"Première","diploma":"Probatoire","next_level":"Lycée","next_class":"Terminale","next_diploma":"Baccalauréat"},
    {"key":"terminal","education_level":"Lycée","class_name":"Terminale","diploma":"Baccalauréat","next_level":"Études supérieures","next_class":"Université","next_diploma":None},
    {"key":"university","education_level":"Études supérieures","class_name":"Université","diploma":None,"next_level":None,"next_class":None,"next_diploma":None},
]

EDUCATION_DOMAINS = {
    "science":"🔬 Sciences",
    "technology":"💻 Technologie & Informatique",
    "economics":"💰 Économie & Gestion",
    "law":"⚖️ Droit",
    "medicine":"🩺 Santé & Médecine",
    "arts":"🎨 Arts & Création",
    "communication":"🎙️ Communication & Médias",
    "engineering":"⚙️ Ingénierie",
}

def normalize_domain(domain: str) -> str:
    aliases = {
        "general":"general","général":"general","science":"science","sciences":"science",
        "technology":"technology","technologie":"technology",
        "economics":"economics","economie":"economics","économie":"economics",
        "law":"law","droit":"law","medicine":"medicine","medecine":"medicine","médecine":"medicine",
        "arts":"arts","art":"arts","communication":"communication","engineering":"engineering","ingénierie":"engineering",
    }
    value=str(domain or "").strip().lower()
    if value not in aliases:
        raise ValueError("Domaine scolaire inconnu.")
    return aliases[value]

def get_character_domain(character):
    value = character.get("education_domain") or character.get("domain") or character.get("school_domain")
    if not value:
        return None
    try: return normalize_domain(value)
    except ValueError: return None

def build_domain_keyboard():
    keys=list(EDUCATION_DOMAINS)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(EDUCATION_DOMAINS[k], callback_data=f"edu_domain:{k}") for k in keys[i:i+2]]
        for i in range(0,len(keys),2)
    ])

async def save_education_domain(character_id:int, domain:str)->bool:
    domain=normalize_domain(domain)
    async with AsyncSessionLocal() as session:
        await session.execute(text("ALTER TABLE life_characters ADD COLUMN IF NOT EXISTS education_domain VARCHAR(80)"))
        result=await session.execute(text("""
            UPDATE life_characters SET education_domain=:domain, updated_at=NOW()
            WHERE id=:character_id RETURNING id
        """),{"domain":domain,"character_id":character_id})
        await session.commit()
        return result.first() is not None

async def get_actor(update):
    user=update.effective_user
    return await get_life_character(user.id) if user else None

def current_level(character):
    education=str(character.get("education_level") or "").lower()
    diploma=str(character.get("current_diploma") or character.get("diploma_level") or "").lower()
    if "univers" in education or "supérieur" in education or "superieur" in education: return SCHOOL_LEVELS[4]
    if "terminal" in education or "baccalaur" in diploma: return SCHOOL_LEVELS[3]
    if "lycée" in education or "lycee" in education:
        if "baccalaur" in diploma: return SCHOOL_LEVELS[3]
        return SCHOOL_LEVELS[2]
    if "collège" in education or "college" in education or "bepc" in diploma: return SCHOOL_LEVELS[1]
    return SCHOOL_LEVELS[0]

def safe_name(character):
    if character.get("username"): return f"@{character['username']}"
    return " ".join(x for x in (character.get("first_name"),character.get("last_name")) if x) or "Joueur"

async def ensure_active_school_year(session, character_id, level):
    existing=await session.execute(text("""
        SELECT id FROM life_school_years WHERE character_id=:character_id AND result='in_progress'
        ORDER BY id DESC LIMIT 1
    """),{"character_id":character_id})
    row=existing.first()
    if row: return row[0]
    result=await session.execute(text("""
        INSERT INTO life_school_years(character_id,class_name,academic_year,average,result)
        VALUES(:character_id,:class_name,:academic_year,0,'in_progress') RETURNING id
    """),{"character_id":character_id,"class_name":level["class_name"],"academic_year":datetime.now(timezone.utc).year})
    return result.scalar_one()

async def get_active_school_year(session, character_id):
    result=await session.execute(text("""
        SELECT id,class_name,academic_year,average,result
        FROM life_school_years WHERE character_id=:character_id AND result='in_progress'
        ORDER BY id DESC LIMIT 1
    """),{"character_id":character_id})
    return result.mappings().first()

async def school_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    message=update.effective_message
    character=await get_actor(update)
    if not message:return
    if not character:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    level=current_level(character)
    async with AsyncSessionLocal() as session:
        year=await get_active_school_year(session,character["id"])
        if not year:
            await ensure_active_school_year(session,character["id"],level)
            await session.commit()
            year=await get_active_school_year(session,character["id"])
    xp=int(character.get("school_xp") or 0)
    required=int(character.get("school_xp_required") or 100)
    diploma=level["diploma"] or character.get("current_diploma") or "Aucun"
    lines=[
        "🎓 **PARCOURS SCOLAIRE**","━━━━━━━━━━━━━━━━━━━━",
        f"👤 Élève : **{safe_name(character)}**",
        f"🏫 Niveau : **{level['education_level']}**",
        f"📚 Classe : **{level['class_name']}**",
        f"📜 Diplôme : **{diploma}**",
        f"⭐ XP scolaire : **{xp}/{required}**",
    ]
    if level["next_level"]:
        lines += ["","➡️ **Prochaine étape**",f"🏫 {level['next_level']}",f"📚 {level['next_class']}"]
        if level["next_diploma"]: lines.append(f"📜 Diplôme : {level['next_diploma']}")
    else: lines += ["","🎓 Études supérieures atteintes."]
    await message.reply_text("\n".join(lines),parse_mode="Markdown")

async def ensure_study_column():
    async with AsyncSessionLocal() as session:
        result=await session.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name='life_characters' AND column_name='last_study_at' LIMIT 1
        """))
        if result.first() is None:
            await session.execute(text("ALTER TABLE life_characters ADD COLUMN last_study_at TIMESTAMPTZ"))
            await session.commit()

async def study_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    message=update.effective_message
    user=update.effective_user
    character=await get_actor(update)
    if not message or not user:return
    if not character:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    await ensure_study_column()
    now=datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        result=await session.execute(text("""
            SELECT last_study_at,school_xp,school_xp_required
            FROM life_characters WHERE id=:id FOR UPDATE
        """),{"id":character["id"]})
        row=result.mappings().first()
        last=row["last_study_at"]
        if last:
            if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
            elapsed=(now-last).total_seconds()
            if elapsed<STUDY_COOLDOWN_SECONDS:
                remain=int(STUDY_COOLDOWN_SECONDS-elapsed)
                await session.rollback()
                await message.reply_text(f"⏳ **ÉTUDE INDISPONIBLE**\n\nProchaine session dans **{remain//3600}h {(remain%3600)//60:02d}min**.",parse_mode="Markdown")
                return
        xp=int(row["school_xp"] or 0)+STUDY_XP_REWARD
        required=int(row["school_xp_required"] or 100)
        await session.execute(text("""
            UPDATE life_characters SET school_xp=:xp,school_xp_required=:required,last_study_at=:last_study_at,updated_at=NOW()
            WHERE id=:id
        """),{"xp":xp,"required":required,"last_study_at":now,"id":character["id"]})
        await session.commit()
    await message.reply_text(f"📚 **SESSION D'ÉTUDE TERMINÉE**\n\n⭐ XP scolaire : **+{STUDY_XP_REWARD}**\n📊 Progression : **{xp}/{required}**\n\n⏳ Prochaine session dans **5 heures**.",parse_mode="Markdown")

async def domain_command(update,context):
    message=update.effective_message
    if message: await message.reply_text("🎯 **CHOISIS TON DOMAINE**",reply_markup=build_domain_keyboard(),parse_mode="Markdown")

async def domain_callback(update,context):
    query=update.callback_query
    if not query:return
    await query.answer()
    domain=(query.data or "").split(":",1)[-1]
    character=await get_actor(update)
    if not character:
        await query.edit_message_text("❌ Personnage introuvable."); return
    try: await save_education_domain(character["id"],domain)
    except ValueError:
        await query.edit_message_text("❌ Domaine invalide."); return
    await query.edit_message_text(f"✅ **DOMAINE ENREGISTRÉ**\n\n{EDUCATION_DOMAINS[domain]}",parse_mode="Markdown")

def register_education_handlers(application:Application):
    application.add_handler(CommandHandler("school",school_command))
    application.add_handler(CommandHandler("study",study_command))
    application.add_handler(CommandHandler("domain",domain_command))
    application.add_handler(CallbackQueryHandler(domain_callback,pattern=r"^edu_domain:"))

__all__=["SCHOOL_LEVELS","EDUCATION_DOMAINS","STUDY_COOLDOWN_SECONDS","STUDY_XP_REWARD","school_command","study_command","domain_command","domain_callback","register_education_handlers"]
