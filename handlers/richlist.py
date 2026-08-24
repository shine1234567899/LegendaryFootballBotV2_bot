from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import text

from database.database import AsyncSessionLocal

def richlist_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪙 COINS", callback_data="richlist:coins"),
            InlineKeyboardButton("💎 GEMS", callback_data="richlist:gems"),
        ],
        [
            InlineKeyboardButton("📊 MY RANK", callback_data="richlist:myrank"),
        ],
    ])

async def _render_top(query, category: str):
    column = "coins" if category == "coins" else "gems"
    icon = "🪙" if category == "coins" else "💎"
    label = "COINS" if category == "coins" else "GEMS"

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                text(f"""
                    SELECT id, username, first_name, {column}
                    FROM users
                    ORDER BY {column} DESC, id ASC
                    LIMIT 10
                """)
            )
        ).all()

    lines = [
        f"👑 𝐑𝐈𝐂𝐇𝐋𝐈𝐒𝐓 — {label}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if not rows:
        lines.append("No users found.")
    else:
        for pos, row in enumerate(rows, 1):
            uid, username, first_name, amount = row
            name = f"@{username}" if username else (first_name or f"User {uid}")
            lines.append(f"{pos}. {name} — {icon} {int(amount or 0):,}")

    lines.append("")
    lines.append("Tap MY RANK to see your position.")

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=richlist_keyboard(),
    )

async def _render_myrank(query):
    uid = query.from_user.id

    async with AsyncSessionLocal() as session:
        # Compute both ranks independently; no schema changes.
        coins_rank = await session.scalar(text("""
            SELECT 1 + COUNT(*)
            FROM users other
            JOIN users me ON me.id = :uid
            WHERE other.coins > me.coins
        """), {"uid": uid})

        gems_rank = await session.scalar(text("""
            SELECT 1 + COUNT(*)
            FROM users other
            JOIN users me ON me.id = :uid
            WHERE other.gems > me.gems
        """), {"uid": uid})

        me = (
            await session.execute(
                text("""
                    SELECT coins, gems FROM users WHERE id = :uid
                """),
                {"uid": uid},
            )
        ).first()

    if me is None:
        await query.edit_message_text(
            "❌ Your account was not found.",
            reply_markup=richlist_keyboard(),
        )
        return

    coins, gems = me
    await query.edit_message_text(
        "👑 𝐌𝐘 𝐑𝐈𝐂𝐇𝐋𝐈𝐒𝐓 𝐑𝐀𝐍𝐊\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 Coins: {int(coins or 0):,}\n"
        f"🏆 Coins rank: #{int(coins_rank or 1)}\n\n"
        f"💎 Gems: {int(gems or 0):,}\n"
        f"🏆 Gems rank: #{int(gems_rank or 1)}",
        reply_markup=richlist_keyboard(),
    )

async def richlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return

    await message.reply_text(
        "👑 𝐑𝐈𝐂𝐇𝐋𝐈𝐒𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose a ranking:",
        reply_markup=richlist_keyboard(),
    )

async def richlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or not query.data:
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = query.data.split(":", 1)[1]
    if action in {"coins", "gems"}:
        await _render_top(query, action)
    elif action == "myrank":
        await _render_myrank(query)

richlist_handler = CommandHandler("richlist", richlist)
richlist_callback_handler = CallbackQueryHandler(
    richlist_callback,
    pattern=r"^richlist:(coins|gems|myrank)$",
)