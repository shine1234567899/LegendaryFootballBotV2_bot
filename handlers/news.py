from __future__ import annotations
from pathlib import Path

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, or_

from database.database import AsyncSessionLocal
from database.models import (
    Club,
    ClubPlayer,
    Player,
    Fixture,
    Match,
    TransferListing,
    League,
    LeagueSeasonClub,
)



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "news.jpg"
# ==========================================================
# NEWS
# ==========================================================
#
# /news
#
# The news feed combines important events from the database:
#
#   🔄 Transfers
#   🏆 League activity
#   🏆 Cup matches
#   🌍 European matches
#   🔥 Winning streaks
#   ⚔️ Big-match announcements
#
# Big-match rule:
#   both clubs must have an average current-player overall
#   of at least 85.
#
# The feed is generated from existing database data.
# It does not invent results.
# ==========================================================


BIG_MATCH_AVERAGE = 85
NEWS_LIMIT = 20


async def _club_averages(
    session,
    club_ids: list[int],
) -> dict[int, float]:
    if not club_ids:
        return {}

    result = await session.execute(
        select(
            ClubPlayer.club_id,
            Player.overall,
        )
        .join(
            Player,
            Player.id == ClubPlayer.player_id,
        )
        .where(
            ClubPlayer.club_id.in_(club_ids),
            ClubPlayer.is_current.is_(True),
        )
    )

    values: dict[int, list[int]] = {}

    for club_id, overall in result.all():
        values.setdefault(
            club_id,
            [],
        ).append(int(overall))

    return {
        club_id: (
            sum(overalls) / len(overalls)
            if overalls
            else 0.0
        )
        for club_id, overalls in values.items()
    }


async def _club_names(
    session,
    club_ids: list[int],
) -> dict[int, str]:
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


async def _transfer_news(
    session,
):
    """
    Recent transfer listings/sales information available in
    the current schema.

    The schema contains listings and sold_at, but does not
    contain a transfer-history table, so this section reports
    information that can actually be derived from listings.
    """
    result = await session.execute(
        select(
            TransferListing,
            Player,
        )
        .join(
            Player,
            Player.id == TransferListing.player_id,
        )
        .order_by(
            TransferListing.listed_at.desc()
        )
        .limit(NEWS_LIMIT)
    )

    news = []

    for listing, player in result.all():
        if listing.status == "sold":
            news.append(
                (
                    listing.listed_at,
                    (
                        f"🔄 Transfer : {player.name} "
                        f"— {listing.price:,} "
                        f"{listing.currency}"
                    ),
                )
            )
        else:
            news.append(
                (
                    listing.listed_at,
                    (
                        f"💰 Transfer market : "
                        f"{player.name} listed for "
                        f"{listing.price:,} "
                        f"{listing.currency}"
                    ),
                )
            )

    return news


async def _fixture_news(
    session,
    competition_type: str,
    label: str,
):
    result = await session.execute(
        select(
            Fixture,
            Match,
        )
        .join(
            Match,
            Match.fixture_id == Fixture.id,
        )
        .where(
            Fixture.competition_type
            == competition_type
        )
        .order_by(
            Fixture.scheduled_at.desc(),
            Fixture.id.desc(),
        )
        .limit(NEWS_LIMIT)
    )

    rows = list(result.all())

    club_ids = [
        fixture.home_club_id
        for fixture, match in rows
    ] + [
        fixture.away_club_id
        for fixture, match in rows
    ]

    names = await _club_names(
        session,
        list(set(club_ids)),
    )

    news = []

    for fixture, match in rows:
        home = names.get(
            fixture.home_club_id,
            f"Club #{fixture.home_club_id}",
        )
        away = names.get(
            fixture.away_club_id,
            f"Club #{fixture.away_club_id}",
        )

        status = str(
            match.status
        ).lower()

        if status in {
            "finished",
            "completed",
        }:
            text = (
                f"{label} : {home} "
                f"{match.home_score}–"
                f"{match.away_score} {away}"
            )
        else:
            text = (
                f"{label} : {home} vs {away}"
            )

        news.append(
            (
                fixture.scheduled_at,
                text,
            )
        )

    return news


async def _big_match_news(
    session,
):
    result = await session.execute(
        select(Fixture)
        .where(
            Fixture.competition_type.in_(
                [
                    "league",
                    "league_europe",
                    "cup",
                ]
            )
        )
        .order_by(
            Fixture.scheduled_at.asc(),
            Fixture.id.asc(),
        )
        .limit(NEWS_LIMIT * 2)
    )

    fixtures = list(result.scalars().all())

    club_ids = list(
        {
            club_id
            for fixture in fixtures
            for club_id in (
                fixture.home_club_id,
                fixture.away_club_id,
            )
        }
    )

    averages = await _club_averages(
        session,
        club_ids,
    )
    names = await _club_names(
        session,
        club_ids,
    )

    news = []

    for fixture in fixtures:
        home_average = averages.get(
            fixture.home_club_id,
            0.0,
        )
        away_average = averages.get(
            fixture.away_club_id,
            0.0,
        )

        if (
            home_average >= BIG_MATCH_AVERAGE
            and away_average >= BIG_MATCH_AVERAGE
        ):
            home = names.get(
                fixture.home_club_id,
                f"Club #{fixture.home_club_id}",
            )
            away = names.get(
                fixture.away_club_id,
                f"Club #{fixture.away_club_id}",
            )

            news.append(
                (
                    fixture.scheduled_at,
                    (
                        "⚔️ BIG MATCH : "
                        f"{home} ({home_average:.0f}) "
                        "vs "
                        f"{away} ({away_average:.0f})"
                    ),
                )
            )

    return news


async def _winning_streak_news(
    session,
):
    """
    Calculates current winning streaks from completed fixtures.

    A streak is calculated from the most recent completed
    matches of each club, across competitions.
    """
    result = await session.execute(
        select(
            Fixture,
            Match,
        )
        .join(
            Match,
            Match.fixture_id == Fixture.id,
        )
        .where(
            Match.status.in_(
                [
                    "finished",
                    "completed",
                ]
            )
        )
        .order_by(
            Fixture.scheduled_at.desc(),
            Fixture.id.desc(),
        )
    )

    rows = list(result.all())

    streaks: dict[int, int] = {}
    broken: set[int] = set()

    for fixture, match in rows:
        clubs = (
            fixture.home_club_id,
            fixture.away_club_id,
        )

        for club_id in clubs:
            if club_id in broken:
                continue

            if club_id == fixture.home_club_id:
                won = (
                    match.home_score
                    > match.away_score
                )
            else:
                won = (
                    match.away_score
                    > match.home_score
                )

            if won:
                streaks[club_id] = (
                    streaks.get(club_id, 0) + 1
                )
            else:
                broken.add(club_id)

    important = [
        (club_id, streak)
        for club_id, streak in streaks.items()
        if streak >= 3
    ]

    if not important:
        return []

    names = await _club_names(
        session,
        [club_id for club_id, _ in important],
    )

    now = datetime.now().astimezone()

    return [
        (
            now,
            (
                f"🔥 {names.get(club_id, f'Club #{club_id}')} "
                f"is on a {streak}-match winning streak!"
            ),
        )
        for club_id, streak in important
    ]


async def news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    async with AsyncSessionLocal() as session:
        events = []

        events.extend(
            await _transfer_news(session)
        )

        events.extend(
            await _fixture_news(
                session,
                "league",
                "🏆 League",
            )
        )

        events.extend(
            await _fixture_news(
                session,
                "league_europe",
                "🌍 Europe",
            )
        )

        events.extend(
            await _fixture_news(
                session,
                "cup",
                "🏆 Cup",
            )
        )

        events.extend(
            await _winning_streak_news(
                session
            )
        )

        events.extend(
            await _big_match_news(
                session
            )
        )

    # Most recent events first.
    events.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    events = events[:NEWS_LIMIT]

    if not events:
        await message.reply_text(
            (
                "📰 𝐍𝐄𝐖𝐒\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📭 No important events yet."
            )
        )
        return

    lines = [
        "📰 𝐋𝐄𝐆𝐄𝐍𝐃𝐀𝐑𝐘 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋 𝐍𝐄𝐖𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for timestamp, text in events:
        if timestamp is not None:
            time_text = timestamp.strftime(
                "%d/%m %H:%M"
            )
            lines.append(
                f"🕒 {time_text}\n{text}"
            )
        else:
            lines.append(text)

    await message.reply_text(
        "\n\n".join(lines)
    )


news_handler = CommandHandler(
    "news",
    news,
)