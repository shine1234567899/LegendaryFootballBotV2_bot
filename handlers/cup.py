from __future__ import annotations
from pathlib import Path

from datetime import datetime

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

from services.competition_scheduler import (
    schedule_slots,
    validate_fixture_datetime,
)



IMAGE_FILE = Path(__file__).resolve().parent.parent / "assets" / "cup.jpg"
# ==========================================================
# CUP
# ==========================================================
#
# Cup competition rules:
#
#   Wednesday / Thursday ONLY
#
# The Cup module prepares competition state and exposes the
# scheduling rules. Fixture creation will be handled by the
# Cup start engine once the exact Cup entry format is fixed.
#
# Knockout ties can use:
#   - single match
#   - two legs
#
# For a two-leg tie:
#   first leg + second leg
#   aggregate score
#   extra time if aggregate is level
#   penalties if still level
#
# No away-goals rule.
# ==========================================================


CUP_DAYS = (2, 3)  # Wednesday / Thursday


def cup_slots(
    count: int,
    start: datetime | None = None,
) -> list[datetime]:
    """
    Return Cup kickoff slots.

    The central scheduler guarantees Wednesday/Thursday only.
    """
    slots = schedule_slots(
        competition_type="cup",
        count=count,
        start=start,
    )

    for scheduled_at in slots:
        validate_fixture_datetime(
            "cup",
            scheduled_at,
        )

    return slots


def aggregate_score(
    first_leg_home_score: int,
    first_leg_away_score: int,
    second_leg_home_score: int,
    second_leg_away_score: int,
) -> tuple[int, int]:
    """
    First leg:
        A home vs B away

    Second leg:
        B home vs A away
    """
    club_a = (
        first_leg_home_score
        + second_leg_away_score
    )
    club_b = (
        first_leg_away_score
        + second_leg_home_score
    )

    return club_a, club_b


def resolve_two_leg_tie(
    club_a_id: int,
    club_b_id: int,
    first_leg_home_score: int,
    first_leg_away_score: int,
    second_leg_home_score: int,
    second_leg_away_score: int,
    extra_time_a: int = 0,
    extra_time_b: int = 0,
    penalties_a: int | None = None,
    penalties_b: int | None = None,
) -> dict:
    """
    Resolve a two-leg Cup tie.

    No away-goals rule is applied.
    """
    aggregate_a, aggregate_b = aggregate_score(
        first_leg_home_score,
        first_leg_away_score,
        second_leg_home_score,
        second_leg_away_score,
    )

    if aggregate_a > aggregate_b:
        return {
            "winner_club_id": club_a_id,
            "aggregate_a": aggregate_a,
            "aggregate_b": aggregate_b,
            "extra_time": False,
            "penalties": False,
            "pending": False,
        }

    if aggregate_b > aggregate_a:
        return {
            "winner_club_id": club_b_id,
            "aggregate_a": aggregate_a,
            "aggregate_b": aggregate_b,
            "extra_time": False,
            "penalties": False,
            "pending": False,
        }

    total_a = aggregate_a + extra_time_a
    total_b = aggregate_b + extra_time_b

    if total_a > total_b:
        return {
            "winner_club_id": club_a_id,
            "aggregate_a": total_a,
            "aggregate_b": total_b,
            "extra_time": True,
            "penalties": False,
            "pending": False,
        }

    if total_b > total_a:
        return {
            "winner_club_id": club_b_id,
            "aggregate_a": total_a,
            "aggregate_b": total_b,
            "extra_time": True,
            "penalties": False,
            "pending": False,
        }

    if penalties_a is None or penalties_b is None:
        return {
            "winner_club_id": None,
            "aggregate_a": total_a,
            "aggregate_b": total_b,
            "extra_time": True,
            "penalties": True,
            "pending": True,
        }

    if penalties_a == penalties_b:
        raise ValueError(
            "Penalty shootout cannot finish level."
        )

    winner = (
        club_a_id
        if penalties_a > penalties_b
        else club_b_id
    )

    return {
        "winner_club_id": winner,
        "aggregate_a": total_a,
        "aggregate_b": total_b,
        "extra_time": True,
        "penalties": True,
        "pending": False,
    }


async def get_active_season(session):
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


async def get_cup_competition(session):
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


async def get_cup_season(
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


async def get_cup_participants(
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


async def cup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner-only Cup overview.

    This does not create fixtures yet.
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
        season = await get_active_season(
            session
        )

        if season is None:
            await message.reply_text(
                "🏆 No active season."
            )
            return

        competition = await get_cup_competition(
            session
        )

        if competition is None:
            await message.reply_text(
                (
                    "🏆 No Cup competition has been "
                    "created yet."
                )
            )
            return

        competition_season = await get_cup_season(
            session,
            competition.id,
            season.id,
        )

        if competition_season is None:
            await message.reply_text(
                (
                    "🏆 The Cup exists, but its season "
                    "is not prepared yet."
                )
            )
            return

        participants = await get_cup_participants(
            session,
            competition_season.id,
        )

    await message.reply_text(
        (
            "🏆 𝐂𝐔𝐏\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 {competition.name}\n"
            f"📅 {season.name}\n"
            f"👥 Participants : {len(participants)}\n\n"
            "📆 Cup match days:\n"
            "🏆 Wednesday / Thursday\n\n"
            "⚽ Knockout options:\n"
            "🏠 First leg + ✈️ second leg\n"
            "📊 Aggregate score\n"
            "⏱️ Extra time if level\n"
            "🎯 Penalties if still level\n"
            "🚫 No away-goals rule"
        )
    )


cup_handler = CommandHandler(
    "cup",
    cup,
)