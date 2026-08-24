from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    Club,
    Competition,
    CompetitionParticipant,
    CompetitionSeason,
    Season,
)


# ==========================================================
# LEAGUE EUROPE
# ==========================================================
#
# This module contains the rules/state helpers for European
# competitions. Match scheduling is intentionally kept out
# of this file; the central scheduler will assign Europe
# fixtures only to Monday/Tuesday.
#
# European competition:
#   1. League phase
#   2. Knockout ties
#   3. Two legs: home + away
#   4. Aggregate score decides qualification
#   5. If aggregate is level -> extra time
#   6. If still level -> penalties
#
# No away-goals rule is used.
# ==========================================================


EUROPE_DAYS = (0, 1)  # Monday, Tuesday
DEFAULT_LEAGUE_PHASE_CLUBS = 36


@dataclass(frozen=True)
class EuropeanTieResult:
    first_leg_home_score: int
    first_leg_away_score: int
    second_leg_home_score: int
    second_leg_away_score: int
    aggregate_home: int
    aggregate_away: int
    winner_club_id: int | None
    needs_extra_time: bool
    needs_penalties: bool


def aggregate_score(
    first_leg_home_score: int,
    first_leg_away_score: int,
    second_leg_home_score: int,
    second_leg_away_score: int,
) -> tuple[int, int]:
    """
    Returns the aggregate score from the perspective of
    the clubs that played home in leg 1 and leg 2.

    First leg:
        A (home) vs B (away)

    Second leg:
        B (home) vs A (away)

    Aggregate:
        A = first_leg_home + second_leg_away
        B = first_leg_away + second_leg_home
    """
    aggregate_a = (
        first_leg_home_score
        + second_leg_away_score
    )
    aggregate_b = (
        first_leg_away_score
        + second_leg_home_score
    )

    return aggregate_a, aggregate_b


def resolve_two_leg_tie(
    club_a_id: int,
    club_b_id: int,
    first_leg_home_score: int,
    first_leg_away_score: int,
    second_leg_home_score: int,
    second_leg_away_score: int,
    extra_time_home_score: int = 0,
    extra_time_away_score: int = 0,
    penalty_home_score: int | None = None,
    penalty_away_score: int | None = None,
) -> EuropeanTieResult:
    """
    Resolve a knockout tie.

    Normal time:
        aggregate decides.

    If aggregate is level:
        extra time decides.

    If still level:
        penalties decide.

    This function does not use away goals.
    """
    aggregate_a, aggregate_b = aggregate_score(
        first_leg_home_score,
        first_leg_away_score,
        second_leg_home_score,
        second_leg_away_score,
    )

    if aggregate_a > aggregate_b:
        return EuropeanTieResult(
            first_leg_home_score,
            first_leg_away_score,
            second_leg_home_score,
            second_leg_away_score,
            aggregate_a,
            aggregate_b,
            club_a_id,
            False,
            False,
        )

    if aggregate_b > aggregate_a:
        return EuropeanTieResult(
            first_leg_home_score,
            first_leg_away_score,
            second_leg_home_score,
            second_leg_away_score,
            aggregate_a,
            aggregate_b,
            club_b_id,
            False,
            False,
        )

    # Aggregate is level -> extra time.
    extra_a = aggregate_a + extra_time_away_score
    extra_b = aggregate_b + extra_time_home_score

    if extra_a > extra_b:
        return EuropeanTieResult(
            first_leg_home_score,
            first_leg_away_score,
            second_leg_home_score,
            second_leg_away_score,
            extra_a,
            extra_b,
            club_a_id,
            True,
            False,
        )

    if extra_b > extra_a:
        return EuropeanTieResult(
            first_leg_home_score,
            first_leg_away_score,
            second_leg_home_score,
            second_leg_away_score,
            extra_a,
            extra_b,
            club_b_id,
            True,
            False,
        )

    # Still level -> penalties are required.
    if (
        penalty_home_score is None
        or penalty_away_score is None
    ):
        return EuropeanTieResult(
            first_leg_home_score,
            first_leg_away_score,
            second_leg_home_score,
            second_leg_away_score,
            extra_a,
            extra_b,
            None,
            True,
            True,
        )

    winner = (
        club_a_id
        if penalty_home_score > penalty_away_score
        else club_b_id
    )

    return EuropeanTieResult(
        first_leg_home_score,
        first_leg_away_score,
        second_leg_home_score,
        second_leg_away_score,
        extra_a,
        extra_b,
        winner,
        True,
        False,
    )


async def get_active_season(session):
    result = await session.execute(
        select(Season)
        .where(Season.is_active.is_(True))
        .order_by(Season.number.desc())
    )
    return result.scalars().first()


async def get_competition(
    session,
    name: str = "Champions League",
):
    result = await session.execute(
        select(Competition).where(
            Competition.name == name
        )
    )
    return result.scalar_one_or_none()


async def get_competition_season(
    session,
    competition_id: int,
    season_id: int,
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


async def get_european_participants(
    session,
    competition_season_id: int,
):
    result = await session.execute(
        select(
            CompetitionParticipant,
            Club,
        )
        .join(
            Club,
            Club.id
            == CompetitionParticipant.club_id,
        )
        .where(
            CompetitionParticipant.competition_season_id
            == competition_season_id,
        )
        .order_by(
            CompetitionParticipant.seed.asc(),
            Club.id.asc(),
        )
    )

    return list(result.all())


async def validate_league_phase_size(
    participants: Iterable[CompetitionParticipant],
    expected: int = DEFAULT_LEAGUE_PHASE_CLUBS,
) -> bool:
    return len(list(participants)) == expected


# ----------------------------------------------------------
# OWNER INFORMATION COMMAND
# ----------------------------------------------------------

async def league_europe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner-only diagnostic/overview command.

    /leagueeurope

    It does not create matches. It shows the current European
    competition state so the scheduler can use the same data.
    """
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    async with AsyncSessionLocal() as session:
        season = await get_active_season(session)

        if season is None:
            await message.reply_text(
                "🌍 No active season."
            )
            return

        competition = await get_competition(session)

        if competition is None:
            await message.reply_text(
                (
                    "🌍 Champions League has not been created "
                    "for this season yet."
                )
            )
            return

        competition_season = (
            await get_competition_season(
                session,
                competition.id,
                season.id,
            )
        )

        if competition_season is None:
            await message.reply_text(
                (
                    "🌍 Champions League exists, but there is "
                    "no competition season yet."
                )
            )
            return

        participants = (
            await get_european_participants(
                session,
                competition_season.id,
            )
        )

    count = len(participants)

    await message.reply_text(
        (
            "🌍 𝐋𝐄𝐀𝐆𝐔𝐄 𝐄𝐔𝐑𝐎𝐏𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 Competition : {competition.name}\n"
            f"📅 Season : {season.name}\n"
            f"👥 Participants : {count}\n"
            f"📊 League phase target : "
            f"{DEFAULT_LEAGUE_PHASE_CLUBS}\n\n"
            "📅 Europe match days:\n"
            "🌍 Monday + Tuesday\n\n"
            "⚽ Knockout ties:\n"
            "🏠 First leg + ✈️ second leg\n"
            "📊 Aggregate score\n"
            "⏱️ Extra time if level\n"
            "🎯 Penalties if still level\n"
            "🚫 No away-goals rule"
        )
    )


league_europe_handler = CommandHandler(
    "leagueeurope",
    league_europe,
)