from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Iterable

# ==========================================================
# COMPETITION SCHEDULER
# ==========================================================
#
# Official V2 calendar:
#
#   LEAGUE        -> Friday / Saturday / Sunday
#   LEAGUE EUROPE -> Monday / Tuesday
#   CUP           -> Wednesday / Thursday
#
# This module ONLY decides when a fixture may be scheduled.
# It does not simulate matches and does not create fixtures.
#
# ==========================================================


LEAGUE_DAYS = frozenset({4, 5, 6})        # Fri/Sat/Sun
EUROPE_DAYS = frozenset({0, 1})           # Mon/Tue
CUP_DAYS = frozenset({2, 3})              # Wed/Thu

DEFAULT_TIMEZONE = "UTC"

# Five-minute spacing prevents a large batch of fixtures from
# receiving exactly the same kickoff time.
MATCH_INTERVAL_MINUTES = 5

# Start times are deliberately simple for V2.
DEFAULT_START_HOUR = 12
DEFAULT_START_MINUTE = 0


def allowed_weekdays(competition_type: str) -> frozenset[int]:
    """
    Return the allowed Python weekday numbers.

    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6
    """
    competition = competition_type.strip().lower()

    if competition in {
        "league",
        "domestic_league",
        "national_league",
    }:
        return LEAGUE_DAYS

    if competition in {
        "league_europe",
        "europe",
        "champions_league",
        "europa_league",
        "conference_league",
    }:
        return EUROPE_DAYS

    if competition in {
        "cup",
        "domestic_cup",
    }:
        return CUP_DAYS

    raise ValueError(
        f"Unknown competition type: {competition_type}"
    )


def is_allowed_day(
    competition_type: str,
    when: datetime,
) -> bool:
    """Return True when the datetime falls on an allowed day."""
    return when.weekday() in allowed_weekdays(
        competition_type
    )


def next_allowed_datetime(
    competition_type: str,
    start: datetime,
) -> datetime:
    """
    Return the first allowed datetime on/after `start`.

    The returned time is normalized to the default V2 start time
    when the requested datetime falls on a forbidden day.
    """
    allowed = allowed_weekdays(competition_type)

    current = start.replace(
        second=0,
        microsecond=0,
    )

    for _ in range(8):
        if current.weekday() in allowed:
            return current

        current = (
            current
            + timedelta(days=1)
        ).replace(
            hour=DEFAULT_START_HOUR,
            minute=DEFAULT_START_MINUTE,
        )

    raise RuntimeError(
        "Could not find an allowed competition day."
    )


def schedule_slots(
    competition_type: str,
    count: int,
    start: datetime | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> list[datetime]:
    """
    Generate `count` kickoff slots using only the competition's
    permitted weekdays.

    Slots are five minutes apart. When a day is exhausted, the
    scheduler moves to the next permitted day.

    No fixtures are created here.
    """
    if count < 0:
        raise ValueError("count cannot be negative.")

    if count == 0:
        return []

    if start is None:
        start = datetime.now(
            ZoneInfo(timezone)
        )

    current = next_allowed_datetime(
        competition_type,
        start,
    )

    allowed = allowed_weekdays(
        competition_type
    )

    slots = []

    while len(slots) < count:
        if current.weekday() not in allowed:
            current = (
                current
                + timedelta(days=1)
            ).replace(
                hour=DEFAULT_START_HOUR,
                minute=DEFAULT_START_MINUTE,
                second=0,
                microsecond=0,
            )
            continue

        slots.append(current)

        current = (
            current
            + timedelta(
                minutes=MATCH_INTERVAL_MINUTES
            )
        )

        # Once the date changes, jump to the next allowed day
        # at the standard start time.
        if current.date() != slots[-1].date():
            next_day = current
            while next_day.weekday() not in allowed:
                next_day = (
                    next_day
                    + timedelta(days=1)
                )

            current = next_day.replace(
                hour=DEFAULT_START_HOUR,
                minute=DEFAULT_START_MINUTE,
                second=0,
                microsecond=0,
            )

    return slots


def schedule_fixture_times(
    competition_type: str,
    fixtures: Iterable[object],
    start: datetime | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> dict[object, datetime]:
    """
    Assign an allowed kickoff datetime to each fixture.

    The fixture objects are not modified.
    """
    fixture_list = list(fixtures)

    slots = schedule_slots(
        competition_type=competition_type,
        count=len(fixture_list),
        start=start,
        timezone=timezone,
    )

    return dict(
        zip(
            fixture_list,
            slots,
        )
    )


def validate_fixture_datetime(
    competition_type: str,
    scheduled_at: datetime,
) -> None:
    """
    Raise ValueError if a fixture is scheduled on a forbidden day.
    """
    if not is_allowed_day(
        competition_type,
        scheduled_at,
    ):
        day_name = scheduled_at.strftime("%A")

        raise ValueError(
            f"{competition_type} cannot be scheduled on "
            f"{day_name}. "
            f"Allowed weekdays: "
            f"{sorted(allowed_weekdays(competition_type))}"
        )


def competition_day_name(
    competition_type: str,
) -> str:
    """Human-readable calendar rule."""
    competition = competition_type.strip().lower()

    if competition in {
        "league",
        "domestic_league",
        "national_league",
    }:
        return "Friday / Saturday / Sunday"

    if competition in {
        "league_europe",
        "europe",
        "champions_league",
        "europa_league",
        "conference_league",
    }:
        return "Monday / Tuesday"

    if competition in {
        "cup",
        "domestic_cup",
    }:
        return "Wednesday / Thursday"

    raise ValueError(
        f"Unknown competition type: {competition_type}"
    )


def calendar_rules() -> dict[str, str]:
    """
    Return the official V2 weekly competition calendar.
    """
    return {
        "league": competition_day_name("league"),
        "league_europe": competition_day_name(
            "league_europe"
        ),
        "cup": competition_day_name("cup"),
    }


__all__ = [
    "LEAGUE_DAYS",
    "EUROPE_DAYS",
    "CUP_DAYS",
    "MATCH_INTERVAL_MINUTES",
    "allowed_weekdays",
    "is_allowed_day",
    "next_allowed_datetime",
    "schedule_slots",
    "schedule_fixture_times",
    "validate_fixture_datetime",
    "competition_day_name",
    "calendar_rules",
]