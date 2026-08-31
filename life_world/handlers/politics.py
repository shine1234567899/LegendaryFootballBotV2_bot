"""
MANUWORLD V3 — POLITIQUE

/parties
/party_create <nom> [slogan]
/election
/run_for <programme>
/vote <candidate_telegram_id>  (deprecated targeting is not used)
 /meeting_create <titre> <YYYY-MM-DDTHH:MM> [lieu] [description]

Les votes et candidatures utilisent le personnage associé au compte Telegram.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import text
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from life_world.database import get_life_character, get_life_character_by_username, AsyncSessionLocal
from life_world.core import ensure_v3_schema


async def actor(update):
    u=update.effective_user
    if not u:return None
    r=await get_life_character(u.id)
    return dict(r) if r else None


async def politics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg=update.effective_message
    a=await actor(update)
    if not msg:return
    if not a:
        await msg.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    await ensure_v3_schema()
    async with AsyncSessionLocal() as s:
        e=(await s.execute(text("""
            SELECT id,title,status,starts_at,ends_at FROM mwl_elections
            WHERE status='open' ORDER BY id DESC LIMIT 1
        """))).mappings().first()
        parties=(await s.execute(text("""
            SELECT name,slogan FROM mwl_political_parties ORDER BY name LIMIT 10
        """))).mappings().all()
    out=["🏛️ **MANUWORLD — POLITIQUE**","━━━━━━━━━━━━━━━━━━━━",""]
    if e:
        out += [f"🗳️ Élection : **{e['title']}**",f"📌 Statut : {e['status']}",""]
    else:
        out += ["🗳️ Aucune élection ouverte.",""]
    out.append("🎗️ **Partis**")
    out += [f"• {p['name']} — {p['slogan']}" for p in parties] or ["• Aucun parti."]
    out += ["","Commandes :","/parties","/party_create <nom> [slogan]","/run_for <programme>","/election","/meeting_create <titre> <YYYY-MM-DDTHH:MM> [lieu]"]
    await msg.reply_text("\n".join(out),parse_mode="Markdown")


async def parties_command(update,context):
    msg=update.effective_message
    if not msg:return
    await ensure_v3_schema()
    async with AsyncSessionLocal() as s:
        rows=(await s.execute(text("""
            SELECT p.name,p.slogan,COALESCE(c.cnt,0) candidates
            FROM mwl_political_parties p
            LEFT JOIN (
                SELECT party_id,COUNT(*) cnt FROM mwl_candidates GROUP BY party_id
            ) c ON c.party_id=p.id
            ORDER BY p.name
        """))).mappings().all()
    if not rows:
        await msg.reply_text("🎗️ Aucun parti politique n'existe encore.")
        return
    await msg.reply_text("🎗️ **PARTIS**\n\n"+"\n".join(
        f"• **{r['name']}** — {r['slogan']} ({r['candidates']} candidat(s))" for r in rows
    ),parse_mode="Markdown")


async def party_create_command(update,context):
    msg=update.effective_message;a=await actor(update)
    if not msg:return
    if not a:return await msg.reply_text("❌ Personnage introuvable.")
    if not context.args:return await msg.reply_text("Utilisation : `/party_create <nom> [slogan]`",parse_mode="Markdown")
    name=context.args[0].strip()
    slogan=" ".join(context.args[1:])[:180]
    await ensure_v3_schema()
    async with AsyncSessionLocal() as s:
        try:
            await s.execute(text("""
                INSERT INTO mwl_political_parties(name,slogan,leader_character_id)
                VALUES(:name,:slogan,:leader)
            """),{"name":name,"slogan":slogan,"leader":int(a["id"])})
            await s.commit()
        except Exception:
            await s.rollback()
            await msg.reply_text("❌ Ce parti existe déjà ou les données sont invalides.")
            return
    await msg.reply_text(f"🎗️ Parti **{name}** créé.\n👤 Leader : {a.get('first_name') or 'Joueur'}",parse_mode="Markdown")


async def election_command(update,context):
    msg=update.effective_message
    if not msg:return
    await ensure_v3_schema()
    async with AsyncSessionLocal() as s:
        rows=(await s.execute(text("""
            SELECT e.id,e.title,e.status,e.starts_at,e.ends_at,
                   COUNT(c.character_id) candidates
            FROM mwl_elections e
            LEFT JOIN mwl_candidates c ON c.election_id=e.id
            GROUP BY e.id ORDER BY e.id DESC LIMIT 5
        """))).mappings().all()
    if not rows:
        await msg.reply_text("🗳️ Aucune élection n'a encore été créée.")
        return
    await msg.reply_text(
        "🗳️ **ÉLECTIONS**\n\n"+
        "\n".join(f"#{r['id']} — **{r['title']}** — {r['status']} — {r['candidates']} candidat(s)" for r in rows),
        parse_mode="Markdown"
    )


async def run_for_command(update,context):
    msg=update.effective_message;a=await actor(update)
    if not msg:return
    if not a:return await msg.reply_text("❌ Personnage introuvable.")
    program=" ".join(context.args).strip()[:2000]
    if not program:return await msg.reply_text("Utilisation : `/run_for <ton programme>`",parse_mode="Markdown")
    await ensure_v3_schema()
    async with AsyncSessionLocal() as s:
        election=(await s.execute(text("""
            SELECT id FROM mwl_elections WHERE status='open' ORDER BY id DESC LIMIT 1
        """))).scalar()
        if election is None:
            await msg.reply_text("❌ Aucune élection ouverte.")
            return
        await s.execute(text("""
            INSERT INTO mwl_candidates(election_id,character_id,program)
            VALUES(:election,:character,:program)
            ON CONFLICT(election_id,character_id)
            DO UPDATE SET program=EXCLUDED.program
        """),{"election":int(election),"character":int(a["id"]),"program":program})
        await s.commit()
    await msg.reply_text("🗳️ **Candidature enregistrée !**\nTon programme est maintenant visible par les électeurs.",parse_mode="Markdown")


async def meeting_create_command(update,context):
    msg=update.effective_message;a=await actor(update)
    if not msg:return
    if not a:return await msg.reply_text("❌ Personnage introuvable.")
    if len(context.args)<2:
        await msg.reply_text("Utilisation : `/meeting_create <titre> <YYYY-MM-DDTHH:MM> [lieu] [description]`",parse_mode="Markdown");return
    try:
        starts=datetime.fromisoformat(context.args[1])
        if starts.tzinfo is None: starts=starts.replace(tzinfo=timezone.utc)
    except ValueError:
        await msg.reply_text("❌ Date invalide. Exemple : `2026-09-05T18:00`",parse_mode="Markdown");return
    location=context.args[2] if len(context.args)>2 else "Hôtel de ville"
    description=" ".join(context.args[3:])[:1000]
    async with AsyncSessionLocal() as s:
        await s.execute(text("""
            INSERT INTO mwl_meetings(organizer_character_id,title,description,location,starts_at)
            VALUES(:owner,:title,:description,:location,:starts)
        """),{"owner":int(a["id"]),"title":context.args[0][:160],"description":description,"location":location[:120],"starts":starts})
        await s.commit()
    await msg.reply_text(f"📣 Meeting créé : **{context.args[0]}**\n📍 {location}\n🕐 {starts.isoformat()}",parse_mode="Markdown")


async def politics_callback(update,context):
    q=update.callback_query
    if q: await q.answer("Cette action n'est plus disponible.")


def register_politics_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("politics", politics_command))
    application.add_handler(CommandHandler("parties", parties_command))
    application.add_handler(CommandHandler("party_create", party_create_command))
    application.add_handler(CommandHandler("election", election_command))
    application.add_handler(CommandHandler("run_for", run_for_command))
    application.add_handler(CommandHandler("meeting_create", meeting_create_command))
