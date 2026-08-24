from __future__ import annotations

import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    Club,
    Competition,
    CompetitionParticipant,
    CompetitionRound,
    CompetitionSeason,
    Fixture,
    Match,
    Season,
)

from services.competition_scheduler import (
    schedule_slots,
    validate_fixture_datetime,
)


# ==========================================================
# START CUP — OWNER ONLY
# ==========================================================
#
# /startcup
#
# V2 Round 1:
#   - participants are taken from the Cup competition season
#   - random draw
#   - two-leg tie
#   - first legs on one Cup day
#   - return legs on the next Cup day
#   - Cup days = Wednesday / Thursday
#
# If the number of clubs is odd, one club receives a bye.
#
# The next round will be generated from the winners after
# Round 1 is completed.
#
# Uses only fields confirmed by the current models.py.
# ==========================================================


def _pair_participants(participants):
    shuffled = list(participants)
    random.shuffle(shuffled)

    bye = None

    if len(shuffled) % 2:
        bye = shuffled.pop()

    pairs = []

    for index in range(0, len(shuffled), 2):
        pairs.append(
            (
                shuffled[index],
                shuffled[index + 1],
            )
        )

    return pairs, bye


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


async def _cup(session):
    result = await session.execute(
        select(Competition)
        .where(
            Competition.competition_type == "cup"
        )
        .order_by(
            Competition.id.asc()
        )
    )
    competition = result.scalars().first()

    if competition is not None:
        return competition

    # Create the Cup automatically the first time /startcup is used.
    competition = Competition(
        name="Legendary Football Cup",
        competition_type="cup",
        country=None,
        is_active=True,
    )

    session.add(competition)
    await session.flush()

    return competition


async def _cup_season(
    session,
    competition_id,
    season_id,
):
    result = await session.execute(
        select(CompetitionSeason).where(
            CompetitionSeason.competition_id
            == competition_id,
            CompetitionSeason.season_id
            == season_id,
        )
    )
    competition_season = result.scalar_one_or_none()

    if competition_season is not None:
        return competition_season

    competition_season = CompetitionSeason(
        competition_id=competition_id,
        season_id=season_id,
        status="scheduled",
    )

    session.add(competition_season)
    await session.flush()

    return competition_season


async def _participants(
    session,
    competition_season_id,
):
    result = await session.execute(
        select(CompetitionParticipant)
        .where(
            CompetitionParticipant.competition_season_id
            == competition_season_id,
            CompetitionParticipant.club_id.is_not(None),
            CompetitionParticipant.status == "active",
        )
        .order_by(
            CompetitionParticipant.seed.asc(),
            CompetitionParticipant.id.asc(),
        )
    )

    return list(result.scalars().all())


async def _ensure_participants(
    session,
    competition_season_id,
):
    participants = await _participants(
        session,
        competition_season_id,
    )

    if participants:
        return participants

    result = await session.execute(
        select(Club).order_by(Club.id.asc())
    )
    clubs = list(result.scalars().all())

    if not clubs:
        return []

    shuffled = list(clubs)
    random.shuffle(shuffled)

    for seed, club in enumerate(shuffled, start=1):
        participant = CompetitionParticipant(
            competition_season_id=competition_season_id,
            club_id=club.id,
            manager_id=None,
            country_code=None,
            country_name=None,
            seed=seed,
            status="active",
        )
        session.add(participant)

    await session.flush()

    return await _participants(
        session,
        competition_season_id,
    )


async def _clubs_by_ids(
    session,
    club_ids,
):
    result = await session.execute(
        select(Club).where(
            Club.id.in_(club_ids)
        )
    )

    return {
        club.id: club
        for club in result.scalars().all()
    }


async def _round_exists(
    session,
    competition_season_id,
    round_number,
):
    result = await session.execute(
        select(CompetitionRound).where(
            CompetitionRound.competition_season_id
            == competition_season_id,
            CompetitionRound.round_number
            == round_number,
        )
    )

    return result.scalar_one_or_none()


async def _create_match(
    session,
    season_id,
    home_club_id,
    away_club_id,
    scheduled_at,
    round_number,
):
    validate_fixture_datetime(
        "cup",
        scheduled_at,
    )

    fixture = Fixture(
        season_id=season_id,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        scheduled_at=scheduled_at,
        competition_type="cup",
        round_number=round_number,
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

    return fixture, match


async def startcup(
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
        "⏳ Preparing the Cup draw..."
    )

    async with AsyncSessionLocal() as session:
        season = await _active_season(session)

        if season is None:
            await message.reply_text(
                "❌ There is no active season."
            )
            return

        competition = await _cup(session)

        if competition is None:
            await message.reply_text(
                "❌ No Cup competition exists yet."
            )
            return

        competition_season = await _cup_season(
            session,
            competition.id,
            season.id,
        )

        participants = await _ensure_participants(
            session,
            competition_season.id,
        )

        if len(participants) < 2:
            await message.reply_text(
                "❌ At least 2 clubs are required."
            )
            return

        existing_round = await _round_exists(
            session,
            competition_season.id,
            1,
        )

        if existing_round is not None:
            await message.reply_text(
                (
                    "⚠️ Cup Round 1 already exists.\n"
                    "No duplicate draw was created."
                )
            )
            return

        pairs, bye = _pair_participants(
            participants
        )

        round_one = CompetitionRound(
            competition_season_id=(
                competition_season.id
            ),
            name="Round 1",
            round_number=1,
            round_type="two_leg",
            status="scheduled",
        )

        session.add(round_one)
        await session.flush()

        # One slot per tie for the first leg, then one slot per
        # tie for the return leg. max_matches_per_day forces
        # all first legs onto the first Cup day and returns onto
        # the next Cup day.
        tie_count = len(pairs)

        # The central scheduler does not support max_matches_per_day.
        # Schedule the first legs separately, then start the return legs
        # from the following calendar day so they fall on the next allowed
        # Cup day (Wednesday/Thursday).
        first_leg_slots = schedule_slots(
            competition_type="cup",
            count=tie_count,
            start=(
                datetime.now().astimezone()
                + timedelta(minutes=5)
            ),
        )

        return_start = (
            first_leg_slots[0] + timedelta(days=1)
            if first_leg_slots
            else datetime.now().astimezone()
            + timedelta(days=1, minutes=5)
        )

        return_leg_slots = schedule_slots(
            competition_type="cup",
            count=tie_count,
            start=return_start,
        )

        slots = first_leg_slots + return_leg_slots

        club_ids = [
            participant.club_id
            for pair in pairs
            for participant in pair
        ]

        clubs = await _clubs_by_ids(
            session,
            club_ids,
        )

        first_legs = []
        return_legs = []

        for index, (participant_a, participant_b) in enumerate(
            pairs
        ):
            club_a = clubs[participant_a.club_id]
            club_b = clubs[participant_b.club_id]

            first_home = club_a
            first_away = club_b

            return_home = club_b
            return_away = club_a

            first_slot = slots[index]
            return_slot = slots[
                tie_count + index
            ]

            first_fixture, _ = await _create_match(
                session=session,
                season_id=season.id,
                home_club_id=first_home.id,
                away_club_id=first_away.id,
                scheduled_at=first_slot,
                round_number=1,
            )

            return_fixture, _ = await _create_match(
                session=session,
                season_id=season.id,
                home_club_id=return_home.id,
                away_club_id=return_away.id,
                scheduled_at=return_slot,
                round_number=1,
            )

            first_legs.append(
                (
                    first_home.name,
                    first_away.name,
                    first_fixture.scheduled_at,
                )
            )

            return_legs.append(
                (
                    return_home.name,
                    return_away.name,
                    return_fixture.scheduled_at,
                )
            )

        competition_season.status = "active"

        await session.commit()

        participant_count = len(participants)

    lines = [
        "🏆 𝐂𝐔𝐏 𝐑𝐎𝐔𝐍𝐃 𝟏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🏆 {competition.name}",
        f"📅 {season.name}",
        f"👥 Clubs : {participant_count}",
        f"⚔️ Ties : {len(pairs)}",
        "",
        "🏠 𝐅𝐈𝐑𝐒𝐓 𝐋𝐄𝐆",
    ]

    for index, (
        home,
        away,
        scheduled_at,
    ) in enumerate(first_legs, start=1):
        lines.append(
            (
                f"{index}. {home} vs {away}\n"
                f"📅 {scheduled_at.strftime('%A %d/%m')} "
                f"⏰ {scheduled_at.strftime('%H:%M')}"
            )
        )

    lines.extend(
        [
            "",
            "✈️ 𝐑𝐄𝐓𝐔𝐑𝐍 𝐋𝐄𝐆",
        ]
    )

    for index, (
        home,
        away,
        scheduled_at,
    ) in enumerate(return_legs, start=1):
        lines.append(
            (
                f"{index}. {home} vs {away}\n"
                f"📅 {scheduled_at.strftime('%A %d/%m')} "
                f"⏰ {scheduled_at.strftime('%H:%M')}"
            )
        )

    if bye is not None:
        club_name = (
            clubs.get(bye.club_id).name
            if bye.club_id in clubs
            else f"Club #{bye.club_id}"
        )

        lines.extend(
            [
                "",
                f"🎟️ BYE : {club_name}",
                "This club advances automatically.",
            ]
        )

    lines.extend(
        [
            "",
            "📆 Cup days : Wednesday / Thursday",
            "📊 Qualification uses aggregate score.",
            "⏱️ Aggregate draw → extra time.",
            "🎯 Still level → penalties.",
            "🚫 No away-goals rule.",
        ]
    )

    await message.reply_text(
        "\n".join(lines)
    )


startcup_handler = CommandHandler(
    "startcup",
    startcup,
)