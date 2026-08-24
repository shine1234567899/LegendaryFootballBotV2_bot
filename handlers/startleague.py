from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, func, or_

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    League,
    LeagueSeasonClub,
    Season,
    Fixture,
    Match,
)


# ==========================================================
# START LEAGUE — OWNER ONLY
# ==========================================================

MIN_CLUBS = 10


def _is_valid_club_count(count: int) -> bool:
    """
    League can start only with at least 10 clubs
    and an even number of clubs.
    """
    return count >= MIN_CLUBS and count % 2 == 0


async def _get_or_create_active_season(session):
    result = await session.execute(
        select(Season)
        .where(Season.is_active.is_(True))
        .order_by(Season.number.desc())
    )
    season = result.scalars().first()

    if season is not None:
        return season, False

    result = await session.execute(
        select(func.max(Season.number))
    )
    max_number = result.scalar() or 0

    season = Season(
        name=f"Season {max_number + 1}",
        number=max_number + 1,
        is_active=True,
        started_at=datetime.utcnow(),
    )

    session.add(season)
    await session.flush()

    return season, True


async def _get_league_clubs(session, league_id: int, season_id: int):
    result = await session.execute(
        select(LeagueSeasonClub)
        .where(
            LeagueSeasonClub.league_id == league_id,
            LeagueSeasonClub.season_id == season_id,
        )
        .order_by(LeagueSeasonClub.id.asc())
    )
    return list(result.scalars().all())


def _build_rounds(club_ids: list[int]) -> list[list[tuple[int, int]]]:
    """
    Circle-method round robin.
    Returns every round with one match per club.
    Produces home/away double round robin.
    """
    teams = list(club_ids)

    if len(teams) < MIN_CLUBS or len(teams) % 2 != 0:
        raise ValueError(
            "League must contain at least 10 clubs and an even number."
        )

    rounds = []

    # Circle method: fix first team and rotate the rest.
    fixed = teams[0]
    rotating = teams[1:]

    first_leg = []

    for round_number in range(len(teams) - 1):
        current = [fixed] + rotating

        pairings = []

        for index in range(len(teams) // 2):
            home = current[index]
            away = current[-(index + 1)]

            # Alternate home advantage to distribute it better.
            if round_number % 2 == 1:
                home, away = away, home

            pairings.append((home, away))

        first_leg.append(pairings)

        rotating = [
            rotating[-1],
            *rotating[:-1],
        ]

    # Second leg: reverse every fixture.
    second_leg = [
        [(away, home) for home, away in pairings]
        for pairings in first_leg
    ]

    rounds.extend(first_leg)
    rounds.extend(second_leg)

    return rounds


async def _create_league_schedule(
    session,
    league_id: int,
    season_id: int,
    club_ids: list[int],
):
    rounds = _build_rounds(club_ids)

    # Do not create the same league schedule twice in the same season.
    existing_result = await session.execute(
        select(func.count(Fixture.id))
        .where(
            Fixture.season_id == season_id,
            Fixture.competition_type == "league",
            Fixture.home_club_id.in_(club_ids),
            Fixture.away_club_id.in_(club_ids),
        )
    )
    existing_count = int(existing_result.scalar() or 0)

    expected_count = len(club_ids) * (len(club_ids) - 1)

    if existing_count >= expected_count:
        return 0, len(rounds)

    # If a partial schedule exists, do not silently duplicate it.
    if existing_count > 0:
        raise ValueError(
            "This league already has a partial schedule for this season."
        )

    created = 0
    base_time = datetime.utcnow() + timedelta(minutes=5)

    for round_index, pairings in enumerate(rounds, start=1):
        round_time = base_time + timedelta(
            days=round_index - 1
        )

        for match_index, (home_id, away_id) in enumerate(
            pairings,
            start=1,
        ):
            scheduled_at = round_time + timedelta(
                minutes=(match_index - 1) * 5
            )

            fixture = Fixture(
                season_id=season_id,
                home_club_id=home_id,
                away_club_id=away_id,
                scheduled_at=scheduled_at,
                competition_type="league",
                round_number=round_index,
                status="scheduled",
            )

            session.add(fixture)
            await session.flush()

            match = Match(
                fixture_id=fixture.id,
                home_score=0,
                away_score=0,
                minute=0,
                status="not_started",
                possession_home=50,
                possession_away=50,
                stats={},
            )

            session.add(match)
            created += 1

    return created, len(rounds)


async def _start_one_league(
    session,
    league: League,
    season: Season,
):
    memberships = await _get_league_clubs(
        session,
        league.id,
        season.id,
    )

    club_count = len(memberships)

    if not _is_valid_club_count(club_count):
        return {
            "league": league.name,
            "count": club_count,
            "started": False,
            "reason": "Need at least 10 clubs and an even number.",
        }

    # Ensure the club records still point to this league.
    club_ids = [membership.club_id for membership in memberships]

    created_fixtures, rounds = await _create_league_schedule(
        session=session,
        league_id=league.id,
        season_id=season.id,
        club_ids=club_ids,
    )

    league.status = "active"

    return {
        "league": league.name,
        "count": club_count,
        "started": True,
        "fixtures": created_fixtures,
        "rounds": rounds,
    }


async def startleague(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    if not context.args:
        await message.reply_text(
            (
                "🏆 𝐒𝐓𝐀𝐑𝐓 𝐋𝐄𝐀𝐆𝐔𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Use:\n"
                "/startleague <league name>\n"
                "/startleague all\n\n"
                "A league needs at least 10 clubs "
                "and an even number of clubs."
            )
        )
        return

    target = " ".join(context.args).strip()

    await message.reply_text(
        "⏳ Checking leagues and preparing the schedule..."
    )

    async with AsyncSessionLocal() as session:
        # Only create a season when at least one valid league
        # is actually ready to start.
        if target.lower() == "all":
            result = await session.execute(
                select(League)
                .order_by(
                    League.tier.asc(),
                    League.name.asc(),
                )
            )
            leagues = list(result.scalars().all())

            # First use the existing active season if one exists.
            season_result = await session.execute(
                select(Season)
                .where(Season.is_active.is_(True))
                .order_by(Season.number.desc())
            )
            season = season_result.scalars().first()

            if season is None:
                # We need a season before checking memberships.
                season, _ = await _get_or_create_active_season(
                    session
                )

            results = []

            for league in leagues:
                result_data = await _start_one_league(
                    session,
                    league,
                    season,
                )

                results.append(result_data)

            started = [
                item for item in results
                if item["started"]
            ]
            skipped = [
                item for item in results
                if not item["started"]
            ]

            if not started:
                await session.rollback()
                await message.reply_text(
                    (
                        "❌ No league was started.\n\n"
                        "Every league needs at least 10 clubs "
                        "and an even number of clubs."
                    )
                )
                return

            season.started_at = (
                season.started_at
                or datetime.utcnow()
            )
            season.is_active = True

            await session.commit()

        else:
            result = await session.execute(
                select(League).where(
                    League.name.ilike(target)
                )
            )
            league = result.scalar_one_or_none()

            if league is None:
                await session.rollback()
                await message.reply_text(
                    f"❌ League not found: {target}"
                )
                return

            season_result = await session.execute(
                select(Season)
                .where(Season.is_active.is_(True))
                .order_by(Season.number.desc())
            )
            season = season_result.scalars().first()

            if season is None:
                season, _ = await _get_or_create_active_season(
                    session
                )

            result_data = await _start_one_league(
                session,
                league,
                season,
            )

            if not result_data["started"]:
                await session.rollback()
                await message.reply_text(
                    (
                        f"❌ {league.name} was not started.\n\n"
                        f"👥 Clubs: {result_data['count']}\n"
                        "📌 Requirement: at least 10 clubs "
                        "and an even number."
                    )
                )
                return

            season.started_at = (
                season.started_at
                or datetime.utcnow()
            )
            season.is_active = True

            await session.commit()

            await message.reply_text(
                (
                    "🏆 𝐋𝐄𝐀𝐆𝐔𝐄 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏆 {result_data['league']}\n"
                    f"📅 {season.name}\n"
                    f"👥 Clubs: {result_data['count']}\n"
                    f"📅 Rounds: {result_data['rounds']}\n"
                    f"⚽ Fixtures: {result_data['fixtures']}\n\n"
                    "🏠 Home and away matches have been created."
                )
            )
            return

    lines = [
        "🏆 𝐋𝐄𝐀𝐆𝐔𝐄𝐒 𝐒𝐓𝐀𝐑𝐓𝐄𝐃",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📅 {season.name}",
        "",
    ]

    for item in started:
        lines.append(
            f"✅ {item['league']} — "
            f"{item['count']} clubs • "
            f"{item['fixtures']} fixtures"
        )

    if skipped:
        lines.extend(
            [
                "",
                "⏸️ 𝐋𝐄𝐀𝐆𝐔𝐄𝐒 𝐒𝐊𝐈𝐏𝐏𝐄𝐃",
            ]
        )

        for item in skipped:
            lines.append(
                f"⏸️ {item['league']} — "
                f"{item['count']} clubs"
            )

    lines.extend(
        [
            "",
            "📌 Skipped leagues remain available.",
            "You can complete them and launch them individually.",
        ]
    )

    await message.reply_text(
        "\n".join(lines)
    )


startleague_handler = CommandHandler(
    "startleague",
    startleague,
)