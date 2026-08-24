from dataclasses import dataclass
from typing import Optional

from .engine import MatchTeam, MatchEvent


# ==========================================================
# FIELD
# ==========================================================

FIELD_WIDTH = 1280
FIELD_HEIGHT = 720

FIELD_LEFT = 80
FIELD_RIGHT = 1200

FIELD_TOP = 80
FIELD_BOTTOM = 640


# ==========================================================
# POSITION
# ==========================================================

@dataclass
class Position:

    x: float
    y: float


# ==========================================================
# VISUAL PLAYER
# ==========================================================

@dataclass
class VisualPlayer:

    player_id: int
    name: str
    team_id: int

    position: Position

    shirt_number: int = 0

    role: str = ""

    active: bool = True


# ==========================================================
# BALL
# ==========================================================

@dataclass
class Ball:

    position: Position

    target: Optional[Position] = None

    moving: bool = False


# ==========================================================
# CAMERA
# ==========================================================

@dataclass
class Camera:

    x: float = 640
    y: float = 360

    zoom: float = 1.0

    target_x: float = 640
    target_y: float = 360


# ==========================================================
# MATCH VISUAL STATE
# ==========================================================

class MatchVisualState:

    def __init__(
        self,
        home_team: MatchTeam,
        away_team: MatchTeam,
    ):

        self.home_team = home_team
        self.away_team = away_team

        self.minute = 0

        self.home_score = 0
        self.away_score = 0

        self.players = []

        self.ball = Ball(
            position=Position(
                640,
                360,
            )
        )

        self.camera = Camera()

        self.last_event = None

        self._create_players()

    # ======================================================
    # CREATE PLAYERS
    # ======================================================

    def _create_players(self):

        self.players.clear()

        self._create_team_players(
            self.home_team,
            True,
        )

        self._create_team_players(
            self.away_team,
            False,
        )

    # ======================================================
    # CREATE TEAM
    # ======================================================

    def _create_team_players(
        self,
        team: MatchTeam,
        home: bool,
    ):

        positions = self._formation_positions(
            team.formation,
            home,
        )

        # On prend exactement les 11
        # titulaires envoyés au moteur.

        selected_players = team.players[:11]

        for index, player in enumerate(
            selected_players
        ):

            if index >= len(
                positions
            ):
                break

            x, y, role = positions[
                index
            ]

            self.players.append(
                VisualPlayer(
                    player_id=player.id,
                    name=player.name,
                    team_id=team.club_id,
                    position=Position(
                        x,
                        y,
                    ),
                    shirt_number=index + 1,
                    role=role,
                )
            )

    # ======================================================
    # FORMATION POSITIONS
    # ======================================================

    def _formation_positions(
        self,
        formation: str,
        home: bool,
    ):

        formation = (
            str(
                formation
            )
            .strip()
            .lower()
        )

        formations = {

            # ----------------------------------------------
            # 4-3-3
            # ----------------------------------------------

            "4-3-3": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 4),
                ("MID", 0.48, 3),
                ("ATT", 0.73, 3),
            ],

            # ----------------------------------------------
            # 4-4-2
            # ----------------------------------------------

            "4-4-2": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 4),
                ("MID", 0.48, 4),
                ("ATT", 0.72, 2),
            ],

            # ----------------------------------------------
            # 3-5-2
            # ----------------------------------------------

            "3-5-2": [
                ("GK", 0.08, 1),
                ("DEF", 0.28, 3),
                ("MID", 0.50, 5),
                ("ATT", 0.73, 2),
            ],

            # ----------------------------------------------
            # 4-2-3-1
            # ----------------------------------------------

            "4-2-3-1": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 4),
                ("MID", 0.43, 2),
                ("MID", 0.58, 3),
                ("ATT", 0.75, 1),
            ],

            # ----------------------------------------------
            # 3-4-3
            # ----------------------------------------------

            "3-4-3": [
                ("GK", 0.08, 1),
                ("DEF", 0.28, 3),
                ("MID", 0.50, 4),
                ("ATT", 0.74, 3),
            ],

            # ----------------------------------------------
            # 5-3-2
            # ----------------------------------------------

            "5-3-2": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 5),
                ("MID", 0.50, 3),
                ("ATT", 0.74, 2),
            ],

            # ----------------------------------------------
            # 5-4-1
            # ----------------------------------------------

            "5-4-1": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 5),
                ("MID", 0.50, 4),
                ("ATT", 0.75, 1),
            ],

            # ----------------------------------------------
            # 4-5-1
            # ----------------------------------------------

            "4-5-1": [
                ("GK", 0.08, 1),
                ("DEF", 0.25, 4),
                ("MID", 0.52, 5),
                ("ATT", 0.76, 1),
            ],
        }

        rows = formations.get(
            formation
        )

        # Formation inconnue :
        # retour sécurisé en 4-4-2.

        if rows is None:

            rows = formations[
                "4-4-2"
            ]

        result = []

        for role, percentage, count in rows:

            x = (
                FIELD_LEFT
                + (
                    FIELD_RIGHT
                    - FIELD_LEFT
                )
                * percentage
            )

            # --------------------------------------------------
            # ÉQUIPE EXTÉRIEURE
            # --------------------------------------------------

            if not home:

                x = (
                    FIELD_RIGHT
                    - (
                        x
                        - FIELD_LEFT
                    )
                )

            # --------------------------------------------------
            # VERTICAL POSITIONS
            # --------------------------------------------------

            if count == 1:

                ys = [360]

            else:

                available_height = (
                    FIELD_BOTTOM
                    - FIELD_TOP
                    - 80
                )

                spacing = (
                    available_height
                    / (
                        count - 1
                    )
                )

                ys = []

                for i in range(
                    count
                ):

                    y = (
                        FIELD_TOP
                        + 40
                        + (
                            spacing * i
                        )
                    )

                    ys.append(y)

            for y in ys:

                result.append(
                    (
                        x,
                        y,
                        role,
                    )
                )

        return result

    # ======================================================
    # FIND PLAYER
    # ======================================================

    def find_player(
        self,
        player_id: int,
    ):

        for player in self.players:

            if (
                player.player_id
                == player_id
            ):

                return player

        return None

    # ======================================================
    # APPLY EVENT
    # ======================================================

    def apply_event(
        self,
        event: MatchEvent,
    ):

        self.minute = event.minute

        self.last_event = event

        # --------------------------------------------------
        # SCORE
        # --------------------------------------------------

        if event.event_type == "GOAL":

            if (
                event.team_id
                == self.home_team.club_id
            ):

                self.home_score += 1

            elif (
                event.team_id
                == self.away_team.club_id
            ):

                self.away_score += 1

        # --------------------------------------------------
        # PLAYER
        # --------------------------------------------------

        player = None

        if event.player_id:

            player = self.find_player(
                event.player_id
            )

        # --------------------------------------------------
        # PASS
        # --------------------------------------------------

        if event.event_type == "PASS":

            self._animate_pass(
                event
            )

        # --------------------------------------------------
        # DRIBBLE
        # --------------------------------------------------

        elif event.event_type == "DRIBBLE":

            self._animate_dribble(
                event
            )

        # --------------------------------------------------
        # CROSS
        # --------------------------------------------------

        elif event.event_type == "CROSS":

            self._animate_cross(
                event
            )

        # --------------------------------------------------
        # SHOT
        # --------------------------------------------------

        elif event.event_type in {
            "SHOT",
            "GOAL",
            "SAVE",
        }:

            self._animate_shot(
                event
            )

        # --------------------------------------------------
        # COUNTER
        # --------------------------------------------------

        elif (
            event.event_type
            == "COUNTER_ATTACK"
        ):

            self._animate_counter(
                event
            )

        elif player:

            self.camera.target_x = (
                player.position.x
            )

            self.camera.target_y = (
                player.position.y
            )

    # ======================================================
    # PASS
    # ======================================================

    def _animate_pass(
        self,
        event: MatchEvent,
    ):

        player = self.find_player(
            event.player_id
        )

        receiver = self.find_player(
            event.secondary_player_id
        )

        if not player:
            return

        self.camera.target_x = (
            player.position.x
        )

        self.camera.target_y = (
            player.position.y
        )

        if receiver:

            self.ball.target = Position(
                receiver.position.x,
                receiver.position.y,
            )

    # ======================================================
    # DRIBBLE
    # ======================================================

    def _animate_dribble(
        self,
        event: MatchEvent,
    ):

        player = self.find_player(
            event.player_id
        )

        if not player:
            return

        direction = (
            35
            if player.team_id
            == self.home_team.club_id
            else -35
        )

        player.position.x += direction

        self.ball.position = Position(
            player.position.x,
            player.position.y,
        )

        self.camera.target_x = (
            player.position.x
        )

        self.camera.target_y = (
            player.position.y
        )

    # ======================================================
    # CROSS
    # ======================================================

    def _animate_cross(
        self,
        event: MatchEvent,
    ):

        player = self.find_player(
            event.player_id
        )

        if not player:
            return

        self.ball.position = Position(
            player.position.x,
            player.position.y,
        )

        self.camera.target_x = (
            player.position.x
        )

        self.camera.target_y = (
            player.position.y
        )

    # ======================================================
    # SHOT
    # ======================================================

    def _animate_shot(
        self,
        event: MatchEvent,
    ):

        player = self.find_player(
            event.player_id
        )

        if not player:
            return

        self.ball.position = Position(
            player.position.x,
            player.position.y,
        )

        self.camera.target_x = (
            player.position.x
        )

        self.camera.target_y = (
            player.position.y
        )

        self.camera.zoom = 1.15

    # ======================================================
    # COUNTER ATTACK
    # ======================================================

    def _animate_counter(
        self,
        event: MatchEvent,
    ):

        player = self.find_player(
            event.player_id
        )

        if not player:
            return

        direction = (
            80
            if player.team_id
            == self.home_team.club_id
            else -80
        )

        player.position.x += direction

        self.ball.position = Position(
            player.position.x,
            player.position.y,
        )

        self.camera.target_x = (
            player.position.x
        )

        self.camera.target_y = (
            player.position.y
        )

        self.camera.zoom = 1.10

    # ======================================================
    # CAMERA RESET
    # ======================================================

    def reset_camera(self):

        self.camera.zoom = 1.0

        self.camera.target_x = 640
        self.camera.target_y = 360