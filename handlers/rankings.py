from __future__ import annotations
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select, desc, asc

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    League,
    LeagueSeasonClub,
    Season,
)



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "rankings.jpg"
# ==========================================================
# RANKINGS
# ==========================================================
#
# /rankings
#
# Shows:
#   🏆 domestic league standings
#   🌍 European ranking (when league_europe data exists)
#   🏆 Cup ranking is not treated as a league table.
#
# Domestic ranking order:
#   1. points
#   2. goal difference
#   3. goals for
#   4. wins
#
# Uses only fields present in models.py.
# ==========================================================


def rankings_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏆 LEAGUE",
                    callback_data="rankings:league",
                ),
                InlineKeyboardButton(
                    "🌍 EUROPE",
                    callback_data="rankings:europe",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="rankings:refresh",
                ),
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="rankings:close",
                ),
            ],
        ]
    )


async def _active_season(session):
    result = await session.execute(
        select(Season)
        .where(
            Season.is_active.is_(True)
        )
        .order_by(
            Season.number.desc()
        )
    )
    return result.scalars().first()


async def _club_names(session, club_ids):
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


async def _latest_membership_for_user_club(
    session,
    user_id: int,
    season_id: int,
):
    club_result = await session.execute(
        select(Club).where(
            Club.owner_id == user_id
        )
    )
    club = club_result.scalar_one_or_none()

    if club is None:
        return None, None

    membership_result = await session.execute(
        select(LeagueSeasonClub)
        .where(
            LeagueSeasonClub.club_id == club.id,
            LeagueSeasonClub.season_id == season_id,
        )
    )
    membership = (
        membership_result.scalar_one_or_none()
    )

    return club, membership


async def _league_table(
    session,
    season_id: int,
    league_id: int,
):
    result = await session.execute(
        select(LeagueSeasonClub)
        .where(
            LeagueSeasonClub.season_id == season_id,
            LeagueSeasonClub.league_id == league_id,
        )
        .order_by(
            desc(LeagueSeasonClub.points),
            desc(
                LeagueSeasonClub.goals_for
                - LeagueSeasonClub.goals_against
            ),
            desc(LeagueSeasonClub.goals_for),
            desc(LeagueSeasonClub.wins),
            asc(LeagueSeasonClub.club_id),
        )
    )

    rows = list(result.scalars().all())

    names = await _club_names(
        session,
        [row.club_id for row in rows],
    )

    return rows, names


def _render_league_rows(rows, names):
    if not rows:
        return "📭 No league standings available yet."

    lines = []

    for position, row in enumerate(
        rows,
        start=1,
    ):
        name = names.get(
            row.club_id,
            f"Club #{row.club_id}",
        )

        gd = (
            row.goals_for
            - row.goals_against
        )

        lines.append(
            (
                f"{position}. {name}\n"
                f"   🏆 {row.points} pts • "
                f"🎮 {row.played} • "
                f"✅ {row.wins} • "
                f"🤝 {row.draws} • "
                f"❌ {row.losses}\n"
                f"   ⚽ {row.goals_for} "
                f"🥅 {row.goals_against} "
                f"📈 GD {gd}"
            )
        )

    return "\n".join(lines)


async def _render_rankings(
    query,
    user_id: int,
    category: str,
):
    async with AsyncSessionLocal() as session:
        season = await _active_season(session)

        if season is None:
            await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='📊 𝐑𝐀𝐍𝐊𝐈𝐍𝐆𝐒\n━━━━━━━━━━━━━━━━━━━━\n❌ No active season.',
    reply_markup=rankings_keyboard(),
)
            return

        club, membership = (
            await _latest_membership_for_user_club(
                session,
                user_id,
                season.id,
            )
        )

        if category == "league":
            if club is None or membership is None:
                text = (
                    "🏆 𝐋𝐄𝐀𝐆𝐔𝐄 𝐑𝐀𝐍𝐊𝐈𝐍𝐆\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ Your club is not registered in "
                    "a league for this season."
                )
            else:
                result = await session.execute(
                    select(League).where(
                        League.id == membership.league_id
                    )
                )
                league = result.scalar_one_or_none()

                rows, names = await _league_table(
                    session,
                    season.id,
                    membership.league_id,
                )

                text = (
                    "🏆 𝐋𝐄𝐀𝐆𝐔𝐄 𝐑𝐀𝐍𝐊𝐈𝐍𝐆\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏆 {league.name if league else 'League'}\n"
                    f"📅 {season.name}\n\n"
                    f"{_render_league_rows(rows, names)}"
                )

        elif category == "europe":
            # European club rankings are represented through
            # LeagueSeasonClub only when a domestic league is
            # available. CompetitionParticipant in the current
            # schema has no points/ranking fields, so we do not
            # fabricate a European table here.
            text = (
                "🌍 𝐄𝐔𝐑𝐎𝐏𝐄 𝐑𝐀𝐍𝐊𝐈𝐍𝐆\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "European ranking will be shown once the "
                "European league-phase standings are stored.\n\n"
                "📌 Current model does not contain European "
                "points/goal fields in CompetitionParticipant."
            )
        else:
            return

    await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption=text,
    reply_markup=rankings_keyboard(),
)


async def rankings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        (
            "📊 𝐑𝐀𝐍𝐊𝐈𝐍𝐆𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Choose the ranking you want to see:"
        ),
        reply_markup=rankings_keyboard(),
    )


async def rankings_callback(
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
    caption='📊 Rankings closed.',
)
        return

    if action in {
        "league",
        "europe",
    }:
        await _render_rankings(
            query,
            query.from_user.id,
            action,
        )
        return

    if action == "refresh":
        await query.message.reply_photo(
    photo=open(IMAGE_FILE, "rb"),
    caption='📊 𝐑𝐀𝐍𝐊𝐈𝐍𝐆𝐒\n━━━━━━━━━━━━━━━━━━━━\nChoose the ranking you want to see:',
    reply_markup=rankings_keyboard(),
)


rankings_handler = CommandHandler(
    "rankings",
    rankings,
)

rankings_callback_handler = CallbackQueryHandler(
    rankings_callback,
    pattern=r"^rankings:(league|europe|refresh|close)$",
)