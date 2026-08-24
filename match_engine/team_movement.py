import random

from .renderer import MatchVisualState, Position


class TeamMovementEngine:

    def __init__(
        self,
        state: MatchVisualState,
    ):

        self.state = state

    # ======================================================
    # UPDATE
    # ======================================================

    def update(
        self,
        attacking_team,
        defending_team,
        ball_position,
    ):

        self._move_attackers(
            attacking_team,
            ball_position,
        )

        self._move_defenders(
            defending_team,
            ball_position,
        )

    # ======================================================
    # ATTACKING MOVEMENT
    # ======================================================

    def _move_attackers(
        self,
        team,
        ball_position,
    ):

        players = [
            player
            for player in self.state.players
            if player.team_id == team.club_id
        ]

        for player in players:

            if player.position is None:
                continue

            position = str(
                getattr(
                    self._find_real_player(
                        team,
                        player.player_id,
                    ),
                    "position",
                    "",
                )
            ).upper()

            # GK reste principalement en retrait
            if position == "GK":
                continue

            # Le porteur est déjà géré
            # par l'animation de l'action.
            distance = self._distance(
                player.position,
                ball_position,
            )

            if distance < 55:
                continue

            # --------------------------------------------------
            # ATT
            # --------------------------------------------------

            if position == "ATT":

                self._small_movement(
                    player,
                    forward=True,
                    amount=random.uniform(
                        15,
                        35,
                    ),
                )

            # --------------------------------------------------
            # MID
            # --------------------------------------------------

            elif position == "MID":

                self._small_movement(
                    player,
                    forward=True,
                    amount=random.uniform(
                        8,
                        25,
                    ),
                )

            # --------------------------------------------------
            # DEF
            # --------------------------------------------------

            elif position == "DEF":

                self._small_movement(
                    player,
                    forward=True,
                    amount=random.uniform(
                        3,
                        12,
                    ),
                )

    # ======================================================
    # DEFENSIVE MOVEMENT
    # ======================================================

    def _move_defenders(
        self,
        team,
        ball_position,
    ):

        players = [
            player
            for player in self.state.players
            if player.team_id == team.club_id
        ]

        for player in players:

            real_player = (
                self._find_real_player(
                    team,
                    player.player_id,
                )
            )

            if real_player is None:
                continue

            position = str(
                getattr(
                    real_player,
                    "position",
                    "",
                )
            ).upper()

            if position == "GK":

                self._goalkeeper_adjustment(
                    player,
                    ball_position,
                    team,
                )

                continue

            distance = self._distance(
                player.position,
                ball_position,
            )

            if distance < 180:

                self._move_toward_ball(
                    player,
                    ball_position,
                    random.uniform(
                        0.03,
                        0.08,
                    ),
                )

            else:

                self._small_movement(
                    player,
                    forward=False,
                    amount=random.uniform(
                        3,
                        10,
                    ),
                )

    # ======================================================
    # GOALKEEPER
    # ======================================================

    def _goalkeeper_adjustment(
        self,
        player,
        ball_position,
        team,
    ):

        target_y = ball_position.y

        target_y = max(
            275,
            min(
                445,
                target_y,
            ),
        )

        # GK suit légèrement la hauteur
        # du ballon sans sortir de sa zone.

        player.position.y += (
            target_y
            - player.position.y
        ) * 0.025

    # ======================================================
    # MOVE TOWARD BALL
    # ======================================================

    def _move_toward_ball(
        self,
        player,
        ball_position,
        factor,
    ):

        player.position.x += (
            ball_position.x
            - player.position.x
        ) * factor

        player.position.y += (
            ball_position.y
            - player.position.y
        ) * factor

    # ======================================================
    # SMALL MOVEMENT
    # ======================================================

    def _small_movement(
        self,
        player,
        forward,
        amount,
    ):

        direction = 1

        if player.team_id == (
            self.state.away_team.club_id
        ):

            direction = -1

        if not forward:

            direction *= -1

        player.position.x += (
            direction
            * amount
            * 0.02
        )

        player.position.y += (
            random.uniform(
                -amount,
                amount,
            )
            * 0.01
        )

        self._clamp_player(
            player
        )

    # ======================================================
    # KEEP PLAYER ON FIELD
    # ======================================================

    def _clamp_player(
        self,
        player,
    ):

        player.position.x = max(
            100,
            min(
                1180,
                player.position.x,
            ),
        )

        player.position.y = max(
            115,
            min(
                605,
                player.position.y,
            ),
        )

    # ======================================================
    # FIND REAL PLAYER
    # ======================================================

    @staticmethod
    def _find_real_player(
        team,
        player_id,
    ):

        for player in team.players:

            if player.id == player_id:
                return player

        return None

    # ======================================================
    # DISTANCE
    # ======================================================

    @staticmethod
    def _distance(
        a,
        b,
    ):

        dx = (
            a.x - b.x
        )

        dy = (
            a.y - b.y
        )

        return (
            dx * dx
            + dy * dy
        ) ** 0.5