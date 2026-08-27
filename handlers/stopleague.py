from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, update as sql_update

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import (
    League,
    Season,
    Fixture,
    Match,
    LeagueSeasonClub,
)


async def stopleague(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner command:

        /stopleague <league name>

    Stops the league for the current active season.

    Existing completed/history matches are preserved.
    Future scheduled fixtures are cancelled.
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

    if not context.args:
        await message.reply_text(
            "🏆 𝐒𝐓𝐎𝐏 𝐋𝐄𝐀𝐆𝐔𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Use:\n"
            "/stopleague <league name>\n\n"
            "Example:\n"
            "/stopleague Premier League"
        )
        return

    target = " ".join(context.args).strip()

    async with AsyncSessionLocal() as session:
        league = await session.scalar(
            select(League).where(
                League.name.ilike(target)
            )
        )

        if league is None:
            await message.reply_text(
                f"❌ League not found: {target}"
            )
            return

        season = await session.scalar(
            select(Season)
            .where(
                Season.is_active.is_(True)
            )
            .order_by(
                Season.number.desc()
            )
        )

        league.status = "stopped"

        cancelled = 0

        if season is not None:
            club_ids_query = select(
                LeagueSeasonClub.club_id
            ).where(
                LeagueSeasonClub.league_id == league.id,
                LeagueSeasonClub.season_id == season.id,
            )

            result = await session.execute(
                select(Fixture, Match)
                .join(
                    Match,
                    Match.fixture_id == Fixture.id,
                )
                .where(
                    Fixture.season_id == season.id,
                    Fixture.competition_type == "league",
                    Match.status.in_(
                        ["scheduled", "not_started"]
                    ),
                    (
                        Fixture.home_club_id.in_(club_ids_query)
                        | Fixture.away_club_id.in_(club_ids_query)
                    ),
                )
            )


            rows = list(result.all())
            for fixture, match in rows:
                match.status = "cancelled"
                fixture.status = "cancelled"
                cancelled += 1

        await session.commit()

    await message.reply_text(
        "🛑 𝐋𝐄𝐀𝐆𝐔𝐄 𝐒𝐓𝐎𝐏𝐏𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 League : {league.name}\n"
        f"🚫 Future matches cancelled : {cancelled}\n\n"
        "✅ Finished matches and standings history were preserved."
    )


stopleague_handler = CommandHandler(
    "stopleague",
    stopleague,
)
