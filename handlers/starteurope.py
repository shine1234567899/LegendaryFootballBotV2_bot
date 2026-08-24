from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, func

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    Club,
    League,
    LeagueSeasonClub,
    Season,
    Competition,
    CompetitionSeason,
    CompetitionParticipant,
)


# ==========================================================
# START EUROPE — OWNER ONLY
# ==========================================================

TOP_LEAGUES_COUNT = 5
DIRECT_SLOTS_PER_LEAGUE = 4
MAX_SLOTS_PER_LEAGUE = 8
TARGET_CLUBS = 36


async def _active_season(session):
    result = await session.execute(
        select(Season)
        .where(Season.is_active.is_(True))
        .order_by(Season.number.desc())
    )
    return result.scalars().first()


async def _top_leagues(session):
    """
    Select the five highest-tier domestic leagues.

    Lower tier number = higher division.
    If several leagues share the same tier, name is used
    only as a deterministic tie-breaker.
    """
    result = await session.execute(
        select(League)
        .where(
            League.status == "active",
            League.parent_league_id.is_(None),
        )
        .order_by(
            League.tier.asc(),
            League.name.asc(),
        )
        .limit(TOP_LEAGUES_COUNT)
    )
    return list(result.scalars().all())


async def _ranked_clubs_for_league(
    session,
    league_id: int,
    season_id: int,
):
    """
    Return clubs ordered by their current league performance.

    Primary ranking:
      points
    Then:
      goal difference
      goals scored
      wins
      club id (stable tie-break)
    """
    result = await session.execute(
        select(LeagueSeasonClub, Club)
        .join(
            Club,
            Club.id == LeagueSeasonClub.club_id,
        )
        .where(
            LeagueSeasonClub.league_id == league_id,
            LeagueSeasonClub.season_id == season_id,
        )
        .order_by(
            LeagueSeasonClub.points.desc(),
            (
                LeagueSeasonClub.goals_for
                - LeagueSeasonClub.goals_against
            ).desc(),
            LeagueSeasonClub.goals_for.desc(),
            LeagueSeasonClub.wins.desc(),
            Club.id.asc(),
        )
    )

    return list(result.all())


async def _get_or_create_competition(
    session,
    name: str,
    competition_type: str,
):
    result = await session.execute(
        select(Competition).where(
            Competition.name == name
        )
    )
    competition = result.scalar_one_or_none()

    if competition is None:
        competition = Competition(
            name=name,
            competition_type=competition_type,
            country="Europe",
            tier=1,
            max_teams=TARGET_CLUBS,
            format="league_phase",
            is_active=True,
        )
        session.add(competition)
        await session.flush()

    return competition


async def _get_or_create_competition_season(
    session,
    competition_id: int,
    season_id: int,
):
    result = await session.execute(
        select(CompetitionSeason).where(
            CompetitionSeason.competition_id == competition_id,
            CompetitionSeason.season_id == season_id,
        )
    )
    competition_season = result.scalar_one_or_none()

    if competition_season is None:
        competition_season = CompetitionSeason(
            competition_id=competition_id,
            season_id=season_id,
            status="open",
        )
        session.add(competition_season)
        await session.flush()

    return competition_season


async def _participant_exists(
    session,
    competition_season_id: int,
    club_id: int,
):
    result = await session.execute(
        select(CompetitionParticipant.id).where(
            CompetitionParticipant.competition_season_id
            == competition_season_id,
            CompetitionParticipant.club_id == club_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _select_clubs(
    session,
    leagues,
    season_id: int,
):
    """
    Qualification rule requested for Europe:

    1. Take the top 4 clubs from each of the 5 best leagues.
       = 20 direct places.

    2. From the clubs left outside those 20, take the best clubs
       by league performance until the competition reaches 36.

    3. A domestic league may contribute at most 8 clubs total.
       Therefore, after its first 4, no league can send more than
       4 additional clubs.

    4. If there are not enough eligible clubs to reach 36, the
       command reports the shortfall instead of inventing clubs.
    """
    ranked_by_league = {}
    selected = []
    selected_ids = set()
    slots_used = {league.id: 0 for league in leagues}

    for league in leagues:
        rows = await _ranked_clubs_for_league(
            session,
            league.id,
            season_id,
        )
        ranked_by_league[league.id] = rows

        direct = rows[:DIRECT_SLOTS_PER_LEAGUE]

        for membership, club in direct:
            if club.id in selected_ids:
                continue

            selected.append(
                (club, league, membership)
            )
            selected_ids.add(club.id)
            slots_used[league.id] += 1

    if len(selected) >= TARGET_CLUBS:
        return selected[:TARGET_CLUBS], []

    # Candidates after the first four in each league.
    # Global ranking is based on the same domestic performance.
    extra_candidates = []

    for league in leagues:
        rows = ranked_by_league[league.id]
        for rank, (membership, club) in enumerate(
            rows[DIRECT_SLOTS_PER_LEAGUE:],
            start=DIRECT_SLOTS_PER_LEAGUE + 1,
        ):
            if club.id in selected_ids:
                continue

            extra_candidates.append(
                (
                    membership.points,
                    (
                        membership.goals_for
                        - membership.goals_against
                    ),
                    membership.goals_for,
                    membership.wins,
                    club.id,
                    rank,
                    club,
                    league,
                    membership,
                )
            )

    extra_candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3],
            -item[4],
        ),
        reverse=True,
    )

    for candidate in extra_candidates:
        if len(selected) >= TARGET_CLUBS:
            break

        (
            _points,
            _gd,
            _gf,
            _wins,
            _club_id,
            _rank,
            club,
            league,
            membership,
        ) = candidate

        # Maximum 8 clubs total from one of the five leagues.
        if slots_used[league.id] >= MAX_SLOTS_PER_LEAGUE:
            continue

        selected.append(
            (club, league, membership)
        )
        selected_ids.add(club.id)
        slots_used[league.id] += 1

    skipped = [
        (
            league,
            slots_used[league.id],
            len(ranked_by_league[league.id]),
        )
        for league in leagues
    ]

    return selected, skipped


async def starteurope(
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

    await message.reply_text(
        "🌍 Checking the five best leagues and European qualification..."
    )

    async with AsyncSessionLocal() as session:
        season = await _active_season(session)

        if season is None:
            await message.reply_text(
                "❌ There is no active season."
            )
            return

        leagues = await _top_leagues(session)

        if len(leagues) < TOP_LEAGUES_COUNT:
            await message.reply_text(
                (
                    "❌ Not enough active domestic leagues.\n"
                    f"Required: {TOP_LEAGUES_COUNT}\n"
                    f"Found: {len(leagues)}"
                )
            )
            return

        selected, league_summary = await _select_clubs(
            session,
            leagues,
            season.id,
        )

        if len(selected) < TARGET_CLUBS:
            await session.rollback()

            await message.reply_text(
                (
                    "❌ European competition cannot be filled.\n\n"
                    f"👥 Qualified clubs: {len(selected)}/{TARGET_CLUBS}\n"
                    "📌 Rule: top 4 from each of the 5 best leagues, "
                    "then best remaining clubs, with a maximum of 8 "
                    "clubs from one domestic league."
                )
            )
            return

        competition = await _get_or_create_competition(
            session,
            "Champions League",
            "champions_league",
        )

        competition_season = await _get_or_create_competition_season(
            session,
            competition.id,
            season.id,
        )

        added = 0

        for club, league, membership in selected:
            exists = await _participant_exists(
                session,
                competition_season.id,
                club.id,
            )

            if exists:
                continue

            participant = CompetitionParticipant(
                competition_season_id=competition_season.id,
                club_id=club.id,
                qualification_source=(
                    f"Top {DIRECT_SLOTS_PER_LEAGUE}"
                    if membership in [
                        item[2]
                        for item in selected
                        if item[1].id == league.id
                    ][:DIRECT_SLOTS_PER_LEAGUE]
                    else "Best remaining",
                ),
                seed=None,
            )

            session.add(participant)
            added += 1

        competition_season.status = "active"

        await session.commit()

    lines = [
        "🌍 𝐂𝐇𝐀𝐌𝐏𝐈𝐎𝐍𝐒 𝐋𝐄𝐀𝐆𝐔𝐄",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📅 Season : {season.name}",
        f"👥 Clubs : {len(selected)}/{TARGET_CLUBS}",
        f"➕ Added : {added}",
        "",
        "📋 Qualification:",
    ]

    for league in leagues:
        league_count = sum(
            1
            for _club, selected_league, _membership in selected
            if selected_league.id == league.id
        )
        lines.append(
            f"🏆 {league.name} : {league_count} clubs"
        )

    lines.extend(
        [
            "",
            "🥇 Top 4 from each top-5 league are guaranteed.",
            "⭐ Remaining places use the best clubs left out.",
            "🔒 Maximum 8 clubs from one domestic league.",
        ]
    )

    await message.reply_text(
        "\n".join(lines)
    )


starteurope_handler = CommandHandler(
    "starteurope",
    starteurope,
)