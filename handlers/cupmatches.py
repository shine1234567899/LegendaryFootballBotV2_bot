from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Fixture, Match, Club


# ==========================================================
# CUP MATCHES
# ==========================================================
#
# /cupmatches
#
# Uses the real V2 models:
#   Fixture:
#       home_club_id
#       away_club_id
#       scheduled_at
#       competition_type
#       round_number
#       status
#
#   Match:
#       fixture_id
#       home_score
#       away_score
#       status
#
# No non-existing model fields are used.
# ==========================================================


async def cupmatches(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if message is None:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                Fixture,
                Match,
                Club,
            )
            .join(
                Match,
                Match.fixture_id == Fixture.id,
            )
            .join(
                Club,
                Club.id == Fixture.home_club_id,
            )
            .where(
                Fixture.competition_type == "cup"
            )
            .order_by(
                Fixture.scheduled_at.asc(),
                Fixture.round_number.asc(),
                Fixture.id.asc(),
            )
        )

        rows = list(result.all())

        # Load away clubs separately so we do not depend on
        # SQLAlchemy relationship fields that are not present
        # in the supplied models.
        away_ids = {
            fixture.away_club_id
            for fixture, match, home_club in rows
        }

        away_clubs = {}

        if away_ids:
            away_result = await session.execute(
                select(Club).where(
                    Club.id.in_(away_ids)
                )
            )

            away_clubs = {
                club.id: club
                for club in away_result.scalars().all()
            }

    if not rows:
        await message.reply_text(
            (
                "🏆 𝐂𝐔𝐏 𝐌𝐀𝐓𝐂𝐇𝐄𝐒\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📭 No Cup matches have been scheduled yet."
            )
        )
        return

    lines = [
        "🏆 𝐂𝐔𝐏 𝐌𝐀𝐓𝐂𝐇𝐄𝐒",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    current_round = None

    for fixture, match, home_club in rows:
        if fixture.round_number != current_round:
            current_round = fixture.round_number

            if current_round is not None:
                lines.extend(
                    [
                        "",
                        f"🏆 𝐑𝐎𝐔𝐍𝐃 {current_round}",
                        "────────────────────",
                    ]
                )

        away_club = away_clubs.get(
            fixture.away_club_id
        )

        home_name = (
            home_club.name
            if home_club is not None
            else f"Club #{fixture.home_club_id}"
        )

        away_name = (
            away_club.name
            if away_club is not None
            else f"Club #{fixture.away_club_id}"
        )

        date_text = fixture.scheduled_at.strftime(
            "%d/%m/%Y"
        )
        time_text = fixture.scheduled_at.strftime(
            "%H:%M"
        )

        status = (
            match.status
            if match is not None
            else fixture.status
        )

        if match is not None:
            score = (
                f"{match.home_score}"
                f" - "
                f"{match.away_score}"
            )
        else:
            score = "—"

        lines.append(
            (
                f"⚽ {home_name} "
                f"vs {away_name}\n"
                f"📊 {score}   •   {status}\n"
                f"📅 {date_text}   ⏰ {time_text}"
            )
        )

    lines.extend(
        [
            "",
            "📆 Cup days: Wednesday / Thursday",
        ]
    )

    # Telegram messages have a practical size limit.
    # Split into several messages instead of failing on a
    # large Cup.
    chunk = ""

    for line in lines:
        candidate = (
            f"{chunk}\n{line}"
            if chunk
            else line
        )

        if len(candidate) > 3800:
            await message.reply_text(chunk)
            chunk = line
        else:
            chunk = candidate

    if chunk:
        await message.reply_text(chunk)


cupmatches_handler = CommandHandler(
    "cupmatches",
    cupmatches,
)