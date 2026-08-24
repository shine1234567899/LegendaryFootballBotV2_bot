from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from database.database import AsyncSessionLocal

from database.models import (
    Club,
    Player,
    ClubPlayer,
    Season,
    Fixture,
    Match,
    Lineup,
    LineupPlayer,
)

from .engine import MatchTeam


# ==========================================================
# FRIENDLY ERROR
# ==========================================================

class FriendlyError(Exception):
    pass


# ==========================================================
# FRIENDLY PLAYER
# ==========================================================

@dataclass
class FriendlyPlayer:

    player: Player
    position: str
    shirt_number: int
    is_captain: bool = False


# ==========================================================
# FRIENDLY TEAM
# ==========================================================

@dataclass
class FriendlyTeam:

    club: Club
    players: list
    formation: str

    def to_match_team(self):

        # Le moteur actuel utilise directement
        # les objets Player.

        return MatchTeam(
            club_id=self.club.id,
            name=self.club.name,
            players=[
                item.player
                for item in self.players
            ],
            formation=self.formation,
        )


# ==========================================================
# GET CLUB BY OWNER
# ==========================================================

async def get_club_by_owner(
    user_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club).where(
                Club.owner_id == user_id
            )
        )

        return result.scalar_one_or_none()


# ==========================================================
# GET CLUB BY ID
# ==========================================================

async def get_club_by_id(
    club_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Club).where(
                Club.id == club_id
            )
        )

        return result.scalar_one_or_none()


# ==========================================================
# GET ACTIVE SEASON
# ==========================================================

async def get_active_season():

    async with AsyncSessionLocal() as session:

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


# ==========================================================
# GET CURRENT PLAYERS
# ==========================================================

async def get_current_players(
    club_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Player)
            .join(
                ClubPlayer,
                ClubPlayer.player_id
                == Player.id,
            )
            .where(
                ClubPlayer.club_id == club_id,
                ClubPlayer.is_current.is_(True),
            )
            .order_by(
                Player.overall.desc()
            )
        )

        return list(
            result.scalars().all()
        )


# ==========================================================
# VALIDATE LINEUP
# ==========================================================

def validate_lineup(
    players: list,
    formation: str,
):

    if not formation:

        raise FriendlyError(
            "Formation is missing."
        )

    if len(players) != 11:

        raise FriendlyError(
            "Lineup must contain exactly "
            f"11 players. Current: {len(players)}."
        )

    ids = set()

    goalkeepers = 0

    for item in players:

        player = (
            item.player
            if isinstance(
                item,
                FriendlyPlayer,
            )
            else item
        )

        if player.id in ids:

            raise FriendlyError(
                f"Player {player.name} "
                "appears more than once."
            )

        ids.add(
            player.id
        )

        position = str(
            getattr(
                item,
                "position",
                getattr(
                    player,
                    "position",
                    "",
                ),
            )
        ).upper()

        if position == "GK":

            goalkeepers += 1

    if goalkeepers != 1:

        raise FriendlyError(
            "Lineup must contain exactly "
            "one goalkeeper."
        )


# ==========================================================
# BUILD FRIENDLY TEAM
# ==========================================================

async def build_friendly_team(
    club_id: int,
    formation: str,
    lineup_players: list,
):

    current_players = (
        await get_current_players(
            club_id
        )
    )

    players_by_id = {
        player.id: player
        for player in current_players
    }

    selected = []

    for item in lineup_players:

        player_id = item.get(
            "id"
        )

        player = players_by_id.get(
            player_id
        )

        if player is None:

            raise FriendlyError(
                f"Player {player_id} "
                "does not belong to this club."
            )

        position = str(
            item.get(
                "position",
                player.position,
            )
        ).upper()

        real_position = str(
            player.position
        ).upper()

        if position != real_position:

            raise FriendlyError(
                f"{player.name} is "
                f"{real_position}, "
                f"not {position}."
            )

        selected.append(
            FriendlyPlayer(
                player=player,
                position=position,
                shirt_number=item.get(
                    "shirt_number",
                    len(selected) + 1,
                ),
                is_captain=item.get(
                    "is_captain",
                    False,
                ),
            )
        )

    validate_lineup(
        selected,
        formation,
    )

    club = await get_club_by_id(
        club_id
    )

    if club is None:

        raise FriendlyError(
            "Club not found."
        )

    return FriendlyTeam(
        club=club,
        players=selected,
        formation=formation,
    )


# ==========================================================
# CREATE FRIENDLY MATCH
# ==========================================================

# ==========================================================
# CREATE FRIENDLY MATCH
# ==========================================================

async def create_friendly_match(
    home_club_id: int,
    away_club_id: int,
):

    if (
        home_club_id
        == away_club_id
    ):

        raise FriendlyError(
            "A club cannot play against itself."
        )

    async with AsyncSessionLocal() as session:

        # --------------------------------------------------
        # FRIENDLY DOES NOT REQUIRE AN ACTIVE SEASON
        # --------------------------------------------------
        #
        # We try to use the current active season if one
        # exists, but a friendly can still be created
        # without one.
        #
        # --------------------------------------------------

        result = await session.execute(
            select(Season)
            .where(
                Season.is_active.is_(True)
            )
            .order_by(
                Season.number.desc()
            )
        )

        season = (
            result.scalars().first()
        )

        # --------------------------------------------------
        # CREATE FIXTURE
        # --------------------------------------------------

        fixture = Fixture(
            season_id=(
                season.id
                if season is not None
                else None
            ),
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            scheduled_at=datetime.utcnow(),
            competition_type="friendly",
            round_number=None,
            status="scheduled",
        )

        session.add(
            fixture
        )

        await session.flush()

        # --------------------------------------------------
        # CREATE MATCH
        # --------------------------------------------------

        match = Match(
            fixture_id=fixture.id,
            home_score=0,
            away_score=0,
            minute=0,
            status="not_started",
            possession_home=50,
            possession_away=50,
            stats={},
        )

        session.add(
            match
        )

        await session.flush()

        await session.commit()

        return (
            fixture.id,
            match.id,
            season.id
            if season is not None
            else None,
        )

# ==========================================================
# SAVE MATCH LINEUP
# ==========================================================

async def save_match_lineup(
    match_id: int,
    club_id: int,
    formation: str,
    lineup_players: list,
):

    team = await build_friendly_team(
        club_id,
        formation,
        lineup_players,
    )

    async with AsyncSessionLocal() as session:

        match = await session.get(
            Match,
            match_id,
        )

        if match is None:

            raise FriendlyError(
                "Match not found."
            )

        result = await session.execute(
            select(Lineup).where(
                Lineup.match_id == match_id,
                Lineup.club_id == club_id,
            )
        )

        lineup = (
            result.scalar_one_or_none()
        )

        if lineup is None:

            lineup = Lineup(
                match_id=match_id,
                club_id=club_id,
                formation=formation,
            )

            session.add(
                lineup
            )

            await session.flush()

        else:

            lineup.formation = formation

            result = await session.execute(
                select(LineupPlayer).where(
                    LineupPlayer.lineup_id
                    == lineup.id
                )
            )

            old_players = list(
                result.scalars().all()
            )

            for old_player in old_players:

                await session.delete(
                    old_player
                )

            await session.flush()

        # --------------------------------------------------
        # SAVE STARTERS
        # --------------------------------------------------

        for item in team.players:

            lineup_player = LineupPlayer(
                lineup_id=lineup.id,
                player_id=item.player.id,
                position=item.position,
                shirt_number=item.shirt_number,
                is_starting=True,
                is_captain=item.is_captain,
            )

            session.add(
                lineup_player
            )

        await session.commit()

        return lineup.id


# ==========================================================
# LOAD SAVED MATCH LINEUP
# ==========================================================

async def load_match_lineup(
    match_id: int,
    club_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Lineup).where(
                Lineup.match_id == match_id,
                Lineup.club_id == club_id,
            )
        )

        lineup = (
            result.scalar_one_or_none()
        )

        if lineup is None:

            raise FriendlyError(
                "No lineup found for this match."
            )

        result = await session.execute(
            select(
                Player,
                LineupPlayer.position,
                LineupPlayer.shirt_number,
                LineupPlayer.is_captain,
            )
            .join(
                LineupPlayer,
                LineupPlayer.player_id
                == Player.id,
            )
            .where(
                LineupPlayer.lineup_id
                == lineup.id,
                LineupPlayer.is_starting.is_(True),
            )
            .order_by(
                LineupPlayer.id
            )
        )

        rows = result.all()

        if len(rows) != 11:

            raise FriendlyError(
                "Saved lineup must contain "
                "exactly 11 starters."
            )

        players = []

        for (
            player,
            position,
            shirt_number,
            is_captain,
        ) in rows:

            players.append(
                FriendlyPlayer(
                    player=player,
                    position=str(
                        position
                    ).upper(),
                    shirt_number=shirt_number,
                    is_captain=is_captain,
                )
            )

        validate_lineup(
            players,
            lineup.formation,
        )

        club = await get_club_by_id(
            club_id
        )

        if club is None:

            raise FriendlyError(
                "Club not found."
            )

        return FriendlyTeam(
            club=club,
            players=players,
            formation=lineup.formation,
        )


# ==========================================================
# BUILD MATCH TEAMS
# ==========================================================

async def build_match_teams(
    match_id: int,
    home_club_id: int,
    away_club_id: int,
):

    home_team = (
        await load_match_lineup(
            match_id,
            home_club_id,
        )
    )

    away_team = (
        await load_match_lineup(
            match_id,
            away_club_id,
        )
    )

    return (
        home_team.to_match_team(),
        away_team.to_match_team(),
    )