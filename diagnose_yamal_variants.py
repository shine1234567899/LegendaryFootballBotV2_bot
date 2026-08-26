from database.database import AsyncSessionLocal
from database.models import Player, ClubPlayer, Club, SavedLineup, SavedLineupPlayer
from sqlalchemy import select


async def diagnose_yamal_variants():
    async with AsyncSessionLocal() as session:
        # Search broad variants, case-insensitive.
        result = await session.execute(
            select(Player).where(
                Player.name.ilike("%yamal%"),
            )
        )
        players = result.scalars().all()

        if not players:
            result = await session.execute(
                select(Player).where(
                    Player.name.ilike("%lamine%"),
                )
            )
            players = result.scalars().all()

        if not players:
            print("❌ Aucun joueur trouvé avec Yamal/Lamine.")
            print("➡️ Affichage des 30 premiers joueurs de la base :")

            result = await session.execute(
                select(Player)
                .order_by(Player.id)
                .limit(30)
            )
            for player in result.scalars().all():
                print(f"ID={player.id} | NAME={player.name}")
            return

        for player in players:
            print("\n================================")
            print(f"PLAYER NAME : {player.name}")
            print(f"PLAYER ID   : {player.id}")
            print("================================")

            result = await session.execute(
                select(ClubPlayer, Club)
                .join(Club, Club.id == ClubPlayer.club_id)
                .where(
                    ClubPlayer.player_id == player.id,
                    ClubPlayer.is_current.is_(True),
                )
            )
            ownerships = result.all()

            if not ownerships:
                print("CURRENT CLUB : ❌ aucun")
            else:
                for ownership, club in ownerships:
                    print(
                        f"CURRENT CLUB : {club.name} "
                        f"(club_id={club.id}, ownership_id={ownership.id})"
                    )

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

            if not lineups:
                print("SAVED LINEUPS : aucun")
            else:
                print("SAVED LINEUPS :")
                for saved_player, lineup, club in lineups:
                    print(
                        f"  Club={club.name} (club_id={club.id})"
                        f" | formation={lineup.formation}"
                        f" | slot={saved_player.slot_id}"
                        f" | lineup_id={lineup.id}"
                    )

        print("\n✅ Diagnostic terminé. Aucune donnée modifiée.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose_yamal_variants())
