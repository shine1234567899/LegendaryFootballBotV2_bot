import math
import random
from dataclasses import dataclass

from .renderer import (
    MatchVisualState,
    Position,
)


# ==========================================================
# ANIMATION
# ==========================================================

@dataclass
class Movement:

    player_id: int

    start: Position

    target: Position

    duration: float

    elapsed: float = 0.0


# ==========================================================
# ANIMATION ENGINE
# ==========================================================

class AnimationEngine:

    def __init__(
        self,
        state: MatchVisualState,
    ):

        self.state = state

        self.movements = []

        self.ball_start = Position(
            self.state.ball.position.x,
            self.state.ball.position.y,
        )

        self.ball_target = None

        self.ball_duration = 0.0
        self.ball_elapsed = 0.0

        self.camera_start = Position(
            self.state.camera.x,
            self.state.camera.y,
        )

        self.camera_target = Position(
            self.state.camera.target_x,
            self.state.camera.target_y,
        )

        self.camera_duration = 0.0
        self.camera_elapsed = 0.0

    # ======================================================
    # INTERPOLATION
    # ======================================================

    @staticmethod
    def interpolate(
        start: float,
        target: float,
        progress: float,
    ) -> float:

        progress = max(
            0.0,
            min(
                1.0,
                progress,
            ),
        )

        # Smooth step
        progress = (
            progress
            * progress
            * (
                3
                - 2 * progress
            )
        )

        return (
            start
            + (
                target - start
            )
            * progress
        )

    # ======================================================
    # DISTANCE
    # ======================================================

    @staticmethod
    def distance(
        a: Position,
        b: Position,
    ) -> float:

        return math.sqrt(
            (
                b.x - a.x
            ) ** 2
            +
            (
                b.y - a.y
            ) ** 2
        )

    # ======================================================
    # MOVE PLAYER
    # ======================================================

    def move_player(
        self,
        player_id: int,
        target: Position,
        duration: float = 0.8,
    ):

        player = self.state.find_player(
            player_id
        )

        if player is None:
            return

        start = Position(
            player.position.x,
            player.position.y,
        )

        self.movements.append(
            Movement(
                player_id=player_id,
                start=start,
                target=target,
                duration=max(
                    0.05,
                    duration,
                ),
            )
        )

    # ======================================================
    # MOVE PLAYER FOR EVENT
    # ======================================================

    def animate_event(
        self,
        event,
    ):

        player = None

        if event.player_id:

            player = self.state.find_player(
                event.player_id
            )

        # --------------------------------------------------
        # PASS
        # --------------------------------------------------

        if event.event_type == "PASS":

            receiver = None

            if event.secondary_player_id:

                receiver = (
                    self.state.find_player(
                        event.secondary_player_id
                    )
                )

            if player and receiver:

                self.move_player(
                    receiver.player_id,
                    Position(
                        receiver.position.x + (
                            random.uniform(
                                -10,
                                10,
                            )
                        ),
                        receiver.position.y + (
                            random.uniform(
                                -10,
                                10,
                            )
                        ),
                    ),
                    duration=0.6,
                )

                self.ball_to(
                    Position(
                        receiver.position.x,
                        receiver.position.y,
                    ),
                    duration=0.6,
                )

            return

        # --------------------------------------------------
        # DRIBBLE
        # --------------------------------------------------

        if event.event_type == "DRIBBLE":

            if not player:
                return

            direction = (
                1
                if (
                    player.team_id
                    == self.state.home_team.club_id
                )
                else -1
            )

            distance = random.uniform(
                25,
                65,
            )

            target = Position(
                player.position.x
                + (
                    direction
                    * distance
                ),
                player.position.y
                + random.uniform(
                    -20,
                    20,
                ),
            )

            self.move_player(
                player.player_id,
                target,
                duration=random.uniform(
                    0.7,
                    1.4,
                ),
            )

            self.ball_to(
                target,
                duration=0.7,
            )

            return

        # --------------------------------------------------
        # CROSS
        # --------------------------------------------------

        if event.event_type == "CROSS":

            if not player:
                return

            target_x = (
                self.state.camera.target_x
            )

            if (
                player.team_id
                == self.state.home_team.club_id
            ):

                target_x = (
                    self.state.camera.target_x
                    + 220
                )

            else:

                target_x = (
                    self.state.camera.target_x
                    - 220
                )

            target = Position(
                max(
                    100,
                    min(
                        1180,
                        target_x,
                    ),
                ),
                random.uniform(
                    230,
                    490,
                ),
            )

            self.ball_to(
                target,
                duration=1.0,
            )

            return

        # --------------------------------------------------
        # SHOT
        # --------------------------------------------------

        if event.event_type in {
            "SHOT",
            "GOAL",
            "SAVE",
        }:

            if not player:
                return

            direction = (
                1
                if (
                    player.team_id
                    == self.state.home_team.club_id
                )
                else -1
            )

            target = Position(
                player.position.x
                + (
                    direction
                    * random.uniform(
                        180,
                        300,
                    )
                ),
                random.uniform(
                    260,
                    460,
                ),
            )

            self.ball_to(
                target,
                duration=random.uniform(
                    0.4,
                    0.8,
                ),
            )

            self.state.camera.zoom = 1.2

            return

        # --------------------------------------------------
        # COUNTER ATTACK
        # --------------------------------------------------

        if event.event_type == "COUNTER_ATTACK":

            if not player:
                return

            direction = (
                1
                if (
                    player.team_id
                    == self.state.home_team.club_id
                )
                else -1
            )

            target = Position(
                player.position.x
                + (
                    direction
                    * random.uniform(
                        100,
                        180,
                    )
                ),
                player.position.y
                + random.uniform(
                    -35,
                    35,
                ),
            )

            self.move_player(
                player.player_id,
                target,
                duration=1.2,
            )

            self.ball_to(
                target,
                duration=1.0,
            )

            return

    # ======================================================
    # BALL
    # ======================================================

    def ball_to(
        self,
        target: Position,
        duration: float,
    ):

        self.ball_start = Position(
            self.state.ball.position.x,
            self.state.ball.position.y,
        )

        self.ball_target = Position(
            target.x,
            target.y,
        )

        self.ball_duration = max(
            0.05,
            duration,
        )

        self.ball_elapsed = 0.0

    # ======================================================
    # CAMERA
    # ======================================================

    def camera_to(
        self,
        target: Position,
        duration: float = 0.8,
    ):

        self.camera_start = Position(
            self.state.camera.x,
            self.state.camera.y,
        )

        self.camera_target = Position(
            target.x,
            target.y,
        )

        self.camera_duration = max(
            0.05,
            duration,
        )

        self.camera_elapsed = 0.0

    # ======================================================
    # UPDATE
    # ======================================================

    def update(
        self,
        delta_time: float,
    ):

        # --------------------------------------------------
        # PLAYERS
        # --------------------------------------------------

        finished = []

        for movement in self.movements:

            movement.elapsed += (
                delta_time
            )

            progress = (
                movement.elapsed
                / movement.duration
            )

            player = (
                self.state.find_player(
                    movement.player_id
                )
            )

            if player is None:

                finished.append(
                    movement
                )

                continue

            player.position.x = (
                self.interpolate(
                    movement.start.x,
                    movement.target.x,
                    progress,
                )
            )

            player.position.y = (
                self.interpolate(
                    movement.start.y,
                    movement.target.y,
                    progress,
                )
            )

            if progress >= 1.0:

                finished.append(
                    movement
                )

        for movement in finished:

            if movement in self.movements:

                self.movements.remove(
                    movement
                )

        # --------------------------------------------------
        # BALL
        # --------------------------------------------------

        if self.ball_target:

            self.ball_elapsed += (
                delta_time
            )

            progress = (
                self.ball_elapsed
                / self.ball_duration
            )

            self.state.ball.position.x = (
                self.interpolate(
                    self.ball_start.x,
                    self.ball_target.x,
                    progress,
                )
            )

            self.state.ball.position.y = (
                self.interpolate(
                    self.ball_start.y,
                    self.ball_target.y,
                    progress,
                )
            )

            if progress >= 1.0:

                self.ball_target = None

        # --------------------------------------------------
        # CAMERA
        # --------------------------------------------------

        if self.camera_duration > 0:

            self.camera_elapsed += (
                delta_time
            )

            progress = (
                self.camera_elapsed
                / self.camera_duration
            )

            self.state.camera.x = (
                self.interpolate(
                    self.camera_start.x,
                    self.camera_target.x,
                    progress,
                )
            )

            self.state.camera.y = (
                self.interpolate(
                    self.camera_start.y,
                    self.camera_target.y,
                    progress,
                )
            )

            if progress >= 1.0:

                self.camera_duration = 0.0

    # ======================================================
    # RESET ZOOM
    # ======================================================

    def reset_zoom(self):

        self.state.camera.zoom = (
            self.interpolate(
                self.state.camera.zoom,
                1.0,
                0.15,
            )
        )