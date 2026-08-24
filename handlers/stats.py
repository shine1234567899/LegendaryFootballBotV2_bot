from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select, desc

from database.database import AsyncSessionLocal
from database.models import Match, Fixture, Club



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "stats.jpg"
# ==========================================================
# STATS
# ==========================================================

async def _get_my_club(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Club).where(Club.owner_id == user_id)
        )
        return result.scalar_one_or_none()


def _stats_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🤝 FRIENDLY",
                    callback_data="stats:friendly",
                ),
                InlineKeyboardButton(
                    "🏆 LEAGUE",
                    callback_data="stats:league",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="stats:close",
                ),
            ],
        ]
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    club = await _get_my_club(user.id)

    if club is None:
        await message.reply_text(
            "❌ Create your club first."
        )
        return

    await message.reply_text(
        (
            "📊 𝐂𝐋𝐔𝐁 𝐒𝐓𝐀𝐓𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚽ {club.name}\n\n"
            "Choose the statistics you want to see:"
        ),
        reply_markup=_stats_keyboard(),
    )


async def stats_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    # ACK immediately so the button never stays loading.
    try:
        await query.answer()
    except Exception:
        pass

    action = str(query.data).split(":", 1)[1]

    if action == "close":
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='📊 Stats closed.',
)
        return

    user = query.from_user
    club = await _get_my_club(user.id)

    if club is None:
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='❌ Club not found.',
)
        return

    # Friendly and League use competition_type from fixtures.
    competition_type = {
        "friendly": "friendly",
        "league": "league",
    }.get(action)

    if competition_type is None:
        return

    async with AsyncSessionLocal() as session:
        # A fixture belongs to two clubs. Fetch matches involving this club.
        result = await session.execute(
            select(Match, Fixture)
            .join(Fixture, Match.fixture_id == Fixture.id)
            .where(
                (
                    (Fixture.home_club_id == club.id)
                    | (Fixture.away_club_id == club.id)
                ),
                Fixture.competition_type == competition_type,
                Match.status.in_(
                    [
                        "finished",
                        "completed",
                        "ended",
                    ]
                ),
            )
            .order_by(desc(Match.id))
        )

        rows = result.all()

    if not rows:
        title = (
            "🤝 FRIENDLY STATS"
            if action == "friendly"
            else "🏆 LEAGUE STATS"
        )

        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=f'📊 𝐂𝐋𝐔𝐁 𝐒𝐓𝐀𝐓𝐒 — {title}\n━━━━━━━━━━━━━━━━━━━━\nNo finished matches yet.',
    reply_markup=_stats_keyboard(),
)
        return

    played = len(rows)
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0

    for match, fixture in rows:
        if fixture.home_club_id == club.id:
            gf = int(match.home_score or 0)
            ga = int(match.away_score or 0)
        else:
            gf = int(match.away_score or 0)
            ga = int(match.home_score or 0)

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    points = wins * 3 + draws

    title = (
        "🤝 FRIENDLY"
        if action == "friendly"
        else "🏆 LEAGUE"
    )

    await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=f'📊 𝐂𝐋𝐔𝐁 𝐒𝐓𝐀𝐓𝐒 — {title}\n━━━━━━━━━━━━━━━━━━━━\n⚽ {club.name}\n\n🎮 Played : {played}\n✅ Wins : {wins}\n🤝 Draws : {draws}\n❌ Losses : {losses}\n⚽ Goals : {goals_for}\n🥅 Conceded : {goals_against}\n📈 Goal difference : {goals_for - goals_against}\n🏆 Points : {points}',
    reply_markup=_stats_keyboard(),
)


stats_handler = CommandHandler(
    "stats",
    stats,
)

stats_callback_handler = CallbackQueryHandler(
    stats_callback,
    pattern=r"^stats:(friendly|league|close)$",
)