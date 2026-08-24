from __future__ import annotations
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Fixture, Match, Club



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "calendar.jpg"
# ==========================================================
# CALENDAR
# ==========================================================
#
# /calendar
#
# Views:
#   ⚽ League
#   🌍 Europe
#   🏆 Cup
#   📅 All
#
# Uses the real Fixture/Match/Club fields from models.py.
# ==========================================================


def calendar_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ LEAGUE",
                    callback_data="calendar:league",
                ),
                InlineKeyboardButton(
                    "🌍 EUROPE",
                    callback_data="calendar:europe",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏆 CUP",
                    callback_data="calendar:cup",
                ),
                InlineKeyboardButton(
                    "📅 ALL",
                    callback_data="calendar:all",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="calendar:refresh",
                ),
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="calendar:close",
                ),
            ],
        ]
    )


def _normalize_type(value: str) -> str | None:
    value = value.lower()

    if value == "league":
        return "league"

    if value in {
        "europe",
        "league_europe",
    }:
        return "league_europe"

    if value == "cup":
        return "cup"

    if value == "all":
        return None

    return None


async def _get_calendar(
    session,
    competition_type: str | None,
):
    query = (
        select(
            Fixture,
            Match,
        )
        .join(
            Match,
            Match.fixture_id == Fixture.id,
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


async def _get_club_names(
    session,
    fixtures,
):
    club_ids = {
        club_id
        for fixture, match in fixtures
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


def _competition_label(
    competition_type: str,
) -> str:
    labels = {
        "league": "⚽ LEAGUE",
        "league_europe": "🌍 EUROPE",
        "cup": "🏆 CUP",
    }

    return labels.get(
        competition_type,
        competition_type.upper(),
    )


def _status_text(
    fixture,
    match,
) -> str:
    status = str(
        match.status
    ).lower()

    if status in {
        "finished",
        "completed",
    }:
        return (
            f"📊 {match.home_score}"
            f" - "
            f"{match.away_score}"
        )

    if status in {
        "live",
        "in_progress",
        "playing",
    }:
        return (
            f"🔴 LIVE "
            f"{match.home_score}"
            f" - "
            f"{match.away_score}"
            f" • {match.minute}'"
        )

    return f"⏳ {status}"


async def _render_calendar(
    query,
    competition_type: str,
):
    normalized = _normalize_type(
        competition_type
    )

    async with AsyncSessionLocal() as session:
        rows = await _get_calendar(
            session,
            normalized,
        )

        names = await _get_club_names(
            session,
            rows,
        )

    if not rows:
        title = (
            "📅 ALL"
            if normalized is None
            else _competition_label(normalized)
        )

        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=f'📅 𝐂𝐀𝐋𝐄𝐍𝐃𝐀𝐑\n━━━━━━━━━━━━━━━━━━━━\n{title}\n\n📭 No scheduled matches yet.',
    reply_markup=calendar_keyboard(),
)
        return

    title = (
        "📅 ALL"
        if normalized is None
        else _competition_label(normalized)
    )

    lines = [
        "📅 𝐂𝐀𝐋𝐄𝐍𝐃𝐀𝐑",
        "━━━━━━━━━━━━━━━━━━━━",
        title,
        "",
    ]

    current_date = None

    for fixture, match in rows:
        date = fixture.scheduled_at.date()

        if date != current_date:
            current_date = date

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
                f"{fixture.scheduled_at.strftime('%H:%M')} "
                f"• {_competition_label(fixture.competition_type)}"
                f"{round_text}\n"
                f"⚽ {home} vs {away}\n"
                f"{_status_text(fixture, match)}"
            )
        )

    lines.extend(
        [
            "",
            "📆 Competition calendar:",
            "⚽ League → Friday / Saturday / Sunday",
            "🌍 Europe → Monday / Tuesday",
            "🏆 Cup → Wednesday / Thursday",
        ]
    )

    text = "\n".join(lines)

    # Telegram message safety.
    if len(text) > 3900:
        text = (
            text[:3850]
            + "\n\n… Use a competition filter "
            "to see fewer matches."
        )

    await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=text,
    reply_markup=calendar_keyboard(),
)


async def calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        (
            "📅 𝐂𝐀𝐋𝐄𝐍𝐃𝐀𝐑\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Choose the competition:"
        ),
        reply_markup=calendar_keyboard(),
    )


async def calendar_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None:
        return

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""

    if not data.startswith("calendar:"):
        return

    action = data.split(":", 1)[1]

    if action == "close":
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='📅 Calendar closed.',
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
        await _render_calendar(
            query,
            action,
        )


calendar_handler = CommandHandler(
    "calendar",
    calendar,
)

calendar_callback_handler = CallbackQueryHandler(
    calendar_callback,
    pattern=r"^calendar:(league|europe|cup|all|refresh|close)$",
)