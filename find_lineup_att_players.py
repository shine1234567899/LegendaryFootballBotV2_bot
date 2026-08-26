from database.database import AsyncSessionLocal
from database.models import Player, Club, ClubPlayer, SavedLineup, SavedLineupPlayer
from sqlalchemy import select


async def find_att_lineup_players():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                SavedLineupPlayer,
                SavedLineup,
                Club,
                Player,
            )
            .join(
                SavedLineup,
                SavedLineup.id == SavedLineupPlayer.saved_lineup_id,
            )
            .join(
                Club,
                Club.id == SavedLineup.club_id,
            )
            .join(
                Player,
                Player.id == SavedLineupPlayer.player_id,
            )
            .where(
                SavedLineupPlayer.position.ilike("ATT")
            )
            .order_by(Player.overall.desc())
        )

        rows = result.all()

        print("=== ATT PLAYERS IN SAVED LINEUPS ===")

        if not rows:
            print("❌ Aucun ATT dans les saved lineups.")
            return

        for saved_player, lineup, club, player in rows:
            ownership = await session.scalar(
                select(ClubPlayer).where(
                    ClubPlayer.player_id == player.id,
                    ClubPlayer.is_current.is_(True),
                ).limit(1)
            )

            owner_club = None
            if ownership:
                owner_club = await session.scalar(
                    select(Club).where(Club.id == ownership.club_id)
                )

            print(
                f"PLAYER ID={player.id} | NAME={player.name} | "
                f"OVR={player.overall} | "
                f"LINEUP CLUB={club.name} (ID={club.id}) | "
                f"FORMATION={lineup.formation} | SLOT={saved_player.slot_id} | "
                f"CURRENT OWNER={owner_club.name if owner_club else 'NONE'}"
            )


if __name__ == "__main__":
    import asyncio
    asyncio.run(find_att_lineup_players())
