"""
MANUWORLD V3 — SERVICES TRANSVERSAUX

Nouvelles commandes :
/daily       récompense quotidienne + streak
/achievements réalisations
/notifications notifications non lues
/mwlhelp     aide MANUWORLD
"""
from __future__ import annotations

from datetime import timedelta
from sqlalchemy import text
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

from life_world.database import AsyncSessionLocal, get_life_character
from life_world.core import ensure_v3_schema, money, utcnow


async def get_actor(update: Update):
    user = update.effective_user
    if not user:
        return None
    row = await get_life_character(user.id)
    return dict(row) if row else None


async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    actor = await get_actor(update)
    if not msg:
        return
    if not actor:
        await msg.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return

    await ensure_v3_schema()
    now = utcnow()

    async with AsyncSessionLocal() as session:
        row = (await session.execute(text("""
            SELECT last_claim_at, streak FROM mwl_daily_claims
            WHERE character_id=:id FOR UPDATE
        """), {"id": int(actor["id"])})).mappings().first()

        if row and row["last_claim_at"]:
            last = row["last_claim_at"]
            if last.tzinfo is None:
                last = last.replace(tzinfo=now.tzinfo)
            elapsed = now - last
            if elapsed < timedelta(hours=20):
                remaining = timedelta(hours=20) - elapsed
                await session.rollback()
                h = int(remaining.total_seconds() // 3600)
                m = int((remaining.total_seconds() % 3600) // 60)
                await msg.reply_text(f"⏳ Prochaine récompense dans **{h}h {m:02d}min**.", parse_mode="Markdown")
                return

            streak = int(row["streak"] or 0) + (1 if elapsed <= timedelta(hours=48) else 1)
            await session.execute(text("""
                UPDATE mwl_daily_claims SET last_claim_at=:now, streak=:streak
                WHERE character_id=:id
            """), {"now": now, "streak": streak, "id": int(actor["id"])})
        else:
            streak = 1
            await session.execute(text("""
                INSERT INTO mwl_daily_claims(character_id,last_claim_at,streak)
                VALUES(:id,:now,1)
                ON CONFLICT(character_id) DO UPDATE SET last_claim_at=:now, streak=1
            """), {"id": int(actor["id"]), "now": now})

        reward = min(500 + (streak - 1) * 100, 3000)
        result = await session.execute(text("""
            SELECT balance FROM life_characters WHERE id=:id FOR UPDATE
        """), {"id": int(actor["id"])})
        balance = int(result.scalar_one() or 0)
        new_balance = balance + reward
        await session.execute(text("""
            UPDATE life_characters SET balance=:balance, updated_at=NOW()
            WHERE id=:id
        """), {"balance": new_balance, "id": int(actor["id"])})
        await session.execute(text("""
            INSERT INTO life_transactions
                (character_id,transaction_type,amount,balance_after,description,reference)
            VALUES(:id,'daily',:reward,:balance,'Récompense quotidienne',:reference)
        """), {
            "id": int(actor["id"]), "reward": reward,
            "balance": new_balance, "reference": f"daily:{streak}",
        })
        await session.commit()

    await msg.reply_text(
        "🎁 **RÉCOMPENSE QUOTIDIENNE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 +{money(reward)}\n"
        f"🔥 Série : **{streak} jour(s)**\n"
        f"💵 Solde : **{money(new_balance)}**",
        parse_mode="Markdown",
    )


async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    actor = await get_actor(update)
    if not msg:
        return
    if not actor:
        await msg.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return
    await ensure_v3_schema()
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text("""
            SELECT a.title,a.description,a.reward,ca.unlocked_at
            FROM mwl_achievements a
            LEFT JOIN mwl_character_achievements ca
              ON ca.achievement_id=a.id AND ca.character_id=:id
            ORDER BY a.id
        """), {"id": int(actor["id"])})).mappings().all()

    lines=["🏆 **RÉALISATIONS MANUWORLD**","━━━━━━━━━━━━━━━━━━━━",""]
    for r in rows:
        mark="✅" if r["unlocked_at"] else "🔒"
        lines.append(f"{mark} **{r['title']}** — {r['description']} (+{money(r['reward'])})")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    actor = await get_actor(update)
    if not msg:
        return
    if not actor:
        await msg.reply_text("❌ Personnage introuvable.")
        return
    await ensure_v3_schema()
    async with AsyncSessionLocal() as session:
        rows=(await session.execute(text("""
            SELECT id,title,body,created_at
            FROM mwl_notifications
            WHERE character_id=:id AND read_at IS NULL
            ORDER BY created_at DESC LIMIT 15
        """),{"id":int(actor["id"])})).mappings().all()
        await session.execute(text("""
            UPDATE mwl_notifications SET read_at=NOW()
            WHERE character_id=:id AND read_at IS NULL
        """),{"id":int(actor["id"])})
        await session.commit()
    if not rows:
        await msg.reply_text("🔔 Aucune nouvelle notification.")
        return
    text_out="🔔 **NOTIFICATIONS**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text_out += "\n\n".join(f"**{r['title']}**\n{r['body']}" for r in rows)
    await msg.reply_text(text_out, parse_mode="Markdown")


async def mwlhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg=update.effective_message
    if not msg:return
    await msg.reply_text(
        "🌍 **MANUWORLD V3**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 /life — créer/voir sa vie\n"
        "📊 /lifestyle — statistiques\n"
        "🎁 /daily — récompense quotidienne\n"
        "🏆 /achievements — réalisations\n"
        "🔔 /notifications — notifications\n"
        "🎓 /school /study /exam — études\n"
        "💼 /jobs /work — emploi\n"
        "🏢 /business — entreprises\n"
        "🏥 /hospital /health — santé\n"
        "🏠 /housing — logement\n"
        "🏛️ /politics — vie politique\n"
        "👥 /friends /family — relations\n"
        "🎒 /inventory — inventaire\n"
        "💳 /bank — banque\n"
        "💰 /wealth — patrimoine\n\n"
        "Les opérations sensibles utilisent toujours le personnage "
        "MANUWORLD lié à ton Telegram."
    )


def register_mwl_core_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    application.add_handler(CommandHandler("mwlhelp", mwlhelp_command))
