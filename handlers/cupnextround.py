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

from services.competition_scheduler import schedule_slots


# ==========================================================
# CUP NEXT ROUND — OWNER ONLY
# ==========================================================
#
# /cupnextround
#
# Reads the latest completed Cup round.
# For a two-leg round:
#   first leg + return leg
#   aggregate score
#   extra time / penalties are expected to have already been
#   reflected in the decisive Match score when the match ends.
#
# Because the current Fixture model has no tie_id field, this
# module identifies a tie from the two fixtures containing the
# same pair of clubs in opposite home/away order.
#
# No database columns are invented here.
# ==========================================================


def aggregate_for_tie(
    first_fixture,
    first_match,
    second_fixture,
    second_match,
):
    """
    Convert the two fixtures into a single aggregate score,
    independent of which club was home in each leg.
    """
    scores = {}

    scores[first_fixture.home_club_id] = (
        scores.get(first_fixture.home_club_id, 0)
        + first_match.home_score
    )
    scores[first_fixture.away_club_id] = (
        scores.get(first_fixture.away_club_id, 0)
        + first_match.away_score
    )

    scores[second_fixture.home_club_id] = (
        scores.get(second_fixture.home_club_id, 0)
        + second_match.home_score
    )
    scores[second_fixture.away_club_id] = (
        scores.get(second_fixture.away_club_id, 0)
        + second_match.away_score
    )

    return scores


def _pair_fixtures(rows):
    """
    Pair two-leg fixtures by the two club IDs.

    Returns:
        list[(fixture, match, fixture, match)]
    """
    groups = {}

    for fixture, match in rows:
        key = tuple(
            sorted(
                (
                    fixture.home_club_id,
                    fixture.away_club_id,
                )
            )
        )
        groups.setdefault(key, []).append(
            (fixture, match)
        )

    ties = []

    for key, items in groups.items():
        if len(items) != 2:
            raise ValueError(
                "Every Cup knockout tie must contain exactly "
                "two fixtures before the next round can start."
            )

        first, second = sorted(
            items,
            key=lambda item: (
                item[0].scheduled_at,
                item[0].id,
            ),
        )

        ties.append(
            (
                first[0],
                first[1],
                second[0],
                second[1],
            )
        )

    return ties


def _winner_from_tie(
    first_fixture,
    first_match,
    second_fixture,
    second_match,
):
    scores = aggregate_for_tie(
        first_fixture,
        first_match,
        second_fixture,
        second_match,
    )

    if len(scores) != 2:
        raise ValueError(
            "Invalid Cup tie: expected two clubs."
        )

    ordered = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if ordered[0][1] == ordered[1][1]:
        raise ValueError(
            "A Cup tie is still level after both legs. "
            "Resolve extra time / penalties in the match "
            "result before creating the next round."
        )

    return ordered[0][0]


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
    return result.scalars().first()


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
    return result.scalar_one_or_none()


async def _latest_round(
    session,
    competition_season_id,
):
    result = await session.execute(
        select(CompetitionRound)
        .where(
            CompetitionRound.competition_season_id
            == competition_season_id
        )
        .order_by(
            CompetitionRound.round_number.desc()
        )
    )
    return result.scalars().first()


async def _round_fixtures(
    session,
    season_id,
    round_number,
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
            Fixture.season_id == season_id,
            Fixture.competition_type == "cup",
            Fixture.round_number == round_number,
        )
        .order_by(
            Fixture.scheduled_at.asc(),
            Fixture.id.asc(),
        )
    )

    return list(result.all())


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


async def _create_fixture(
    session,
    season_id,
    home_id,
    away_id,
    scheduled_at,
    round_number,
):
    fixture = Fixture(
        season_id=season_id,
        home_club_id=home_id,
        away_club_id=away_id,
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

    return fixture


async def cupnextround(
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
        "⏳ Checking the latest Cup round..."
    )

    async with AsyncSessionLocal() as session:
        season = await _active_season(session)

        if season is None:
            await message.reply_text(
                "❌ No active season."
            )
            return

        competition = await _cup(session)

        if competition is None:
            await message.reply_text(
                "❌ No Cup competition exists."
            )
            return

        competition_season = await _cup_season(
            session,
            competition.id,
            season.id,
        )

        if competition_season is None:
            await message.reply_text(
                "❌ Cup season is not prepared."
            )
            return

        current_round = await _latest_round(
            session,
            competition_season.id,
        )

        if current_round is None:
            await message.reply_text(
                "❌ No Cup round exists yet."
            )
            return

        rows = await _round_fixtures(
            session,
            season.id,
            current_round.round_number,
        )

        if not rows:
            await message.reply_text(
                "❌ No fixtures found for the latest Cup round."
            )
            return

        unfinished = [
            match
            for fixture, match in rows
            if str(match.status).lower()
            not in {
                "finished",
                "completed",
            }
        ]

        if unfinished:
            await message.reply_text(
                (
                    f"⏳ Round {current_round.round_number} "
                    "is not finished yet.\n\n"
                    f"⚽ Remaining matches: {len(unfinished)}"
                )
            )
            return

        if current_round.round_type != "two_leg":
            await message.reply_text(
                (
                    "ℹ️ The latest round is not marked as "
                    "a two-leg round. Its next-round rules "
                    "will be handled separately."
                )
            )
            return

        try:
            ties = _pair_fixtures(rows)

            winners = []

            for (
                first_fixture,
                first_match,
                second_fixture,
                second_match,
            ) in ties:
                winners.append(
                    _winner_from_tie(
                        first_fixture,
                        first_match,
                        second_fixture,
                        second_match,
                    )
                )

        except ValueError as error:
            await message.reply_text(
                f"❌ {error}"
            )
            return

        # A single winner means the Cup is finished at this
        # stage. We do not create a fake next round.
        if len(winners) == 1:
            current_round.status = "completed"
            competition_season.status = "completed"

            await session.commit()

            await message.reply_text(
                (
                    "🏆 𝐂𝐔𝐏 𝐅𝐈𝐍𝐈𝐒𝐇𝐄𝐃\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "The final winner has been determined.\n"
                    f"🏆 Winner club ID: {winners[0]}"
                )
            )
            return

        next_round_number = (
            current_round.round_number + 1
        )

        existing_result = await session.execute(
            select(CompetitionRound).where(
                CompetitionRound.competition_season_id
                == competition_season.id,
                CompetitionRound.round_number
                == next_round_number,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            await message.reply_text(
                (
                    f"⚠️ Round {next_round_number} "
                    "already exists."
                )
            )
            return

        random.shuffle(winners)

        bye = None

        if len(winners) % 2:
            bye = winners.pop()

        pairs = []

        for index in range(0, len(winners), 2):
            pairs.append(
                (
                    winners[index],
                    winners[index + 1],
                )
            )

        next_round = CompetitionRound(
            competition_season_id=(
                competition_season.id
            ),
            name=f"Round {next_round_number}",
            round_number=next_round_number,
            round_type="two_leg",
            status="scheduled",
        )

        session.add(next_round)
        await session.flush()

        tie_count = len(pairs)

        slots = schedule_slots(
            competition_type="cup",
            count=tie_count * 2,
            start=(
                datetime.now().astimezone()
                + timedelta(minutes=5)
            ),
            max_matches_per_day=max(
                1,
                tie_count,
            ),
        )

        clubs = await _clubs_by_ids(
            session,
            [
                club_id
                for pair in pairs
                for club_id in pair
            ],
        )

        for index, (club_a, club_b) in enumerate(
            pairs
        ):
            await _create_fixture(
                session=session,
                season_id=season.id,
                home_id=club_a,
                away_id=club_b,
                scheduled_at=slots[index],
                round_number=next_round_number,
            )

            await _create_fixture(
                session=session,
                season_id=season.id,
                home_id=club_b,
                away_id=club_a,
                scheduled_at=slots[
                    tie_count + index
                ],
                round_number=next_round_number,
            )

        current_round.status = "completed"

        await session.commit()

    await message.reply_text(
        (
            f"🏆 𝐂𝐔𝐏 𝐑𝐎𝐔𝐍𝐃 {next_round_number}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ Ties: {tie_count}\n"
            f"👥 Qualified clubs: {len(winners)}\n\n"
            "🏠 First legs → Wednesday\n"
            "✈️ Return legs → Thursday\n"
            "📊 Aggregate score decides qualification.\n"
            "⏱️ Aggregate draw → extra time.\n"
            "🎯 Still level → penalties.\n"
            "🚫 No away-goals rule."
        )
    )


cupnextround_handler = CommandHandler(
    "cupnextround",
    cupnextround,
)