from database.database import AsyncSessionLocal
from database.models import Club, ClubPlayer, SavedLineup, SavedLineupPlayer
from sqlalchemy import select, delete


async def cleanup_invalid_lineup_players():
    """
    Removes stale lineup entries.

    Rule:
    A player may only appear in a SavedLineup belonging to the club that
    currently owns that player through an active ClubPlayer row.

    This is safer than relying on historical Trade sender/receiver data,
    especially when a player has been traded more than once.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SavedLineupPlayer, SavedLineup)
            .join(
                SavedLineup,
                SavedLineup.id == SavedLineupPlayer.saved_lineup_id,
            )
        )
        rows = result.all()

        removed = 0

        for lineup_player, saved_lineup in rows:
            current_owner_club_id = await session.scalar(
                select(ClubPlayer.club_id).where(
                    ClubPlayer.player_id == lineup_player.player_id,
                    ClubPlayer.is_current.is_(True),
                ).limit(1)
            )

            # No active ownership or lineup belongs to another club:
            # remove only the lineup entry, never the squad ownership.
            if (
                current_owner_club_id is None
                or current_owner_club_id != saved_lineup.club_id
            ):
                await session.delete(lineup_player)
                removed += 1

        await session.commit()

        print(
            f"✅ Lineup cleanup terminé : "
            f"{removed} joueur(s) retiré(s) des anciens lineups."
        )
        print(
            "✅ Les ClubPlayer n'ont pas été supprimés."
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(cleanup_invalid_lineup_players())
