import math
import time

import pygame

from .renderer import (
    MatchVisualState,
    FIELD_WIDTH,
    FIELD_HEIGHT,
    FIELD_LEFT,
    FIELD_RIGHT,
    FIELD_TOP,
    FIELD_BOTTOM,
)


# ==========================================================
# LIVE SCOREBOARD GRAPHICS
# ==========================================================

class MatchGraphics:

    FPS = 30

    # ------------------------------------------------------
    # EVENT DURATIONS
    # ------------------------------------------------------

    EVENT_DURATION = {
        "POSSESSION": 0.90,
        "ATTACK": 1.15,
        "DANGEROUS ATTACK": 1.35,
        "SHOT": 1.10,
        "GOAL": 2.40,
        "CORNER": 1.60,
        "FREE KICK": 1.60,
        "THROW-IN": 1.30,
        "SAVE": 1.10,
        "CLEARANCE": 0.85,
        "INTERCEPTION": 0.85,
        "TACKLE": 0.75,
        "KICK-OFF": 1.20,
        "HALF TIME": 2.00,
        "FULL TIME": 3.00,
    }

    # ------------------------------------------------------
    # COLORS
    # ------------------------------------------------------

    BACKGROUND = (
        24,
        28,
        32,
    )

    STADIUM = (
        44,
        48,
        54,
    )

    GRASS_A = (
        63,
        119,
        42,
    )

    GRASS_B = (
        70,
        132,
        46,
    )

    WHITE = (
        245,
        245,
        245,
    )

    BLACK = (
        15,
        18,
        20,
    )

    HOME = (
        35,
        155,
        235,
    )

    AWAY = (
        155,
        225,
        55,
    )

    ATTACK = (
        70,
        170,
        245,
    )

    DANGEROUS = (
        255,
        165,
        45,
    )

    GOAL = (
        255,
        220,
        55,
    )

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        visual_state: MatchVisualState,
        width: int = FIELD_WIDTH,
        height: int = FIELD_HEIGHT,
        engine=None,
    ):

        self.state = visual_state

        self.width = width
        self.height = height

        self.engine = engine

        self.screen = None

        self.initialized = False

        # --------------------------------------------------
        # FONTS
        # --------------------------------------------------

        self.font_tiny = None
        self.font_small = None
        self.font_medium = None
        self.font_large = None
        self.font_score = None

        # --------------------------------------------------
        # BALL
        # --------------------------------------------------

        self.ball_x = (
            FIELD_LEFT
            + (
                FIELD_RIGHT
                - FIELD_LEFT
            ) / 2
        )

        self.ball_y = (
            FIELD_TOP
            + (
                FIELD_BOTTOM
                - FIELD_TOP
            ) / 2
        )

        self.ball_start_x = self.ball_x
        self.ball_start_y = self.ball_y

        self.ball_target_x = self.ball_x
        self.ball_target_y = self.ball_y

        self.ball_move_started = (
            time.perf_counter()
        )

        self.ball_move_duration = 0.45

        # --------------------------------------------------
        # CURRENT EVENT
        # --------------------------------------------------

        self.current_event_type = (
            "KICK-OFF"
        )

        self.current_event_team = ""

        self.current_event_minute = 0

        self.current_event_description = (
            "KICK-OFF"
        )

        self.event_started = (
            time.perf_counter()
        )

        self.event_duration = (
            self.EVENT_DURATION[
                "KICK-OFF"
            ]
        )

        # --------------------------------------------------
        # TRAJECTORY
        # --------------------------------------------------

        self.arrow_start_x = self.ball_x
        self.arrow_start_y = self.ball_y

        self.arrow_end_x = self.ball_x
        self.arrow_end_y = self.ball_y

        self.arrow_alpha = 0

        # --------------------------------------------------
        # POSSESSION
        # --------------------------------------------------

        self.possession_team = None

        # --------------------------------------------------
        # GOAL FLASH
        # --------------------------------------------------

        self.goal_flash_until = 0.0

    # ======================================================
    # INITIALIZE
    # ======================================================

    def initialize(self):

        if self.initialized:
            return

        pygame.init()

        self.screen = pygame.Surface(
            (
                self.width,
                self.height,
            )
        )

        self.font_tiny = pygame.font.Font(
            None,
            14,
        )

        self.font_small = pygame.font.Font(
            None,
            18,
        )

        self.font_medium = pygame.font.Font(
            None,
            24,
        )

        self.font_large = pygame.font.Font(
            None,
            32,
        )

        self.font_score = pygame.font.Font(
            None,
            38,
        )

        self.initialized = True

    # ======================================================
    # EVENT RECEIVED
    # ======================================================

    def set_event(
        self,
        event,
    ):

        if event is None:
            return

        now = time.perf_counter()

        event_type = str(
            getattr(
                event,
                "event_type",
                "",
            )
            or ""
        ).upper().strip()

        team_name = str(
            getattr(
                event,
                "team_name",
                "",
            )
            or ""
        )

        minute = int(
            getattr(
                event,
                "minute",
                0,
            )
            or 0
        )

        metadata = getattr(
            event,
            "metadata",
            None,
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        # --------------------------------------------------
        # CLASSIFY
        # --------------------------------------------------

        display_type = (
            self._classify_event(
                event_type,
                metadata,
            )
        )

        # --------------------------------------------------
        # TEAM
        # --------------------------------------------------

        team_id = getattr(
            event,
            "team_id",
            None,
        )

        if (
            team_id
            == self.state.home_team.club_id
        ):

            self.possession_team = "HOME"

        elif (
            team_id
            == self.state.away_team.club_id
        ):

            self.possession_team = "AWAY"

        # --------------------------------------------------
        # EVENT
        # --------------------------------------------------

        self.current_event_type = (
            display_type
        )

        self.current_event_team = (
            team_name
        )

        self.current_event_minute = (
            minute
        )

        self.current_event_description = (
            self._event_description(
                display_type,
                team_name,
            )
        )

        self.event_started = now

        self.event_duration = (
            self.EVENT_DURATION.get(
                display_type,
                0.90,
            )
        )

        # --------------------------------------------------
        # TRAJECTORY
        # --------------------------------------------------

        start, end = (
            self._calculate_trajectory(
                display_type,
                team_id,
            )
        )

        self.arrow_start_x = start[0]
        self.arrow_start_y = start[1]

        self.arrow_end_x = end[0]
        self.arrow_end_y = end[1]

        # --------------------------------------------------
        # BALL
        # --------------------------------------------------

        self.ball_start_x = (
            self.ball_x
        )

        self.ball_start_y = (
            self.ball_y
        )

        self.ball_target_x = end[0]
        self.ball_target_y = end[1]

        self.ball_move_started = now

        # --------------------------------------------------
        # GOAL
        # --------------------------------------------------

        if display_type == "GOAL":

            self.goal_flash_until = (
                now + 1.5
            )

    # ======================================================
    # EVENT CLASSIFICATION
    # ======================================================

    def _classify_event(
        self,
        event_type,
        metadata,
    ):

        event_type = str(
            event_type
        ).upper()

        if event_type == "GOAL":
            return "GOAL"

        if event_type in {
            "SHOT",
            "SHOT_ON_TARGET",
        }:
            return "SHOT"

        if event_type == "SAVE":
            return "SAVE"

        if event_type == "CORNER":
            return "CORNER"

        if event_type in {
            "FREE_KICK",
            "FREEKICK",
        }:
            return "FREE KICK"

        if event_type in {
            "THROW_IN",
            "THROWIN",
        }:
            return "THROW-IN"

        if event_type == "COUNTER_ATTACK":
            return "DANGEROUS ATTACK"

        if event_type in {
            "CROSS",
            "DRIBBLE",
        }:
            return "ATTACK"

        if event_type in {
            "BUILD_UP",
            "PASS",
        }:
            return "POSSESSION"

        if event_type == "CLEARANCE":
            return "CLEARANCE"

        if event_type == "INTERCEPTION":
            return "INTERCEPTION"

        if event_type == "TACKLE":
            return "TACKLE"

        if event_type == "KICKOFF":
            return "KICK-OFF"

        if event_type == "HALFTIME":
            return "HALF TIME"

        if event_type == "SECOND_HALF":
            return "KICK-OFF"

        if event_type == "FULL_TIME":
            return "FULL TIME"

        # --------------------------------------------------
        # Metadata can override generic events
        # --------------------------------------------------

        if metadata.get(
            "dangerous_attack"
        ):
            return "DANGEROUS ATTACK"

        if metadata.get(
            "attack"
        ):
            return "ATTACK"

        if metadata.get(
            "possession"
        ):
            return "POSSESSION"

        return "POSSESSION"

    # ======================================================
    # EVENT DESCRIPTION
    # ======================================================

    def _event_description(
        self,
        event_type,
        team_name,
    ):

        if not team_name:
            team_name = "MATCH"

        return (
            f"{team_name}  "
            f"{event_type}"
        )

    # ======================================================
    # TRAJECTORY
    # ======================================================

    def _calculate_trajectory(
        self,
        event_type,
        team_id,
    ):

        field_left = FIELD_LEFT
        field_right = FIELD_RIGHT

        field_top = FIELD_TOP
        field_bottom = FIELD_BOTTOM

        field_width = (
            field_right
            - field_left
        )

        field_height = (
            field_bottom
            - field_top
        )

        center_x = (
            field_left
            + field_width / 2
        )

        center_y = (
            field_top
            + field_height / 2
        )

        # --------------------------------------------------
        # DIRECTION
        # --------------------------------------------------

        is_home = (
            team_id
            == self.state.home_team.club_id
        )

        # Home attacks right.
        # Away attacks left.

        if is_home:

            attack_direction = 1

        else:

            attack_direction = -1

        # --------------------------------------------------
        # START
        # --------------------------------------------------

        start_x = self.ball_x
        start_y = self.ball_y

        # --------------------------------------------------
        # POSSESSION
        # --------------------------------------------------

        if event_type == "POSSESSION":

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.08
            )

            end_y = (
                center_y
                + math.sin(
                    self.current_event_minute
                )
                * field_height
                * 0.08
            )

        # --------------------------------------------------
        # ATTACK
        # --------------------------------------------------

        elif event_type == "ATTACK":

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.25
            )

            end_y = (
                center_y
                + math.sin(
                    self.current_event_minute
                    * 1.7
                )
                * field_height
                * 0.18
            )

        # --------------------------------------------------
        # DANGEROUS ATTACK
        # --------------------------------------------------

        elif (
            event_type
            == "DANGEROUS ATTACK"
        ):

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.40
            )

            end_y = (
                center_y
                + math.sin(
                    self.current_event_minute
                    * 2.1
                )
                * field_height
                * 0.22
            )

        # --------------------------------------------------
        # SHOT
        # --------------------------------------------------

        elif event_type == "SHOT":

            end_x = (
                field_right - 12
                if is_home
                else field_left + 12
            )

            end_y = (
                center_y
                + math.sin(
                    self.current_event_minute
                    * 2.7
                )
                * field_height
                * 0.20
            )

        # --------------------------------------------------
        # GOAL
        # --------------------------------------------------

        elif event_type == "GOAL":

            end_x = (
                field_right - 8
                if is_home
                else field_left + 8
            )

            end_y = center_y

        # --------------------------------------------------
        # CORNER
        # --------------------------------------------------

        elif event_type == "CORNER":

            if is_home:

                end_x = field_right - 12

            else:

                end_x = field_left + 12

            end_y = (
                field_top
                + 18
            )

        # --------------------------------------------------
        # FREE KICK
        # --------------------------------------------------

        elif event_type == "FREE KICK":

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.30
            )

            end_y = center_y

        # --------------------------------------------------
        # THROW-IN
        # --------------------------------------------------

        elif event_type == "THROW-IN":

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.18
            )

            end_y = (
                field_top + 15
                if (
                    self.current_event_minute
                    % 2
                    == 0
                )
                else
                field_bottom - 15
            )

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        elif event_type == "SAVE":

            end_x = (
                field_right - 35
                if is_home
                else field_left + 35
            )

            end_y = center_y

        # --------------------------------------------------
        # DEFAULT
        # --------------------------------------------------

        else:

            end_x = (
                center_x
                + attack_direction
                * field_width
                * 0.12
            )

            end_y = center_y

        # --------------------------------------------------
        # CLAMP
        # --------------------------------------------------

        end_x = max(
            field_left + 8,
            min(
                field_right - 8,
                end_x,
            ),
        )

        end_y = max(
            field_top + 8,
            min(
                field_bottom - 8,
                end_y,
            ),
        )

        return (
            (start_x, start_y),
            (end_x, end_y),
        )

    # ======================================================
    # DRAW FRAME
    # ======================================================

    def draw_frame(self):

        if not self.initialized:
            self.initialize()

        self._update_animation()

        self._draw_background()

        self._draw_field()

        self._draw_goals()

        self._draw_trajectory()

        self._draw_ball()

        self._draw_scoreboard()

        self._draw_event_card()

        self._draw_goal_flash()

        return self.screen

    # ======================================================
    # ANIMATION UPDATE
    # ======================================================

    def _update_animation(self):

        now = time.perf_counter()

        elapsed = (
            now
            - self.ball_move_started
        )

        if (
            self.ball_move_duration
            <= 0
        ):

            progress = 1.0

        else:

            progress = (
                elapsed
                / self.ball_move_duration
            )

        progress = max(
            0.0,
            min(
                1.0,
                progress,
            ),
        )

        # Smoothstep

        progress = (
            progress
            * progress
            * (
                3
                - 2 * progress
            )
        )

        self.ball_x = (
            self.ball_start_x
            + (
                self.ball_target_x
                - self.ball_start_x
            )
            * progress
        )

        self.ball_y = (
            self.ball_start_y
            + (
                self.ball_target_y
                - self.ball_start_y
            )
            * progress
        )

    # ======================================================
    # BACKGROUND
    # ======================================================

    def _draw_background(self):

        self.screen.fill(
            self.BACKGROUND
        )

        # Stadium upper area

        pygame.draw.rect(
            self.screen,
            self.STADIUM,
            (
                0,
                0,
                self.width,
                FIELD_TOP,
            ),
        )

        # Stadium lower area

        pygame.draw.rect(
            self.screen,
            self.STADIUM,
            (
                0,
                FIELD_BOTTOM,
                self.width,
                self.height
                - FIELD_BOTTOM,
            ),
        )

        # Side areas

        pygame.draw.rect(
            self.screen,
            self.STADIUM,
            (
                0,
                FIELD_TOP,
                FIELD_LEFT,
                FIELD_BOTTOM
                - FIELD_TOP,
            ),
        )

        pygame.draw.rect(
            self.screen,
            self.STADIUM,
            (
                FIELD_RIGHT,
                FIELD_TOP,
                self.width
                - FIELD_RIGHT,
                FIELD_BOTTOM
                - FIELD_TOP,
            ),
        )

    # ======================================================
    # FIELD
    # ======================================================

    def _draw_field(self):

        field_width = (
            FIELD_RIGHT
            - FIELD_LEFT
        )

        field_height = (
            FIELD_BOTTOM
            - FIELD_TOP
        )

        stripe_width = (
            field_width
            / 12
        )

        for index in range(12):

            color = (
                self.GRASS_A
                if index % 2 == 0
                else self.GRASS_B
            )

            pygame.draw.rect(
                self.screen,
                color,
                (
                    int(
                        FIELD_LEFT
                        + index
                        * stripe_width
                    ),
                    FIELD_TOP,
                    int(
                        stripe_width
                    ) + 1,
                    field_height,
                ),
            )

        white = self.WHITE

        # --------------------------------------------------
        # OUTLINE
        # --------------------------------------------------

        pygame.draw.rect(
            self.screen,
            white,
            (
                FIELD_LEFT,
                FIELD_TOP,
                field_width,
                field_height,
            ),
            3,
        )

        center_x = (
            FIELD_LEFT
            + field_width / 2
        )

        center_y = (
            FIELD_TOP
            + field_height / 2
        )

        # --------------------------------------------------
        # HALF WAY
        # --------------------------------------------------

        pygame.draw.line(
            self.screen,
            white,
            (
                int(center_x),
                FIELD_TOP,
            ),
            (
                int(center_x),
                FIELD_BOTTOM,
            ),
            3,
        )

        # --------------------------------------------------
        # CENTER CIRCLE
        # --------------------------------------------------

        pygame.draw.circle(
            self.screen,
            white,
            (
                int(center_x),
                int(center_y),
            ),
            70,
            3,
        )

        pygame.draw.circle(
            self.screen,
            white,
            (
                int(center_x),
                int(center_y),
            ),
            4,
        )

        # --------------------------------------------------
        # PENALTY AREAS
        # --------------------------------------------------

        penalty_height = 260
        penalty_width = 150

        penalty_top = (
            center_y
            - penalty_height / 2
        )

        pygame.draw.rect(
            self.screen,
            white,
            (
                FIELD_LEFT,
                int(penalty_top),
                penalty_width,
                penalty_height,
            ),
            3,
        )

        pygame.draw.rect(
            self.screen,
            white,
            (
                FIELD_RIGHT
                - penalty_width,
                int(penalty_top),
                penalty_width,
                penalty_height,
            ),
            3,
        )

        # --------------------------------------------------
        # GOAL AREAS
        # --------------------------------------------------

        goal_height = 130
        goal_width = 55

        goal_top = (
            center_y
            - goal_height / 2
        )

        pygame.draw.rect(
            self.screen,
            white,
            (
                FIELD_LEFT,
                int(goal_top),
                goal_width,
                goal_height,
            ),
            3,
        )

        pygame.draw.rect(
            self.screen,
            white,
            (
                FIELD_RIGHT
                - goal_width,
                int(goal_top),
                goal_width,
                goal_height,
            ),
            3,
        )

    # ======================================================
    # GOALS
    # ======================================================

    def _draw_goals(self):

        center_y = (
            FIELD_TOP
            + FIELD_BOTTOM
        ) / 2

        goal_height = 130

        goal_top = int(
            center_y
            - goal_height / 2
        )

        # Left

        pygame.draw.rect(
            self.screen,
            (
                215,
                215,
                215,
            ),
            (
                FIELD_LEFT - 20,
                goal_top,
                20,
                goal_height,
            ),
            2,
        )

        # Right

        pygame.draw.rect(
            self.screen,
            (
                215,
                215,
                215,
            ),
            (
                FIELD_RIGHT,
                goal_top,
                20,
                goal_height,
            ),
            2,
        )

    # ======================================================
    # TRAJECTORY
    # ======================================================

    def _draw_trajectory(self):

        now = time.perf_counter()

        elapsed = (
            now
            - self.event_started
        )

        if elapsed < 0:
            return

        # Fade out

        fade = 1.0 - (
            elapsed
            / max(
                self.event_duration,
                0.1,
            )
        )

        fade = max(
            0.0,
            min(
                1.0,
                fade,
            ),
        )

        if fade <= 0:
            return

        event_type = (
            self.current_event_type
        )

        # --------------------------------------------------
        # POSSESSION
        # --------------------------------------------------

        if event_type == "POSSESSION":

            base_color = (
                120,
                215,
                255,
            )

            width = 4

        # --------------------------------------------------
        # ATTACK
        # --------------------------------------------------

        elif event_type == "ATTACK":

            base_color = (
                70,
                175,
                255,
            )

            width = 5

        # --------------------------------------------------
        # DANGEROUS
        # --------------------------------------------------

        elif (
            event_type
            == "DANGEROUS ATTACK"
        ):

            base_color = (
                255,
                170,
                45,
            )

            width = 7

        # --------------------------------------------------
        # SHOT
        # --------------------------------------------------

        elif event_type == "SHOT":

            base_color = (
                255,
                245,
                245,
            )

            width = 6

        # --------------------------------------------------
        # GOAL
        # --------------------------------------------------

        elif event_type == "GOAL":

            base_color = (
                255,
                225,
                55,
            )

            width = 8

        # --------------------------------------------------
        # DEFAULT
        # --------------------------------------------------

        else:

            base_color = (
                210,
                220,
                225,
            )

            width = 3

        alpha = int(
            210 * fade
        )

        overlay = pygame.Surface(
            (
                self.width,
                self.height,
            ),
            pygame.SRCALPHA,
        )

        color = (
            base_color[0],
            base_color[1],
            base_color[2],
            alpha,
        )

        start = (
            int(
                self.arrow_start_x
            ),
            int(
                self.arrow_start_y
            ),
        )

        end = (
            int(
                self.arrow_end_x
            ),
            int(
                self.arrow_end_y
            ),
        )

        pygame.draw.line(
            overlay,
            color,
            start,
            end,
            width,
        )

        # --------------------------------------------------
        # ARROW HEAD
        # --------------------------------------------------

        angle = math.atan2(
            end[1] - start[1],
            end[0] - start[0],
        )

        arrow_length = (
            20
            if width <= 5
            else 25
        )

        left_angle = (
            angle
            + math.pi
            - math.pi / 6
        )

        right_angle = (
            angle
            + math.pi
            + math.pi / 6
        )

        left = (
            int(
                end[0]
                + math.cos(
                    left_angle
                )
                * arrow_length
            ),
            int(
                end[1]
                + math.sin(
                    left_angle
                )
                * arrow_length
            ),
        )

        right = (
            int(
                end[0]
                + math.cos(
                    right_angle
                )
                * arrow_length
            ),
            int(
                end[1]
                + math.sin(
                    right_angle
                )
                * arrow_length
            ),
        )

        pygame.draw.polygon(
            overlay,
            color,
            [
                end,
                left,
                right,
            ],
        )

        self.screen.blit(
            overlay,
            (
                0,
                0,
            ),
        )

    # ======================================================
    # BALL
    # ======================================================

    def _draw_ball(self):

        x = int(
            self.ball_x
        )

        y = int(
            self.ball_y
        )

        # --------------------------------------------------
        # SHADOW
        # --------------------------------------------------

        pygame.draw.ellipse(
            self.screen,
            (
                20,
                20,
                20,
            ),
            (
                x - 8,
                y + 5,
                16,
                5,
            ),
        )

        # --------------------------------------------------
        # BALL
        # --------------------------------------------------

        pygame.draw.circle(
            self.screen,
            (
                250,
                250,
                250,
            ),
            (
                x,
                y,
            ),
            7,
        )

        pygame.draw.circle(
            self.screen,
            (
                20,
                20,
                20,
            ),
            (
                x,
                y,
            ),
            7,
            1,
        )

        pygame.draw.circle(
            self.screen,
            (
                35,
                35,
                35,
            ),
            (
                x,
                y,
            ),
            2,
        )

    # ======================================================
    # SCOREBOARD
    # ======================================================

    def _draw_scoreboard(self):

        if self.engine is not None:

            home_score = int(
                self.engine.result.home_score
            )

            away_score = int(
                self.engine.result.away_score
            )

            minute = int(
                self.engine.current_minute
            )

        else:

            home_score = int(
                getattr(
                    self.state,
                    "home_score",
                    0,
                )
            )

            away_score = int(
                getattr(
                    self.state,
                    "away_score",
                    0,
                )
            )

            minute = int(
                getattr(
                    self.state,
                    "minute",
                    0,
                )
            )

        # --------------------------------------------------
        # TOP PANEL
        # --------------------------------------------------

        panel_width = min(
            self.width - 40,
            600,
        )

        panel_height = 82

        panel_x = (
            self.width
            - panel_width
        ) // 2

        panel_y = 10

        pygame.draw.rect(
            self.screen,
            (
                18,
                35,
                38,
            ),
            (
                panel_x,
                panel_y,
                panel_width,
                panel_height,
            ),
            border_radius=10,
        )

        pygame.draw.rect(
            self.screen,
            (
                70,
                85,
                90,
            ),
            (
                panel_x,
                panel_y,
                panel_width,
                panel_height,
            ),
            2,
            border_radius=10,
        )

        # --------------------------------------------------
        # TEAM NAMES
        # --------------------------------------------------

        home_name = (
            self.state.home_team.name[
                :18
            ]
        )

        away_name = (
            self.state.away_team.name[
                :18
            ]
        )

        home = self.font_medium.render(
            home_name,
            True,
            self.WHITE,
        )

        away = self.font_medium.render(
            away_name,
            True,
            self.WHITE,
        )

        self.screen.blit(
            home,
            (
                panel_x + 20,
                panel_y + 17,
            ),
        )

        away_rect = away.get_rect(
            top=(
                panel_y + 17
            ),
            right=(
                panel_x
                + panel_width
                - 20
            ),
        )

        self.screen.blit(
            away,
            away_rect,
        )

        # --------------------------------------------------
        # SCORE
        # --------------------------------------------------

        score_text = (
            f"{home_score}"
            f" : "
            f"{away_score}"
        )

        score = self.font_score.render(
            score_text,
            True,
            self.WHITE,
        )

        score_rect = score.get_rect(
            center=(
                self.width // 2,
                panel_y + 35,
            )
        )

        self.screen.blit(
            score,
            score_rect,
        )

        # --------------------------------------------------
        # CLOCK
        # --------------------------------------------------

        clock_text = (
            f"◷ {minute:02d}:00"
        )

        clock = self.font_small.render(
            clock_text,
            True,
            (
                220,
                230,
                230,
            ),
        )

        clock_rect = clock.get_rect(
            center=(
                self.width // 2,
                panel_y + 66,
            )
        )

        self.screen.blit(
            clock,
            clock_rect,
        )

    # ======================================================
    # EVENT CARD
    # ======================================================

    def _draw_event_card(self):

        now = time.perf_counter()

        elapsed = (
            now
            - self.event_started
        )

        if (
            elapsed
            > self.event_duration
        ):
            return

        # --------------------------------------------------
        # FADE
        # --------------------------------------------------

        fade_in = min(
            1.0,
            elapsed / 0.20,
        )

        fade_out = min(
            1.0,
            max(
                0.0,
                (
                    self.event_duration
                    - elapsed
                )
                / 0.35,
            ),
        )

        alpha = int(
            225
            * min(
                fade_in,
                fade_out,
            )
        )

        if alpha <= 0:
            return

        event_type = (
            self.current_event_type
        )

        # --------------------------------------------------
        # COLOR
        # --------------------------------------------------

        if event_type == "GOAL":

            accent = self.GOAL

        elif (
            event_type
            == "DANGEROUS ATTACK"
        ):

            accent = self.DANGEROUS

        elif event_type == "ATTACK":

            accent = self.ATTACK

        else:

            accent = (
                120,
                220,
                245,
            )

        overlay = pygame.Surface(
            (
                self.width,
                self.height,
            ),
            pygame.SRCALPHA,
        )

        panel_width = 390
        panel_height = 66

        panel_x = (
            self.width
            - panel_width
        ) // 2

        panel_y = (
            FIELD_TOP
            + 95
        )

        pygame.draw.rect(
            overlay,
            (
                8,
                15,
                18,
                alpha,
            ),
            (
                panel_x,
                panel_y,
                panel_width,
                panel_height,
            ),
            border_radius=7,
        )

        # Accent line

        pygame.draw.rect(
            overlay,
            (
                accent[0],
                accent[1],
                accent[2],
                alpha,
            ),
            (
                panel_x,
                panel_y,
                5,
                panel_height,
            ),
            border_radius=4,
        )

        # --------------------------------------------------
        # TEAM
        # --------------------------------------------------

        team_surface = (
            self.font_small.render(
                self.current_event_team[
                    :25
                ],
                True,
                (
                    235,
                    240,
                    240,
                ),
            )
        )

        overlay.blit(
            team_surface,
            (
                panel_x + 18,
                panel_y + 10,
            ),
        )

        # --------------------------------------------------
        # EVENT
        # --------------------------------------------------

        event_surface = (
            self.font_medium.render(
                event_type,
                True,
                accent,
            )
        )

        overlay.blit(
            event_surface,
            (
                panel_x + 18,
                panel_y + 34,
            ),
        )

        self.screen.blit(
            overlay,
            (
                0,
                0,
            ),
        )

    # ======================================================
    # GOAL FLASH
    # ======================================================

    def _draw_goal_flash(self):

        now = time.perf_counter()

        if (
            now
            >= self.goal_flash_until
        ):
            return

        remaining = (
            self.goal_flash_until
            - now
        )

        alpha = int(
            min(
                85,
                remaining * 55,
            )
        )

        overlay = pygame.Surface(
            (
                self.width,
                self.height,
            ),
            pygame.SRCALPHA,
        )

        overlay.fill(
            (
                255,
                215,
                40,
                alpha,
            )
        )

        self.screen.blit(
            overlay,
            (
                0,
                0,
            ),
        )

        text = self.font_large.render(
            "⚽ GOAL!",
            True,
            (
                255,
                245,
                120,
            ),
        )

        rect = text.get_rect(
            center=(
                self.width // 2,
                FIELD_BOTTOM
                - 40,
            )
        )

        self.screen.blit(
            text,
            rect,
        )

    # ======================================================
    # CLOSE
    # ======================================================

    def close(self):

        if self.initialized:

            pygame.quit()

            self.initialized = False