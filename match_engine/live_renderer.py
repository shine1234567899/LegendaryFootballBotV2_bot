import asyncio
import time

from .engine import MatchEngine
from .renderer import MatchVisualState
from .graphics import MatchGraphics
from .video_encoder import LiveVideoEncoder


# ==========================================================
# LIVE MATCH RENDERER
# ==========================================================

class LiveMatchRenderer:

    FPS = 30

    def __init__(
        self,
        engine: MatchEngine,
        output_path="matches/live_match.mp4",
    ):
        self.engine = engine

        # ==================================================
        # VISUAL STATE
        # ==================================================

        self.state = MatchVisualState(
            engine.home_team,
            engine.away_team,
        )

        # ==================================================
        # GRAPHICS
        # ==================================================

        self.graphics = MatchGraphics(
            self.state,
            engine=engine,
        )

        # ==================================================
        # VIDEO ENCODER
        # ==================================================

        self.encoder = LiveVideoEncoder(
            output_path=output_path,
            width=self.graphics.width,
            height=self.graphics.height,
        )

        # ==================================================
        # RUNTIME STATE
        # ==================================================

        self.running = False

        self.frame_count = 0

        self.processed_events = 0

        self.last_time = time.perf_counter()

    # ======================================================
    # MATCH EVENT CALLBACK
    # ======================================================

    async def on_match_event(self, event):
        """
        Called by the match engine whenever a new event occurs.

        The engine remains responsible for the simulation.
        The renderer only visualizes the event.
        """

        try:
            self.graphics.set_event(event)

        except Exception as error:
            print(
                "⚠️ GRAPHICS EVENT ERROR:",
                type(error).__name__,
                error,
            )

    # ======================================================
    # PROCESS NEW EVENTS
    # ======================================================

    def process_new_events(self):

        events = self.engine.result.events

        total_events = len(events)

        if total_events <= self.processed_events:
            return

        new_events = events[
            self.processed_events:
        ]

        for event in new_events:

            try:
                self.graphics.set_event(event)

            except Exception as error:
                print(
                    "⚠️ GRAPHICS EVENT ERROR:",
                    type(error).__name__,
                    error,
                )

        self.processed_events = total_events

    # ======================================================
    # RENDER ONE FRAME
    # ======================================================

    def render_frame(self):

        self.process_new_events()

        return self.graphics.draw_frame()

    # ======================================================
    # MAIN RENDER LOOP
    # ======================================================

    async def run(self):

        self.running = True

        self.frame_count = 0

        self.processed_events = 0

        # --------------------------------------------------
        # INITIALIZE GRAPHICS
        # --------------------------------------------------

        self.graphics.initialize()

        # --------------------------------------------------
        # START FFMPEG ENCODER
        # --------------------------------------------------

        await self.encoder.start()

        frame_duration = 1.0 / self.FPS

        self.last_time = time.perf_counter()

        try:

            while self.running:

                frame_start = time.perf_counter()

                # ==========================================
                # MATCH EVENTS
                # ==========================================

                self.process_new_events()

                # ==========================================
                # DRAW FRAME
                # ==========================================

                frame = self.graphics.draw_frame()

                # ==========================================
                # SEND FRAME TO FFMPEG
                # ==========================================

                await self.encoder.write_frame(
                    frame
                )

                self.frame_count += 1

                # ==========================================
                # CHECK MATCH END
                # ==========================================

                match_finished = (
                    not self.engine.running
                    and self.engine.current_minute >= 90
                )

                if match_finished:

                    # Allow the final event / FULL TIME
                    # animation to remain visible.

                    final_end = (
                        time.perf_counter()
                        + 0.8
                    )

                    while (
                        time.perf_counter()
                        < final_end
                    ):

                        final_frame_start = (
                            time.perf_counter()
                        )

                        final_frame = (
                            self.graphics.draw_frame()
                        )

                        await self.encoder.write_frame(
                            final_frame
                        )

                        self.frame_count += 1

                        final_elapsed = (
                            time.perf_counter()
                            - final_frame_start
                        )

                        final_delay = (
                            frame_duration
                            - final_elapsed
                        )

                        if final_delay > 0:
                            await asyncio.sleep(
                                final_delay
                            )

                    break

                # ==========================================
                # FRAME PACING
                # ==========================================

                elapsed = (
                    time.perf_counter()
                    - frame_start
                )

                delay = (
                    frame_duration
                    - elapsed
                )

                if delay > 0:
                    await asyncio.sleep(
                        delay
                    )

        except asyncio.CancelledError:

            self.running = False

            raise

        except Exception as error:

            print(
                "❌ RENDERER ERROR:",
                type(error).__name__,
                error,
            )

            raise

        finally:

            self.running = False

            # ==============================================
            # STOP ENCODER
            # ==============================================

            try:

                await self.encoder.stop()

            except Exception as error:

                print(
                    "⚠️ ENCODER STOP ERROR:",
                    type(error).__name__,
                    error,
                )

            # ==============================================
            # CLOSE GRAPHICS
            # ==============================================

            try:

                self.graphics.close()

            except Exception as error:

                print(
                    "⚠️ GRAPHICS CLOSE ERROR:",
                    type(error).__name__,
                    error,
                )

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        self.running = False

        