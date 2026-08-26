from database.database import AsyncSessionLocal
from database.models import Player, Club, ClubPlayer, SavedLineup, SavedLineupPlayer
from sqlalchemy import select


async def diagnose_yamal_links():
    async with AsyncSessionLocal() as session:
        # Show every Yamal-like player record.
        result = await session.execute(
            select(Player).where(
                (Player.name.ilike("%yamal%")) |
                (Player.name.ilike("%lamine%"))
            )
        )
        players = result.scalars().all()

        print("=== PLAYER RECORDS ===")
        if not players:
            print("❌ Aucun Yamal/Lamine.")
            return

        for player in players:
            print(
                f"ID={player.id} | NAME={player.name} | "
                f"POSITION={player.position} | OVR={player.overall}"
            )

            # Current squad ownership
            result = await session.execute(
                select(ClubPlayer, Club)
                .join(Club, Club.id == ClubPlayer.club_id)
                .where(ClubPlayer.player_id == player.id)
            )
            ownerships = result.all()

            if ownerships:
                for ownership, club in ownerships:
                    print(
                        f"  CLUBPLAYER id={ownership.id} | "
                        f"club={club.name} ({club.id}) | "
                        f"is_current={ownership.is_current}"
                    )
            else:
                print("  CLUBPLAYER : aucun")

            # Saved lineup references
            result = await session.execute(
                select(SavedLineupPlayer, SavedLineup, Club)
                .join(
                    SavedLineup,
                    SavedLineup.id == SavedLineupPlayer.saved_lineup_id,
                )
                .join(
                    Club,
                    Club.id == SavedLineup.club_id,
                )
                .where(
                    SavedLineupPlayer.player_id == player.id
                )
            )
            lineups = result.all()

            if lineups:
                for saved_player, lineup, club in lineups:
                    print(
                        f"  LINEUP id={lineup.id} | club={club.name} "
                        f"({club.id}) | formation={lineup.formation} | "
                        f"slot={saved_player.slot_id}"
                    )
            else:
                print("  LINEUP : aucun")

        print("\n✅ Diagnostic terminé. Rien n'a été modifié.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose_yamal_links())
