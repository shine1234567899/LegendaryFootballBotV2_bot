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
    """
    Create the missing fixtures for this league/season.

    IMPORTANT:
    - Existing fixtures are never duplicated.
    - Fixtures cancelled by /stopleague are reactivated when the league is
      started again.
    - If a new manager/club was added, only the newly required pairings are
      created.
    - One round spans TWO consecutive days.
    - League rounds can start on ANY day.
    """
    rounds = _build_rounds(club_ids)

    # Load every existing league fixture for this season. We intentionally
    # inspect pairings instead of only counting rows: a count can be "full"
    # while a particular home/away pairing is missing.
    existing_result = await session.execute(
        select(Fixture, Match)
        .join(
            Match,
            Match.fixture_id == Fixture.id,
        )
        .where(
            Fixture.season_id == season_id,
            Fixture.competition_type == "league",
        )
    )

    existing_rows = list(existing_result.all())

    # Only fixtures belonging to the requested league's current clubs.
    club_set = set(club_ids)

    existing_by_pair = {}
    for fixture, match in existing_rows:
        if (
            fixture.home_club_id in club_set
            and fixture.away_club_id in club_set
        ):
            existing_by_pair[
                (fixture.home_club_id, fixture.away_club_id)
            ] = (fixture, match)

    # A league round has one fixture per club. With N clubs there are
    # N-1 rounds in each leg and N*(N-1) fixtures in total.
    expected_count = len(club_ids) * (len(club_ids) - 1)

    # Schedule base: continue from the latest existing league fixture when
    # possible; otherwise start five minutes from now.
    existing_dates = [
        fixture.scheduled_at
        for fixture, _ in existing_by_pair.values()
        if fixture.scheduled_at is not None
    ]

    if existing_dates:
        base_time = min(existing_dates)
        base_time = base_time.replace(
            hour=12,
            minute=0,
            second=0,
            microsecond=0,
        )
    else:
        base_time = datetime.utcnow() + timedelta(minutes=5)
        base_time = base_time.replace(
            second=0,
            microsecond=0,
        )

    # Every round occupies two consecutive calendar days.
    first_day_count = (len(club_ids) // 2 + 1) // 2
    second_day_count = (len(club_ids) // 2) - first_day_count

    # For even N, first_day_count is ceil(matches_per_round / 2).
    matches_per_round = len(club_ids) // 2
    first_day_count = (matches_per_round + 1) // 2
    second_day_count = matches_per_round - first_day_count

    created = 0
    reactivated = 0

    for round_index, pairings in enumerate(rounds, start=1):
        round_start = base_time + timedelta(
            days=(round_index - 1) * 2
        )

        day_one = round_start
        day_two = round_start + timedelta(days=1)

        for match_index, (home_id, away_id) in enumerate(
            pairings,
            start=1,
        ):
            if match_index <= first_day_count:
                scheduled_at = day_one + timedelta(
                    minutes=(match_index - 1) * 5
                )
            else:
                second_index = match_index - first_day_count
                scheduled_at = day_two + timedelta(
                    minutes=(second_index - 1) * 5
                )

            pair = existing_by_pair.get(
                (home_id, away_id)
            )

            if pair is not None:
                fixture, match = pair

                # Restarting a stopped league resumes its already-created
                # future fixtures instead of duplicating them.
                if (
                    str(fixture.status).lower()
                    in {"cancelled", "canceled"}
                    or str(match.status).lower()
                    in {"cancelled", "canceled"}
                ):
                    fixture.status = "scheduled"
                    match.status = "not_started"
                    match.minute = 0
                    match.home_score = 0
                    match.away_score = 0
                    reactivated += 1

                # Keep the canonical round/date for this season.
                fixture.round_number = round_index
                fixture.scheduled_at = scheduled_at
                continue

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

            existing_by_pair[
                (home_id, away_id)
            ] = (fixture, match)

            created += 1

    return (
        created,
        reactivated,
        len(rounds),
        expected_count,
    )


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

    (
        created_fixtures,
        reactivated_fixtures,
        rounds,
        expected_fixtures,
    ) = await _create_league_schedule(
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
        "reactivated": reactivated_fixtures,
        "expected_fixtures": expected_fixtures,
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
                    f"⚽ New fixtures: {result_data['fixtures']}\n"
                    f"🔄 Resumed fixtures: {result_data['reactivated']}\n"
                    f"📊 Total required: {result_data['expected_fixtures']}\n\n"
                    "🏠 Home and away matches are ready."
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
            f"+{item['fixtures']} new • "
            f"↩️ {item['reactivated']} resumed"
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