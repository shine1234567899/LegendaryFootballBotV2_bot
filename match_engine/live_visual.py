import asyncio
from dataclasses import dataclass, field
from typing import Optional

from .engine import MatchEvent


# ==========================================================
# VISUAL SCENE
# ==========================================================

@dataclass
class VisualScene:

    event_type: str

    duration: float

    player_name: Optional[str] = None

    secondary_player_name: Optional[str] = None

    metadata: dict = field(
        default_factory=dict
    )


# ==========================================================
# LIVE VISUAL ENGINE
# ==========================================================

class LiveVisualEngine:

    def __init__(self):

        self.scenes: list[
            VisualScene
        ] = []

        self.running = False

    # ======================================================
    # EVENT → SCENE
    # ======================================================

    def create_scene(
        self,
        event: MatchEvent,
    ) -> VisualScene:

        durations = {
            "KICKOFF": 2.0,
            "PASS": 1.2,
            "BUILD_UP": 1.5,
            "DRIBBLE": 1.8,
            "CROSS": 1.5,
            "SHOT": 1.8,
            "SAVE": 1.8,
            "GOAL": 3.5,
            "FOUL": 1.5,
            "CORNER": 1.5,
            "COUNTER_ATTACK": 2.2,
            "INTERCEPTION": 1.3,
            "TACKLE": 1.4,
            "CLEARANCE": 1.4,
            "FULL_TIME": 3.0,
        }

        duration = durations.get(
            event.event_type,
            1.5,
        )

        return VisualScene(
            event_type=event.event_type,
            duration=duration,
            player_name=(
                event.player_name
            ),
            secondary_player_name=(
                event.secondary_player_name
            ),
            metadata=event.metadata,
        )

    # ======================================================
    # RECEIVE LIVE EVENT
    # ======================================================

    async def on_match_event(
        self,
        event: MatchEvent,
    ):

        scene = self.create_scene(
            event
        )

        self.scenes.append(scene)

        # Pour l'instant on simule
        # la durée de la scène.
        await self.play_scene(
            scene
        )

    # ======================================================
    # PLAY SCENE
    # ======================================================

    async def play_scene(
        self,
        scene: VisualScene,
    ):

        self.running = True

        await asyncio.sleep(
            scene.duration
        )

        self.running = False

    # ======================================================
    # RESET
    # ======================================================

    def reset(self):

        self.scenes.clear()

        self.running = False