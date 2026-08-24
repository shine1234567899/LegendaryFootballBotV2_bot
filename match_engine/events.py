import random
from dataclasses import dataclass
from typing import Optional


# ==========================================================
# EVENT TYPES
# ==========================================================

PASS = "PASS"
BUILD_UP = "BUILD_UP"
DRIBBLE = "DRIBBLE"
CROSS = "CROSS"
SHOT = "SHOT"
GOAL = "GOAL"
FOUL = "FOUL"
CORNER = "CORNER"
COUNTER_ATTACK = "COUNTER_ATTACK"
SAVE = "SAVE"
INTERCEPTION = "INTERCEPTION"
TACKLE = "TACKLE"
CLEARANCE = "CLEARANCE"


# ==========================================================
# ACTION
# ==========================================================

@dataclass
class Action:
    event_type: str
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    secondary_player_id: Optional[int] = None
    secondary_player_name: Optional[str] = None
    description: str = ""
    metadata: dict = None

    def __post_init__(self):

        if self.metadata is None:
            self.metadata = {}


# ==========================================================
# EVENT GENERATOR
# ==========================================================

class EventGenerator:

    def __init__(
        self,
        attacking_team,
        defending_team,
    ):

        self.attacking_team = attacking_team
        self.defending_team = defending_team

    # ======================================================
    # PLAYER FILTER
    # ======================================================

    def players(
        self,
        team,
        positions,
    ):

        return [
            player
            for player in team.players
            if str(
                getattr(
                    player,
                    "position",
                    "",
                )
            ).upper()
            in positions
        ]

    # ======================================================
    # RANDOM PLAYER
    # ======================================================

    def random_player(
        self,
        team,
        positions,
    ):

        candidates = self.players(
            team,
            positions,
        )

        if not candidates:
            return None

        return random.choice(
            candidates
        )

    # ======================================================
    # WEIGHTED ACTION
    # ======================================================

    def choose_action(self):

        actions = [
            PASS,
            PASS,
            PASS,
            BUILD_UP,
            BUILD_UP,
            DRIBBLE,
            DRIBBLE,
            CROSS,
            SHOT,
            FOUL,
            CORNER,
            COUNTER_ATTACK,
            INTERCEPTION,
            TACKLE,
            CLEARANCE,
        ]

        return random.choice(actions)

    # ======================================================
    # GENERATE
    # ======================================================

    def generate(self):

        action_type = (
            self.choose_action()
        )

        # --------------------------------------------------
        # PASS
        # --------------------------------------------------

        if action_type == PASS:

            passer = self.random_player(
                self.attacking_team,
                {"MID", "ATT", "DEF"},
            )

            receiver = self.random_player(
                self.attacking_team,
                {"MID", "ATT"},
            )

            if not passer:
                return None

            return Action(
                event_type=PASS,
                player_id=passer.id,
                player_name=passer.name,
                secondary_player_id=(
                    receiver.id
                    if receiver
                    else None
                ),
                secondary_player_name=(
                    receiver.name
                    if receiver
                    else None
                ),
                description=(
                    f"{passer.name} "
                    "plays a pass."
                ),
            )

        # --------------------------------------------------
        # BUILD UP
        # --------------------------------------------------

        if action_type == BUILD_UP:

            player = self.random_player(
                self.attacking_team,
                {"DEF", "MID"},
            )

            if not player:
                return None

            return Action(
                event_type=BUILD_UP,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    "helps build the attack."
                ),
            )

        # --------------------------------------------------
        # DRIBBLE
        # --------------------------------------------------

        if action_type == DRIBBLE:

            player = self.random_player(
                self.attacking_team,
                {"MID", "ATT"},
            )

            if not player:
                return None

            successful = (
                random.random() < 0.62
            )

            return Action(
                event_type=DRIBBLE,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    + (
                        "beats his opponent."
                        if successful
                        else "loses the ball."
                    )
                ),
                metadata={
                    "successful": successful,
                },
            )

        # --------------------------------------------------
        # CROSS
        # --------------------------------------------------

        if action_type == CROSS:

            player = self.random_player(
                self.attacking_team,
                {"MID", "ATT"},
            )

            if not player:
                return None

            return Action(
                event_type=CROSS,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    "whips a cross into the box."
                ),
            )

        # --------------------------------------------------
        # SHOT
        # --------------------------------------------------

        if action_type == SHOT:

            shooter = self.random_player(
                self.attacking_team,
                {"ATT", "MID"},
            )

            goalkeeper = self.random_player(
                self.defending_team,
                {"GK"},
            )

            if not shooter:
                return None

            return Action(
                event_type=SHOT,
                player_id=shooter.id,
                player_name=shooter.name,
                secondary_player_id=(
                    goalkeeper.id
                    if goalkeeper
                    else None
                ),
                secondary_player_name=(
                    goalkeeper.name
                    if goalkeeper
                    else None
                ),
                description=(
                    f"{shooter.name} "
                    "takes a shot."
                ),
            )

        # --------------------------------------------------
        # FOUL
        # --------------------------------------------------

        if action_type == FOUL:

            player = self.random_player(
                self.attacking_team,
                {"DEF", "MID"},
            )

            if not player:
                return None

            yellow_card = (
                random.random() < 0.14
            )

            return Action(
                event_type=FOUL,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    "commits a foul."
                ),
                metadata={
                    "yellow_card": yellow_card,
                },
            )

        # --------------------------------------------------
        # CORNER
        # --------------------------------------------------

        if action_type == CORNER:

            player = self.random_player(
                self.attacking_team,
                {"MID", "ATT"},
            )

            if not player:
                return None

            return Action(
                event_type=CORNER,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{self.attacking_team.name} "
                    "wins a corner."
                ),
            )

        # --------------------------------------------------
        # COUNTER ATTACK
        # --------------------------------------------------

        if action_type == COUNTER_ATTACK:

            player = self.random_player(
                self.attacking_team,
                {"MID", "ATT"},
            )

            if not player:
                return None

            return Action(
                event_type=COUNTER_ATTACK,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{self.attacking_team.name} "
                    "launches a counter attack!"
                ),
            )

        # --------------------------------------------------
        # INTERCEPTION
        # --------------------------------------------------

        if action_type == INTERCEPTION:

            player = self.random_player(
                self.defending_team,
                {"DEF", "MID"},
            )

            if not player:
                return None

            return Action(
                event_type=INTERCEPTION,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    "intercepts the ball."
                ),
            )

        # --------------------------------------------------
        # TACKLE
        # --------------------------------------------------

        if action_type == TACKLE:

            player = self.random_player(
                self.defending_team,
                {"DEF", "MID"},
            )

            if not player:
                return None

            successful = (
                random.random() < 0.68
            )

            return Action(
                event_type=TACKLE,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    + (
                        "wins the tackle."
                        if successful
                        else "misses the tackle."
                    )
                ),
                metadata={
                    "successful": successful,
                },
            )

        # --------------------------------------------------
        # CLEARANCE
        # --------------------------------------------------

        if action_type == CLEARANCE:

            player = self.random_player(
                self.defending_team,
                {"DEF", "GK"},
            )

            if not player:
                return None

            return Action(
                event_type=CLEARANCE,
                player_id=player.id,
                player_name=player.name,
                description=(
                    f"{player.name} "
                    "clears the danger."
                ),
            )

        return None