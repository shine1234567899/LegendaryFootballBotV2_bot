import asyncio
import random

from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

from .events import (
    EventGenerator,
    PASS,
    BUILD_UP,
    DRIBBLE,
    CROSS,
    SHOT,
    GOAL,
    FOUL,
    CORNER,
    COUNTER_ATTACK,
    SAVE,
    INTERCEPTION,
    TACKLE,
    CLEARANCE,
)

from .match_clock import MatchClock


# ==========================================================
# CALLBACK
# ==========================================================

EventCallback = Callable[
    ["MatchEvent"],
    Awaitable[None],
]


# ==========================================================
# TEAM
# ==========================================================

@dataclass
class MatchTeam:

    club_id: int
    name: str
    players: list

    formation: str = "4-4-2"
    strength: float = 0.0

    # Players available on the bench.
    bench: list = field(
        default_factory=list
    )


# ==========================================================
# MATCH EVENT
# ==========================================================

@dataclass
class MatchEvent:

    minute: int

    team_id: int
    team_name: str

    event_type: str

    player_id: Optional[int] = None
    player_name: Optional[str] = None

    secondary_player_id: Optional[int] = None
    secondary_player_name: Optional[str] = None

    description: str = ""

    metadata: dict = field(
        default_factory=dict
    )


# ==========================================================
# MATCH RESULT
# ==========================================================

@dataclass
class MatchResult:

    home_team: MatchTeam
    away_team: MatchTeam

    home_score: int = 0
    away_score: int = 0

    events: list = field(
        default_factory=list
    )

    # [home, away]
    statistics: dict = field(
        default_factory=lambda: {
            "shots": [0, 0],
            "shots_on_target": [0, 0],
            "possession": [0, 0],
            "corners": [0, 0],
            "yellow_cards": [0, 0],
            "red_cards": [0, 0],
            "fouls": [0, 0],
        }
    )


# ==========================================================
# ENGINE
# ==========================================================

class MatchEngine:

    # ======================================================
    # MATCH TIMING
    # ======================================================

    MATCH_MINUTES = 90

    # Fast test mode:
    # 0.35 real second = 1 match minute.
    SECONDS_PER_MATCH_MINUTE = 0.35

    # Real-world half-time break.
    HALF_TIME_PAUSE_SECONDS = 30

    # Added time is represented as 90 + X internally,
    # but FULL TIME is always displayed as 90'.
    MAX_STOPPAGE_TIME = 20

    # Visual pause after important events.
    # Important events pause the visual moment only.
    # The match event loop itself NEVER stops.
    GOAL_PAUSE_SECONDS = 0.0
    RED_CARD_PAUSE_SECONDS = 0.0

    def __init__(
        self,
        home_team: MatchTeam,
        away_team: MatchTeam,
        event_callback: Optional[
            EventCallback
        ] = None,
    ):

        self.home_team = home_team
        self.away_team = away_team

        self.event_callback = (
            event_callback
        )

        self.result = MatchResult(
            home_team=home_team,
            away_team=away_team,
        )

        self.current_minute = 0
        self.running = False
        self.clock_paused = False

        # ==================================================
        # HALF TIME / SUBSTITUTIONS
        # ==================================================

        self.half_time = False
        self.substitution_window_open = False
        self.substitution_deadline = None

        # Temporary substitutions made during this
        # half-time window. They are emitted as ONE event
        # at the beginning of the second half.
        self.pending_substitutions = {
            home_team.club_id: [],
            away_team.club_id: [],
        }

        self.completed_substitutions = {
            home_team.club_id: [],
            away_team.club_id: [],
        }

        # ==================================================
        # RED CARDS
        # ==================================================

        self.red_cards = {
            home_team.club_id: set(),
            away_team.club_id: set(),
        }

        # ==================================================
        # ADDED TIME
        # ==================================================

        self.stoppage_time = random.randint(
            0,
            self.MAX_STOPPAGE_TIME,
        )

        # ==================================================
        # CLOCK
        # ==================================================

        self.clock = MatchClock(
            match_minutes=self.MATCH_MINUTES,
            seconds_per_match_minute=(
                self.SECONDS_PER_MATCH_MINUTE
            ),
        )

        self._calculate_strengths()

    # ======================================================
    # STRENGTH
    # ======================================================

    def _calculate_team_strength(
        self,
        team: MatchTeam,
    ) -> float:

        if not team.players:
            return 0.0

        values = []

        for player in team.players:

            try:
                overall = float(
                    getattr(
                        player,
                        "overall",
                        0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                overall = 0.0

            values.append(overall)

        if not values:
            return 0.0

        return sum(values) / len(values)

    def _calculate_strengths(self):

        self.home_team.strength = (
            self._calculate_team_strength(
                self.home_team
            )
        )

        self.away_team.strength = (
            self._calculate_team_strength(
                self.away_team
            )
        )

    # ======================================================
    # PLAYERS
    # ======================================================

    def _player_position(
        self,
        player,
    ) -> str:

        return str(
            getattr(
                player,
                "lineup_position",
                getattr(
                    player,
                    "position",
                    "",
                ),
            )
        ).upper()

    def _players_for_position(
        self,
        team: MatchTeam,
        position: str,
    ):

        return [
            player
            for player in team.players
            if self._player_position(player)
            == position
            and player.id
            not in self.red_cards.get(
                team.club_id,
                set(),
            )
        ]

    def _random_player(
        self,
        team: MatchTeam,
        positions,
    ):

        candidates = []

        for position in positions:
            candidates.extend(
                self._players_for_position(
                    team,
                    position,
                )
            )

        if not candidates:
            return None

        return random.choice(candidates)

    def _find_player(
        self,
        team: MatchTeam,
        player_id,
    ):

        if player_id is None:
            return None

        for player in team.players:

            if player.id == player_id:
                return player

        return None

    # ======================================================
    # OVERALL-BASED MATCH MODEL
    # ======================================================

    def _overall_gap(self, team, opponent):
        return team.strength - opponent.strength

    def _team_performance_factor(self, team, opponent):
        """
        Stronger XIs get a meaningful advantage, but the result
        remains probabilistic so weaker teams can still win.
        """
        gap = self._overall_gap(team, opponent)

        return max(
            0.55,
            min(
                1.45,
                1.0 + gap * 0.025,
            ),
        )

    def _weighted_player(self, team, positions):
        """
        Higher-overall players are more likely to be involved,
        without making lower-overall players impossible.
        """
        candidates = []

        for position in positions:
            candidates.extend(
                self._players_for_position(
                    team,
                    position,
                )
            )

        if not candidates:
            return None

        weights = []

        for player in candidates:
            try:
                overall = float(
                    getattr(
                        player,
                        "overall",
                        70,
                    )
                )
            except (TypeError, ValueError):
                overall = 70.0

            weights.append(
                max(
                    1.0,
                    overall - 45.0,
                )
            )

        return random.choices(
            candidates,
            weights=weights,
            k=1,
        )[0]

    # ======================================================
    # POSSESSION
    # ======================================================

    def _possession_probability(
        self,
        team: MatchTeam,
    ):

        home = self.home_team.strength
        away = self.away_team.strength
        total = home + away

        if total <= 0:
            return 0.5

        probability = (
            team.strength / total
        )

        opponent = (
            self.away_team
            if team is self.home_team
            else self.home_team
        )

        probability += (
            self._overall_gap(
                team,
                opponent,
            )
            * 0.004
        )

        if team is self.home_team:
            probability += 0.03

        probability += random.uniform(
            -0.02,
            0.02,
        )

        return max(
            0.15,
            min(
                0.85,
                probability,
            ),
        )

    def _choose_attacking_team(self):

        probability = (
            self._possession_probability(
                self.home_team
            )
        )

        if random.random() < probability:

            return (
                self.home_team,
                self.away_team,
            )

        return (
            self.away_team,
            self.home_team,
        )

    def _record_possession(
        self,
        team: MatchTeam,
    ):

        index = self._team_index(team)

        self.result.statistics[
            "possession"
        ][index] += 1

    # ======================================================
    # STATISTICS
    # ======================================================

    def _team_index(
        self,
        team: MatchTeam,
    ):

        if team.club_id == self.home_team.club_id:
            return 0

        return 1

    def _update_stat(
        self,
        team: MatchTeam,
        stat: str,
        amount: int = 1,
    ):

        index = self._team_index(team)

        values = self.result.statistics.setdefault(
            stat,
            [0, 0],
        )

        values[index] += amount

    def _finalize_possession(self):

        values = self.result.statistics[
            "possession"
        ]

        home = values[0]
        away = values[1]
        total = home + away

        if total <= 0:

            self.result.statistics[
                "possession"
            ] = [50, 50]

            return

        home_percent = round(
            home / total * 100
        )

        away_percent = (
            100 - home_percent
        )

        self.result.statistics[
            "possession"
        ] = [
            home_percent,
            away_percent,
        ]

    # ======================================================
    # EVENT EMITTER
    # ======================================================

    async def _emit(
        self,
        event: MatchEvent,
    ):

        self.result.events.append(event)

        if self.event_callback:

            await self.event_callback(
                event
            )

    # ======================================================
    # PAUSE
    # ======================================================

    async def _pause_match(
        self,
        seconds: float,
    ):

        self.clock_paused = True

        try:
            await asyncio.sleep(seconds)
        finally:
            self.clock_paused = False

    # ======================================================
    # SUBSTITUTION API
    # ======================================================

    def _find_team(
        self,
        club_id: int,
    ):

        if self.home_team.club_id == club_id:
            return self.home_team

        if self.away_team.club_id == club_id:
            return self.away_team

        return None

    def get_starting_players(
        self,
        club_id: int,
    ):

        team = self._find_team(club_id)

        if team is None:
            return []

        return list(team.players)

    def get_bench_players(
        self,
        club_id: int,
    ):

        team = self._find_team(club_id)

        if team is None:
            return []

        return list(team.bench)

    def get_compatible_substitutes(
        self,
        club_id: int,
        player_id: int,
    ):

        if not self.substitution_window_open:
            return []

        team = self._find_team(club_id)

        if team is None:
            return []

        player_out = self._find_player(
            team,
            player_id,
        )

        if player_out is None:
            return []

        position = self._player_position(
            player_out
        )

        return [
            player
            for player in team.bench
            if self._player_position(player)
            == position
        ]

    def make_substitution(
        self,
        club_id: int,
        player_out_id: int,
        player_in_id: int,
    ):

        if not self.substitution_window_open:

            return (
                False,
                "Substitutions are closed.",
            )

        team = self._find_team(club_id)

        if team is None:

            return (
                False,
                "Team not found.",
            )

        player_out = self._find_player(
            team,
            player_out_id,
        )

        player_in = None

        for player in team.bench:

            if player.id == player_in_id:
                player_in = player
                break

        if player_out is None:

            return (
                False,
                "Starting player not found.",
            )

        if player_in is None:

            return (
                False,
                "Substitute not found.",
            )

        out_position = self._player_position(
            player_out
        )

        in_position = self._player_position(
            player_in
        )

        if out_position != in_position:

            return (
                False,
                "A player can only be replaced "
                "by a player in the same position.",
            )

        # --------------------------------------------------
        # SWAP XI <-> BENCH
        # --------------------------------------------------

        team.players = [
            player_in
            if player.id == player_out_id
            else player
            for player in team.players
        ]

        team.bench = [
            player_out
            if player.id == player_in_id
            else player
            for player in team.bench
        ]

        substitution = {
            "club_id": club_id,
            "team_name": team.name,
            "player_out_id": player_out.id,
            "player_out_name": player_out.name,
            "player_out_position": out_position,
            "player_out_overall": getattr(
                player_out,
                "overall",
                0,
            ),
            "player_in_id": player_in.id,
            "player_in_name": player_in.name,
            "player_in_position": in_position,
            "player_in_overall": getattr(
                player_in,
                "overall",
                0,
            ),
        }

        self.pending_substitutions[
            club_id
        ].append(substitution)

        self.completed_substitutions[
            club_id
        ].append(substitution)

        self._calculate_strengths()

        return (
            True,
            substitution,
        )

    # ======================================================
    # HALF TIME
    # ======================================================

    async def _start_half_time(self):

        self.half_time = True
        self.clock_paused = True
        self.substitution_window_open = True

        # Use loop.time(), not a different wall clock.
        loop = asyncio.get_running_loop()

        self.substitution_deadline = (
            loop.time()
            + self.HALF_TIME_PAUSE_SECONDS
        )

        half_time_event = MatchEvent(
            minute=45,
            team_id=0,
            team_name="MATCH",
            event_type="HALF_TIME",
            description=(
                "⏸️ Half time."
            ),
            metadata={
                "substitutions_open": True,
                "duration_seconds": (
                    self.HALF_TIME_PAUSE_SECONDS
                ),
            },
        )

        await self._emit(
            half_time_event
        )

        # Exactly 30 real seconds.
        await asyncio.sleep(
            self.HALF_TIME_PAUSE_SECONDS
        )

        self.substitution_window_open = False
        self.substitution_deadline = None
        self.clock_paused = False

        # --------------------------------------------------
        # COLLECT ALL CHANGES
        # --------------------------------------------------

        substitutions = []

        substitutions.extend(
            self.pending_substitutions[
                self.home_team.club_id
            ]
        )

        substitutions.extend(
            self.pending_substitutions[
                self.away_team.club_id
            ]
        )

        # --------------------------------------------------
        # SECOND HALF
        # --------------------------------------------------

        # If substitutions happened, they MUST be the first
        # event of the second half.
        if substitutions:

            lines = []

            for sub in substitutions:

                lines.append(
                    (
                        f"🔄 {sub['team_name']}: "
                        f"{sub['player_out_name']} ⬇️ "
                        f"→ {sub['player_in_name']} ⬆️"
                    )
                )

            substitution_event = MatchEvent(
                minute=46,
                team_id=0,
                team_name="MATCH",
                event_type="SUBSTITUTIONS",
                description="\n".join(lines),
                metadata={
                    "substitutions": substitutions,
                    "count": len(substitutions),
                },
            )

            await self._emit(
                substitution_event
            )

        second_half_event = MatchEvent(
            minute=46,
            team_id=0,
            team_name="MATCH",
            event_type="SECOND_HALF",
            description=(
                "▶️ Second half begins."
            ),
            metadata={
                "substitutions": substitutions,
            },
        )

        await self._emit(
            second_half_event
        )

        self.pending_substitutions[
            self.home_team.club_id
        ].clear()

        self.pending_substitutions[
            self.away_team.club_id
        ].clear()

        self.half_time = False

    # ======================================================
    # ACTION PROCESSOR
    # ======================================================

    async def _process_action(
        self,
        attacking_team: MatchTeam,
        defending_team: MatchTeam,
        minute: int,
    ):

        self._record_possession(
            attacking_team
        )

        generator = EventGenerator(
            attacking_team,
            defending_team,
        )

        action = generator.generate()

        if action is None:
            return

        event_type = action.event_type

        # ==================================================
        # GENERAL EVENTS
        # ==================================================

        if event_type in {
            PASS,
            BUILD_UP,
            DRIBBLE,
            CROSS,
            INTERCEPTION,
            TACKLE,
            CLEARANCE,
            CORNER,
            COUNTER_ATTACK,
            FOUL,
        }:

            metadata = dict(
                action.metadata
                or {}
            )

            if event_type == COUNTER_ATTACK:
                metadata["dangerous_attack"] = True

            elif event_type in {
                CROSS,
                DRIBBLE,
            }:
                metadata["attack"] = True

            elif event_type in {
                PASS,
                BUILD_UP,
            }:
                metadata["possession"] = True

            # --------------------------------------------------
            # FOUL
            # --------------------------------------------------

            if event_type == FOUL:

                self._update_stat(
                    attacking_team,
                    "fouls",
                )

            # --------------------------------------------------
            # CORNER
            # --------------------------------------------------

            if event_type == CORNER:

                self._update_stat(
                    attacking_team,
                    "corners",
                )

            # --------------------------------------------------
            # RED CARD
            # --------------------------------------------------

            red_card = bool(
                metadata.get(
                    "red_card",
                    False,
                )
            )

            if (
                event_type == FOUL
                and not red_card
                and random.random() < 0.04
            ):

                red_card = True

            if red_card:

                player = self._find_player(
                    attacking_team,
                    action.player_id,
                )

                if player:

                    self.red_cards[
                        attacking_team.club_id
                    ].add(
                        player.id
                    )

                    self._update_stat(
                        attacking_team,
                        "red_cards",
                    )

                    metadata[
                        "red_card"
                    ] = True

                    red_event = MatchEvent(
                        minute=minute,
                        team_id=(
                            attacking_team.club_id
                        ),
                        team_name=(
                            attacking_team.name
                        ),
                        event_type="RED_CARD",
                        player_id=player.id,
                        player_name=player.name,
                        description=(
                            f"🟥 RED CARD! "
                            f"{player.name} "
                            "is sent off."
                        ),
                        metadata=metadata,
                    )

                    await self._emit(
                        red_event
                    )

                    # Do not stop the event stream after a red card.
                    # Only emit the red-card event and continue.

                    # IMPORTANT: this only ends the current action.
                    # The match loop continues at the next action/minute.
                    return

            # --------------------------------------------------
            # YELLOW CARD
            # --------------------------------------------------

            if (
                event_type == FOUL
                and random.random() < 0.22
            ):

                self._update_stat(
                    attacking_team,
                    "yellow_cards",
                )

                metadata[
                    "yellow_card"
                ] = True

                yellow_event = MatchEvent(
                    minute=minute,
                    team_id=(
                        attacking_team.club_id
                    ),
                    team_name=(
                        attacking_team.name
                    ),
                    event_type="YELLOW_CARD",
                    player_id=(
                        action.player_id
                    ),
                    player_name=(
                        action.player_name
                    ),
                    description=(
                        f"🟨 Yellow card "
                        f"for "
                        f"{action.player_name or 'player'}."
                    ),
                    metadata=metadata,
                )

                await self._emit(
                    yellow_event
                )

            event = MatchEvent(
                minute=minute,
                team_id=(
                    attacking_team.club_id
                ),
                team_name=(
                    attacking_team.name
                ),
                event_type=event_type,
                player_id=(
                    action.player_id
                ),
                player_name=(
                    action.player_name
                ),
                secondary_player_id=(
                    action.secondary_player_id
                ),
                secondary_player_name=(
                    action.secondary_player_name
                ),
                description=(
                    action.description
                ),
                metadata=metadata,
            )

            await self._emit(event)

            return

        # ==================================================
        # SHOT
        # ==================================================

        if event_type == SHOT:

            shooter = self._find_player(
                attacking_team,
                action.player_id,
            )

            goalkeeper = self._find_player(
                defending_team,
                action.secondary_player_id,
            )

            if shooter is None:
                shooter = self._weighted_player(
                    attacking_team,
                    [
                        "ST",
                        "CF",
                        "LW",
                        "RW",
                        "CAM",
                        "CM",
                        "MID",
                    ],
                )

            if shooter is None:
                return

            try:
                shooter_overall = float(
                    getattr(
                        shooter,
                        "overall",
                        70,
                    )
                )
            except (TypeError, ValueError):
                shooter_overall = 70.0

            if goalkeeper is None:
                goalkeeper = self._random_player(
                    defending_team,
                    ["GK"],
                )

            goalkeeper_overall = 70.0

            if goalkeeper:
                try:
                    goalkeeper_overall = float(
                        getattr(
                            goalkeeper,
                            "overall",
                            70,
                        )
                    )
                except (TypeError, ValueError):
                    goalkeeper_overall = 70.0

            self._update_stat(
                attacking_team,
                "shots",
            )

            # IMPORTANT:
            # SHOT is ONLY a shot. It can never change the score
            # and it is never treated as a goal by the UI.
            shot_event = MatchEvent(
                minute=minute,
                team_id=attacking_team.club_id,
                team_name=attacking_team.name,
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
                    f"🎯 {shooter.name} "
                    f"shoots for "
                    f"{attacking_team.name}!"
                ),
                metadata={
                    "shot": True,
                    "result": "pending",
                    "shooter": shooter.name,
                    "shooter_id": shooter.id,
                    "goalkeeper": (
                        goalkeeper.name
                        if goalkeeper
                        else None
                    ),
                },
            )

            await self._emit(
                shot_event
            )

            await asyncio.sleep(0.15)

            difference = (
                shooter_overall
                - goalkeeper_overall
            )

            team_factor = (
                self._team_performance_factor(
                    attacking_team,
                    defending_team,
                )
            )

            probability = (
                0.18
                + difference * 0.0045
            ) * team_factor

            # Keep randomness so an underdog can still score.
            probability += random.uniform(
                -0.025,
                0.025,
            )

            probability = max(
                0.035,
                min(
                    0.55,
                    probability,
                ),
            )

            # ==================================================
            # GOAL CANDIDATE
            # ==================================================

            if random.random() < probability:

                self._update_stat(
                    attacking_team,
                    "shots_on_target",
                )

                # --------------------------------------------------
                # VAR CHECK
                # --------------------------------------------------

                var_check = (
                    random.random() < 0.22
                )

                if var_check:

                    var_reasons = [
                        "possible offside",
                        "possible handball",
                        "possible foul in the build-up",
                    ]

                    reason = random.choice(
                        var_reasons
                    )

                    var_event = MatchEvent(
                        minute=minute,
                        team_id=attacking_team.club_id,
                        team_name=attacking_team.name,
                        event_type="VAR_CHECK",
                        player_id=shooter.id,
                        player_name=shooter.name,
                        description=(
                            f"📺 VAR CHECK — "
                            f"{reason}..."
                        ),
                        metadata={
                            "var": True,
                            "reason": reason,
                            "checking_goal": True,
                            "goal_scorer": shooter.name,
                            "goal_scorer_id": shooter.id,
                        },
                    )

                    await self._emit(
                        var_event
                    )

                    await self._pause_match(
                        0.8
                    )

                    goal_cancelled = (
                        random.random() < 0.18
                    )

                    if goal_cancelled:

                        decision_event = MatchEvent(
                            minute=minute,
                            team_id=attacking_team.club_id,
                            team_name=attacking_team.name,
                            event_type="VAR_DECISION",
                            player_id=shooter.id,
                            player_name=shooter.name,
                            description=(
                                "❌ VAR — GOAL DISALLOWED"
                            ),
                            metadata={
                                "var": True,
                                "decision": "disallowed",
                                "goal_cancelled": True,
                                "reason": reason,
                                "goal_scorer": shooter.name,
                                "goal_scorer_id": shooter.id,
                            },
                        )

                        await self._emit(
                            decision_event
                        )

                        # The shot remains a shot. No GOAL event
                        # is created and the scoreboard is unchanged.
                        shot_event.metadata[
                            "result"
                        ] = "goal_disallowed"

                        await self._pause_match(
                            self.GOAL_PAUSE_SECONDS
                        )

                        return

                    decision_event = MatchEvent(
                        minute=minute,
                        team_id=attacking_team.club_id,
                        team_name=attacking_team.name,
                        event_type="VAR_DECISION",
                        player_id=shooter.id,
                        player_name=shooter.name,
                        description=(
                            "✅ VAR — GOAL CONFIRMED"
                        ),
                        metadata={
                            "var": True,
                            "decision": "confirmed",
                            "goal_confirmed": True,
                            "goal_scorer": shooter.name,
                            "goal_scorer_id": shooter.id,
                        },
                    )

                    await self._emit(
                        decision_event
                    )

                # --------------------------------------------------
                # CONFIRMED GOAL
                # --------------------------------------------------

                if attacking_team is self.home_team:
                    self.result.home_score += 1
                else:
                    self.result.away_score += 1

                goal_event = MatchEvent(
                    minute=minute,
                    team_id=attacking_team.club_id,
                    team_name=attacking_team.name,
                    event_type=GOAL,
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
                        f"⚽ GOAL! "
                        f"{shooter.name} "
                        f"scores for "
                        f"{attacking_team.name}!"
                    ),
                    metadata={
                        "goal": True,
                        "scorer": shooter.name,
                        "scorer_id": shooter.id,
                        "var_checked": var_check,
                        "var_confirmed": True,
                        "home_score": self.result.home_score,
                        "away_score": self.result.away_score,
                    },
                )

                # The GOAL event is emitted ONLY here. Therefore a
                # normal SHOT can never be mistaken for a goal and
                # every valid goal carries the scorer name.
                await self._emit(
                    goal_event
                )

                # Do not stop the event stream after a goal.
                # The clock and subsequent events continue normally.
                return

            # ==================================================
            # SAVE / SHOT ON TARGET
            # ==================================================

            if goalkeeper and random.random() < 0.55:

                self._update_stat(
                    attacking_team,
                    "shots_on_target",
                )

                shot_event.metadata[
                    "result"
                ] = "saved"

                save_event = MatchEvent(
                    minute=minute,
                    team_id=defending_team.club_id,
                    team_name=defending_team.name,
                    event_type=SAVE,
                    player_id=goalkeeper.id,
                    player_name=goalkeeper.name,
                    secondary_player_id=shooter.id,
                    secondary_player_name=shooter.name,
                    description=(
                        f"🧤 {goalkeeper.name} "
                        f"saves the shot "
                        f"from {shooter.name}."
                    ),
                    metadata={
                        "save": True,
                        "shot_on_target": True,
                        "shooter": shooter.name,
                        "shooter_id": shooter.id,
                    },
                )

                await self._emit(
                    save_event
                )

                return

            # ==================================================
            # MISS
            # ==================================================

            shot_event.metadata[
                "result"
            ] = "miss"

            shot_event.description = (
                f"🎯 {shooter.name} "
                "shoots wide."
            )

            return

    # ======================================================
    # RUN ONE MATCH MINUTE
    # ======================================================

    async def _run_minute(
        self,
        minute: int,
    ):

        self.current_minute = minute

        action_count = random.choices(
            [0, 1, 2, 3],
            weights=[
                0.22,
                0.52,
                0.21,
                0.05,
            ],
            k=1,
        )[0]

        for _ in range(action_count):

            if not self.running:
                return

            (
                attacking_team,
                defending_team,
            ) = self._choose_attacking_team()

            await self._process_action(
                attacking_team,
                defending_team,
                minute,
            )

    # ======================================================
    # RUN MATCH
    # ======================================================

    async def _run_half_with_independent_clock(
        self,
        start_minute: int,
        end_minute: int,
    ):
        """
        Run match actions while the match clock advances on its
        own fixed schedule.

        Important:
        - Event processing may take longer than one simulated minute.
        - That must NEVER make the match clock stop.
        - The clock task only advances current_minute.
        - Action tasks are allowed to finish independently.
        """

        loop = asyncio.get_running_loop()
        next_tick = loop.time()

        minute = start_minute

        while (
            minute <= end_minute
            and self.running
        ):
            # The clock is authoritative for the displayed minute.
            self.current_minute = minute

            # Start the football action without allowing its internal
            # sleeps (VAR, shot presentation, etc.) to block the clock.
            action_task = asyncio.create_task(
                self._run_minute(
                    minute
                )
            )

            # Wait exactly until the next simulated minute.
            next_tick += self.SECONDS_PER_MATCH_MINUTE

            remaining = (
                next_tick
                - loop.time()
            )

            if remaining > 0:
                await asyncio.sleep(
                    remaining
                )

            # If the action finished normally, retrieve exceptions.
            # Otherwise let it continue in the background so a slow
            # event can never freeze the match clock.
            if action_task.done():
                try:
                    await action_task
                except asyncio.CancelledError:
                    pass
                except Exception as error:
                    print(
                        "⚠️ ACTION ERROR:",
                        type(error).__name__,
                        error,
                    )

            minute += 1

        # Give the final action a chance to finish, but do not make
        # the match clock depend on it.
        await asyncio.sleep(0)

    async def run(
        self,
        realtime_delay: float = 0.0,
    ) -> MatchResult:

        self.running = True

        self.clock.reset()
        self.clock.running = True

        self.current_minute = 0

        # ==================================================
        # KICKOFF
        # ==================================================

        kickoff_team = random.choice(
            [
                self.home_team,
                self.away_team,
            ]
        )

        kickoff_event = MatchEvent(
            minute=0,
            team_id=kickoff_team.club_id,
            team_name=kickoff_team.name,
            event_type="KICKOFF",
            description=(
                f"🟢 Kick-off! "
                f"{kickoff_team.name} "
                "starts the match."
            ),
        )

        await self._emit(
            kickoff_event
        )

        # ==================================================
        # FIRST HALF
        # ==================================================

        await self._run_half_with_independent_clock(
            1,
            45,
        )

        if not self.running:
            self.clock.stop()
            return self.result

        # ==================================================
        # HALF TIME
        # ==================================================

        await self._start_half_time()

        if not self.running:
            self.clock.stop()
            return self.result

        # ==================================================
        # SECOND HALF
        # ==================================================

        await self._run_half_with_independent_clock(
            46,
            90,
        )

        if not self.running:
            self.clock.stop()
            return self.result

        # ==================================================
        # STOPPAGE TIME
        # ==================================================

        stoppage_event = MatchEvent(
            minute=90,
            team_id=0,
            team_name="MATCH",
            event_type="STOPPAGE_TIME",
            description=(
                f"⏱️ +{self.stoppage_time} "
                "minutes of added time."
            ),
            metadata={
                "stoppage_time": (
                    self.stoppage_time
                ),
            },
        )

        await self._emit(
            stoppage_event
        )

        if self.stoppage_time > 0:

            await self._run_half_with_independent_clock(
                91,
                90 + self.stoppage_time,
            )

        if not self.running:
            self.clock.stop()
            return self.result

        # ==================================================
        # FINALIZE
        # ==================================================

        self._finalize_possession()

        self.clock.stop()
        self.running = False

        # ==================================================
        # WINNER
        # ==================================================

        winner = None

        if (
            self.result.home_score
            > self.result.away_score
        ):

            winner = self.home_team.name

        elif (
            self.result.away_score
            > self.result.home_score
        ):

            winner = self.away_team.name

        # ==================================================
        # FULL TIME
        # ==================================================

        full_time_event = MatchEvent(
            minute=90,
            team_id=0,
            team_name="MATCH",
            event_type="FULL_TIME",
            description=(
                "🏁 Full time: "
                f"{self.home_team.name} "
                f"{self.result.home_score}"
                " - "
                f"{self.result.away_score} "
                f"{self.away_team.name}"
            ),
            metadata={
                "winner": winner,
                "home_score": (
                    self.result.home_score
                ),
                "away_score": (
                    self.result.away_score
                ),
                "stoppage_time": (
                    self.stoppage_time
                ),
                "statistics": (
                    self.result.statistics
                ),
            },
        )

        await self._emit(
            full_time_event
        )

        self.current_minute = 90

        return self.result

    # ======================================================
    # PLAY LIVE
    # ======================================================

    async def play_live(
        self,
        realtime_delay: float = 0.0,
    ) -> MatchResult:

        return await self.run(
            realtime_delay=realtime_delay
        )

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        self.running = False

        self.substitution_window_open = False

        self.substitution_deadline = None

        self.clock.stop()