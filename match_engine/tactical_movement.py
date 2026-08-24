from .renderer import MatchVisualState, Position


class TacticalMovement:

    def __init__(
        self,
        state: MatchVisualState,
    ):

        self.state = state

        # Intensité des déplacements.
        # On garde des valeurs faibles pour
        # obtenir des mouvements naturels.
        self.position_speed = 0.025

    # ======================================================
    # MAIN UPDATE
    # ======================================================

    def update(
        self,
        attacking_team,
        defending_team,
    ):

        self._update_team(
            attacking_team,
            attacking=True,
        )

        self._update_team(
            defending_team,
            attacking=False,
        )

    # ======================================================
    # UPDATE TEAM
    # ======================================================

    def _update_team(
        self,
        team,
        attacking,
    ):

        visual_players = [
            player
            for player in self.state.players
            if player.team_id == team.club_id
        ]

        for visual_player in visual_players:

            real_player = (
                self._find_real_player(
                    team,
                    visual_player.player_id,
                )
            )

            if real_player is None:
                continue

            role = self._get_role(
                visual_player,
                real_player,
            )

            target = self._calculate_target(
                visual_player,
                role,
                attacking,
            )

            self._move_toward(
                visual_player,
                target,
            )

    # ======================================================
    # ROLE
    # ======================================================

    @staticmethod
    def _get_role(
        visual_player,
        real_player,
    ):

        # La position créée par LINEUP
        # est prioritaire.

        role = str(
            getattr(
                visual_player,
                "role",
                "",
            )
        ).upper()

        if role in {
            "GK",
            "DEF",
            "MID",
            "ATT",
        }:

            return role

        # Fallback sur la position du joueur.

        role = str(
            getattr(
                real_player,
                "position",
                "",
            )
        ).upper()

        if role in {
            "GK",
            "DEF",
            "MID",
            "ATT",
        }:

            return role

        return "MID"

    # ======================================================
    # TARGET
    # ======================================================

    def _calculate_target(
        self,
        player,
        role,
        attacking,
    ):

        home = (
            player.team_id
            == self.state.home_team.club_id
        )

        direction = (
            1
            if home
            else -1
        )

        # --------------------------------------------------
        # BASE X
        # --------------------------------------------------

        if role == "GK":

            base_x = (
                135
                if home
                else 1145
            )

        elif role == "DEF":

            base_x = (
                315
                if home
                else 965
            )

        elif role == "MID":

            base_x = (
                525
                if home
                else 755
            )

        else:  # ATT

            base_x = (
                760
                if home
                else 520
            )

        # --------------------------------------------------
        # ATTACKING PHASE
        # --------------------------------------------------

        if attacking:

            if role == "DEF":

                base_x += (
                    direction * 35
                )

            elif role == "MID":

                base_x += (
                    direction * 55
                )

            elif role == "ATT":

                base_x += (
                    direction * 80
                )

        # --------------------------------------------------
        # DEFENSIVE PHASE
        # --------------------------------------------------

        else:

            if role == "DEF":

                base_x -= (
                    direction * 20
                )

            elif role == "MID":

                base_x -= (
                    direction * 40
                )

            elif role == "ATT":

                base_x -= (
                    direction * 65
                )

        # --------------------------------------------------
        # BALL INFLUENCE
        # --------------------------------------------------

        ball = self.state.ball.position

        if role == "GK":

            ball_factor = 0.025

        elif role == "DEF":

            ball_factor = 0.06

        elif role == "MID":

            ball_factor = 0.10

        else:

            ball_factor = 0.075

        target_x = (
            base_x
            + (
                ball.x
                - base_x
            )
            * ball_factor
        )

        # --------------------------------------------------
        # Y POSITION
        # --------------------------------------------------

        target_y = player.position.y

        # Le joueur suit légèrement la hauteur
        # du ballon, sans abandonner sa zone.

        target_y += (
            ball.y
            - target_y
        ) * ball_factor

        # --------------------------------------------------
        # ROLE ZONES
        # --------------------------------------------------

        if role == "GK":

            target_y = max(
                270,
                min(
                    450,
                    target_y,
                ),
            )

        elif role == "DEF":

            target_y = max(
                150,
                min(
                    570,
                    target_y,
                ),
            )

        elif role == "MID":

            target_y = max(
                125,
                min(
                    595,
                    target_y,
                ),
            )

        elif role == "ATT":

            target_y = max(
                120,
                min(
                    600,
                    target_y,
                ),
            )

        # --------------------------------------------------
        # FIELD LIMITS
        # --------------------------------------------------

        target_x = max(
            100,
            min(
                1180,
                target_x,
            ),
        )

        target_y = max(
            110,
            min(
                610,
                target_y,
            ),
        )

        return Position(
            target_x,
            target_y,
        )

    # ======================================================
    # SMOOTH MOVEMENT
    # ======================================================

    def _move_toward(
        self,
        player,
        target,
    ):

        player.position.x += (
            target.x
            - player.position.x
        ) * self.position_speed

        player.position.y += (
            target.y
            - player.position.y
        ) * self.position_speed

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