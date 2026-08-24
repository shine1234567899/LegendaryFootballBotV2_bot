import asyncio
from dataclasses import dataclass

from match_engine.engine import (
    MatchEngine,
    MatchTeam,
)

from match_engine.live_renderer import (
    LiveMatchRenderer,
)


# ==========================================================
# TEST PLAYER
# ==========================================================

@dataclass
class TestPlayer:

    id: int
    name: str
    position: str
    overall: int


# ==========================================================
# CREATE TEAM
# ==========================================================

def create_team(
    club_id: int,
    name: str,
    start_id: int,
):

    players = [

        # GK
        TestPlayer(
            start_id,
            f"{name} GK",
            "GK",
            82,
        ),

        # DEF
        TestPlayer(
            start_id + 1,
            f"{name} DEF1",
            "DEF",
            80,
        ),

        TestPlayer(
            start_id + 2,
            f"{name} DEF2",
            "DEF",
            81,
        ),

        TestPlayer(
            start_id + 3,
            f"{name} DEF3",
            "DEF",
            79,
        ),

        TestPlayer(
            start_id + 4,
            f"{name} DEF4",
            "DEF",
            80,
        ),

        # MID
        TestPlayer(
            start_id + 5,
            f"{name} MID1",
            "MID",
            83,
        ),

        TestPlayer(
            start_id + 6,
            f"{name} MID2",
            "MID",
            82,
        ),

        TestPlayer(
            start_id + 7,
            f"{name} MID3",
            "MID",
            81,
        ),

        # ATT
        TestPlayer(
            start_id + 8,
            f"{name} ATT1",
            "ATT",
            85,
        ),

        TestPlayer(
            start_id + 9,
            f"{name} ATT2",
            "ATT",
            84,
        ),

        TestPlayer(
            start_id + 10,
            f"{name} ATT3",
            "ATT",
            83,
        ),
    ]

    return MatchTeam(
        club_id=club_id,
        name=name,
        players=players,
        formation="4-3-3",
    )


# ==========================================================
# MATCH
# ==========================================================

async def main():

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "🏟️ LIVE MATCH TEST"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    home = create_team(
        1,
        "RED FC",
        1,
    )

    away = create_team(
        2,
        "BLUE FC",
        100,
    )

    engine = MatchEngine(
        home_team=home,
        away_team=away,
    )

    renderer = LiveMatchRenderer(
        engine,
        output_path=(
            "matches/test_match.mp4"
        ),
    )

    # ------------------------------------------------------
    # CONNECT ENGINE → RENDERER
    # ------------------------------------------------------

    engine.event_callback = (
        renderer.on_match_event
    )

    print(
        "⚙️ Engine initialized"
    )

    print(
        f"🏠 {home.name} "
        f"({home.strength:.1f})"
    )

    print(
        f"✈️ {away.name} "
        f"({away.strength:.1f})"
    )

    print(
        "🎥 Renderer initialized"
    )

    print(
        "▶️ Starting match..."
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # ------------------------------------------------------
    # RUN BOTH AT THE SAME TIME
    # ------------------------------------------------------

    await asyncio.gather(
        engine.run(
            realtime_delay=0.05
        ),
        renderer.run(),
    )

    # ------------------------------------------------------
    # RESULT
    # ------------------------------------------------------

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "🏁 MATCH FINISHED"
    )

    print(
        f"⚽ {home.name} "
        f"{engine.result.home_score}"
        " - "
        f"{engine.result.away_score} "
        f"{away.name}"
    )

    print(
        f"🎬 Frames generated: "
        f"{renderer.frame_count}"
    )

    print(
        "🎥 Video: "
        "matches/test_match.mp4"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )