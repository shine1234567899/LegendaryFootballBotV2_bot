import asyncio
import random

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import Player


FIRST_NAMES = [
    "Aren", "Bako", "Daren", "Elian", "Faris",
    "Ilan", "Kalen", "Lior", "Marek", "Narek",
    "Oran", "Rayan", "Soren", "Tarek", "Varen",
    "Yanis", "Zarek", "Adem", "Kiro", "Nilo",
    "Arel", "Bren", "Caren", "Dion", "Eren",
    "Felan", "Garen", "Haris", "Iven", "Jarek",
    "Karel", "Luan", "Milan", "Neris", "Orel",
    "Pavel", "Riven", "Salen", "Tarin", "Ulan",
    "Vero", "Waren", "Xaren", "Yoren", "Zilan",
]

LAST_NAMES = [
    "Valen", "Dorin", "Kessan", "Morak", "Silven",
    "Ravel", "Noren", "Darek", "Varek", "Loran",
    "Korin", "Marek", "Sarin", "Toren", "Velar",
    "Narek", "Rovin", "Kalen", "Daven", "Zorin",
    "Arven", "Borin", "Cavel", "Doran", "Evar",
    "Faren", "Gorin", "Havel", "Ivar", "Joren",
    "Kaven", "Lorin", "Maren", "Navel", "Orven",
    "Peren", "Ralen", "Soren", "Tavel", "Uren",
    "Varen", "Welin", "Xorin", "Yaven", "Zoren",
]

COUNTRIES = [
    "Cameroon",
    "France",
    "England",
    "Spain",
    "Italy",
    "Germany",
    "Brazil",
    "Argentina",
    "Portugal",
    "Belgium",
    "Netherlands",
    "Nigeria",
    "Ghana",
    "Morocco",
    "Senegal",
    "Japan",
    "South Korea",
    "Canada",
    "Mexico",
    "USA",
]

POSITIONS = {
    "GK": 80,
    "DEF": 170,
    "MID": 170,
    "ATT": 80,
}


def generate_players():
    players = []
    used_names = set()

    for position, amount in POSITIONS.items():
        while sum(1 for p in players if p["position"] == position) < amount:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"

            if name in used_names:
                continue

            used_names.add(name)

            age = random.randint(17, 34)

            # Joueurs de départ volontairement moyens.
            overall = random.randint(58, 76)

            potential = min(
                85,
                overall + random.randint(3, 12)
            )

            value = (
                overall
                * overall
                * random.randint(5000, 9000)
            )

            players.append(
                {
                    "name": name,
                    "country": random.choice(COUNTRIES),
                    "position": position,
                    "age": age,
                    "overall": overall,
                    "potential": potential,
                    "value": value,
                }
            )

    random.shuffle(players)
    return players


async def main():
    players = generate_players()

    async with AsyncSessionLocal() as session:
        added = 0

        for data in players:
            result = await session.execute(
                select(Player).where(
                    Player.name == data["name"]
                )
            )

            existing = result.scalar_one_or_none()

            if existing is not None:
                existing.starter_pool = True
                continue

            session.add(
                Player(
                    name=data["name"],
                    country=data["country"],
                    position=data["position"],
                    age=data["age"],
                    overall=data["overall"],
                    potential=data["potential"],
                    value=data["value"],
                    starter_pool=True,
                )
            )

            added += 1

        await session.commit()

    print(f"✅ Fictional players added: {added}")


if __name__ == "__main__":
    asyncio.run(main())