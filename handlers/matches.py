from __future__ import annotations
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Fixture, Match, Club



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "matches.jpg"
# ==========================================================
# MATCHES
# ==========================================================
#
# /matches
#
# Shows the current manager's club matches.
#
# Filters:
#   ⚽ LEAGUE
#   🌍 EUROPE
#   🏆 CUP
#   📅 ALL
#
# Uses the real Fixture / Match / Club model fields.
# ==========================================================


def matches_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ LEAGUE",
                    callback_data="matches:league",
                ),
                InlineKeyboardButton(
                    "🌍 EUROPE",
                    callback_data="matches:europe",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏆 CUP",
                    callback_data="matches:cup",
                ),
                InlineKeyboardButton(
                    "📅 ALL",
                    callback_data="matches:all",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="matches:refresh",
                ),
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="matches:close",
                ),
            ],
        ]
    )


def _normalize_type(value: str) -> str | None:
    value = value.lower()

    if value == "league":
        return "league"

    if value in {"europe", "league_europe"}:
        return "league_europe"

    if value == "cup":
        return "cup"

    if value == "all":
        return None

    return None


def _competition_label(value: str) -> str:
    labels = {
        "league": "⚽ LEAGUE",
        "league_europe": "🌍 EUROPE",
        "cup": "🏆 CUP",
    }
    return labels.get(value, value.upper())


async def _get_my_club(
    session,
    user_id: int,
):
    result = await session.execute(
        select(Club).where(
            Club.owner_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _get_rows(
    session,
    club_id: int,
    competition_type: str | None,
):
    query = (
        select(Fixture, Match)
        .join(
            Match,
            Match.fixture_id == Fixture.id,
        )
        .where(
            (
                (Fixture.home_club_id == club_id)
                | (Fixture.away_club_id == club_id)
            )
        )
    )

    if competition_type is not None:
        query = query.where(
            Fixture.competition_type
            == competition_type
        )

    query = query.order_by(
        Fixture.scheduled_at.asc(),
        Fixture.id.asc(),
    )

    result = await session.execute(query)
    return list(result.all())


async def _club_names(
    session,
    rows,
):
    club_ids = {
        club_id
        for fixture, match in rows
        for club_id in (
            fixture.home_club_id,
            fixture.away_club_id,
        )
    }

    if not club_ids:
        return {}

    result = await session.execute(
        select(Club).where(
            Club.id.in_(club_ids)
        )
    )

    return {
        club.id: club.name
        for club in result.scalars().all()
    }


def _match_status(
    match: Match,
):
    status = str(match.status).lower()

    if status in {"finished", "completed"}:
        return (
            f"📊 {match.home_score}"
            f" - {match.away_score}"
        )

    if status in {
        "live",
        "in_progress",
        "playing",
    }:
        return (
            f"🔴 LIVE "
            f"{match.home_score}"
            f" - {match.away_score}"
            f" • {match.minute}'"
        )

    return f"⏳ {status}"


async def _render_matches(
    query,
    user_id: int,
    category: str,
):
    competition_type = _normalize_type(category)

    async with AsyncSessionLocal() as session:
        club = await _get_my_club(
            session,
            user_id,
        )

        if club is None:
            await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='⚽ 𝐌𝐀𝐓𝐂𝐇𝐄𝐒\n━━━━━━━━━━━━━━━━━━━━\n❌ Create your club first.',
    reply_markup=matches_keyboard(),
)
            return

        rows = await _get_rows(
            session,
            club.id,
            competition_type,
        )

        names = await _club_names(
            session,
            rows,
        )

    title = (
        "📅 ALL"
        if competition_type is None
        else _competition_label(
            competition_type
        )
    )

    if not rows:
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=f'⚽ 𝐌𝐀𝐓𝐂𝐇𝐄𝐒\n━━━━━━━━━━━━━━━━━━━━\n{title}\n\n📭 No matches found.',
    reply_markup=matches_keyboard(),
)
        return

    lines = [
        "⚽ 𝐌𝐘 𝐌𝐀𝐓𝐂𝐇𝐄𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🏷️ {club.name}",
        f"{title}",
        "",
    ]

    current_date = None

    for fixture, match in rows:
        fixture_date = fixture.scheduled_at.date()

        if fixture_date != current_date:
            current_date = fixture_date
            lines.extend(
                [
                    "",
                    f"📆 {fixture.scheduled_at.strftime('%A %d/%m/%Y')}",
                    "────────────────────",
                ]
            )

        home = names.get(
            fixture.home_club_id,
            f"Club #{fixture.home_club_id}",
        )
        away = names.get(
            fixture.away_club_id,
            f"Club #{fixture.away_club_id}",
        )

        round_text = (
            f" • Round {fixture.round_number}"
            if fixture.round_number is not None
            else ""
        )

        lines.append(
            (
                f"⏰ {fixture.scheduled_at.strftime('%H:%M')}"
                f" • {_competition_label(fixture.competition_type)}"
                f"{round_text}\n"
                f"⚽ {home} vs {away}\n"
                f"{_match_status(match)}"
            )
        )

    lines.append("")
    lines.append(
        "📆 League: Friday / Saturday / Sunday"
    )
    lines.append(
        "🌍 Europe: Monday / Tuesday"
    )
    lines.append(
        "🏆 Cup: Wednesday / Thursday"
    )

    text = "\n".join(lines)

    if len(text) > 3900:
        text = (
            text[:3850]
            + "\n\n… Use a competition filter "
            "to narrow the list."
        )

    await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=text,
    reply_markup=matches_keyboard(),
)


async def matches(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        (
            "⚽ 𝐌𝐘 𝐌𝐀𝐓𝐂𝐇𝐄𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Choose the competition:"
        ),
        reply_markup=matches_keyboard(),
    )


async def matches_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or not query.data:
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = str(
        query.data
    ).split(":", 1)[1]

    if action == "close":
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='⚽ Matches closed.',
)
        return

    if action == "refresh":
        action = "all"

    if action in {
        "league",
        "europe",
        "cup",
        "all",
    }:
        await _render_matches(
            query,
            query.from_user.id,
            action,
        )


matches_handler = CommandHandler(
    "matches",
    matches,
)

matches_callback_handler = CallbackQueryHandler(
    matches_callback,
    pattern=r"^matches:(league|europe|cup|all|refresh|close)$",
)