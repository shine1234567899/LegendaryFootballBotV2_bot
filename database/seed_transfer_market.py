import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Player


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "fc26_players.csv"

TARGET_TRANSFER_PLAYERS = 500


async def seed_transfer_market():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔥 TRANSFER MARKET SEED")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not CSV_FILE.exists():
        print(f"❌ CSV not found: {CSV_FILE}")
        return

    async with AsyncSessionLocal() as session:

        # --------------------------------------------------
        # Joueurs Transfer Market déjà présents
        # --------------------------------------------------

        result = await session.execute(
            select(Player).where(
                Player.starter_pool.is_(False)
            )
        )

        existing_players = result.scalars().all()

        existing_names = {
            player.name.strip().casefold()
            for player in existing_players
        }

        current_count = len(existing_players)

        print(
            f"Existing transfer players : "
            f"{current_count}"
        )

        if current_count >= TARGET_TRANSFER_PLAYERS:
            print(
                "✅ Transfer Market pool is already "
                f"complete ({current_count}/{TARGET_TRANSFER_PLAYERS})."
            )
            return

        # --------------------------------------------------
        # Lecture du CSV
        # --------------------------------------------------

        with open(
            CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            rows = list(reader)

        added = 0
        skipped = 0

        remaining = (
            TARGET_TRANSFER_PLAYERS
            - current_count
        )

        # --------------------------------------------------
        # Import
        # --------------------------------------------------

        for row in rows:

            if added >= remaining:
                break

            name = row["name"].strip()

            if not name:
                skipped += 1
                continue

            # Empêche les doublons
            if name.casefold() in existing_names:
                skipped += 1
                continue

            try:
                country = row["country"].strip()
                position = row["position"].strip()
                age = int(row["age"])
                overall = int(row["overall"])
                potential = int(row["potential"])
                value = int(row["value"])
            except (
                KeyError,
                ValueError,
                TypeError,
            ):
                skipped += 1
                continue

            player = Player(
                name=name,
                country=country,
                position=position,
                age=age,
                overall=overall,
                potential=potential,
                value=value,
                image_file_id=None,
                starter_pool=False,
            )

            session.add(player)

            existing_names.add(
                name.casefold()
            )

            added += 1

        await session.commit()

        # --------------------------------------------------
        # Vérification finale
        # --------------------------------------------------

        result = await session.execute(
            select(Player).where(
                Player.starter_pool.is_(False)
            )
        )

        final_count = len(
            result.scalars().all()
        )

    print(
        f"Players added    : {added}"
    )

    print(
        f"Players skipped  : {skipped}"
    )

    print(
        f"Transfer pool    : "
        f"{final_count}/{TARGET_TRANSFER_PLAYERS}"
    )

    if final_count >= TARGET_TRANSFER_PLAYERS:
        print(
            "✅ Transfer Market pool COMPLETE"
        )
    else:
        print(
            "⚠️ CSV does not contain enough "
            "new players to reach 500."
        )

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(
        seed_transfer_market()
    )