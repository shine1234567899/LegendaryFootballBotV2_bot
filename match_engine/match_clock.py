import asyncio
import time


class MatchClock:

    def __init__(
        self,
        match_minutes: int = 90,
        seconds_per_match_minute: float = 0.25,
    ):

        self.match_minutes = match_minutes

        self.seconds_per_match_minute = (
            seconds_per_match_minute
        )

        self.current_minute = 0

        self.running = False

    # ======================================================
    # DURATION
    # ======================================================

    @property
    def total_duration(self):

        return (
            self.match_minutes
            * self.seconds_per_match_minute
        )

    # ======================================================
    # RUN
    # ======================================================

    async def run(self):

        self.running = True

        self.current_minute = 0

        for minute in range(
            1,
            self.match_minutes + 1,
        ):

            if not self.running:
                break

            self.current_minute = minute

            await asyncio.sleep(
                self.seconds_per_match_minute
            )

        self.running = False

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        self.running = False

    # ======================================================
    # RESET
    # ======================================================

    def reset(self):

        self.current_minute = 0

        self.running = False