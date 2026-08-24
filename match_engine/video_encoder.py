import asyncio
import shutil
from pathlib import Path

import numpy as np
import pygame


class LiveVideoEncoder:

    FPS = 30

    def __init__(
        self,
        output_path,
        width,
        height,
    ):

        self.output_path = Path(
            output_path
        )

        self.width = width
        self.height = height

        self.process = None
        self.running = False

    # ======================================================
    # START
    # ======================================================

    async def start(self):

        ffmpeg = shutil.which(
            "ffmpeg"
        )

        if ffmpeg is None:

            raise RuntimeError(
                "FFmpeg was not found in PATH."
            )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [
            ffmpeg,

            "-y",

            "-f",
            "rawvideo",

            "-vcodec",
            "rawvideo",

            "-pix_fmt",
            "rgb24",

            "-s",
            f"{self.width}x{self.height}",

            "-r",
            str(self.FPS),

            "-i",
            "-",

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-pix_fmt",
            "yuv420p",

            str(self.output_path),
        ]

        self.process = (
            await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        )

        self.running = True

    # ======================================================
    # PYGAME SURFACE → RGB24
    # ======================================================

    @staticmethod
    def surface_to_rgb(
        surface,
    ):

        if not isinstance(
            surface,
            pygame.Surface,
        ):

            raise TypeError(
                "Expected a pygame.Surface."
            )

        # pygame.surfarray.array3d()
        # retourne généralement :
        #
        # (width, height, 3)
        #
        # FFmpeg attend :
        #
        # (height, width, 3)

        frame = (
            pygame.surfarray.array3d(
                surface
            )
        )

        frame = np.transpose(
            frame,
            (1, 0, 2),
        )

        frame = np.ascontiguousarray(
            frame,
            dtype=np.uint8,
        )

        return frame

    # ======================================================
    # WRITE FRAME
    # ======================================================

    async def write_frame(
        self,
        surface,
    ):

        if not self.running:
            return

        if self.process is None:
            return

        if self.process.stdin is None:
            return

        frame = self.surface_to_rgb(
            surface
        )

        expected_size = (
            self.width
            * self.height
            * 3
        )

        if frame.nbytes != expected_size:

            raise ValueError(
                "Invalid frame size: "
                f"{frame.shape}. "
                f"Expected "
                f"{self.width}x"
                f"{self.height} RGB."
            )

        try:

            self.process.stdin.write(
                frame.tobytes()
            )

            await self.process.stdin.drain()

        except (
            BrokenPipeError,
            ConnectionResetError,
        ):

            self.running = False

    # ======================================================
    # STOP
    # ======================================================

    async def stop(self):

        if self.process is None:
            return

        if self.process.stdin:

            try:

                self.process.stdin.close()

                await (
                    self.process.stdin
                    .wait_closed()
                )

            except (
                BrokenPipeError,
                ConnectionResetError,
            ):

                pass

        await self.process.wait()

        self.running = False
        self.process = None

    # ======================================================
    # OUTPUT
    # ======================================================

    def exists(self):

        return (
            self.output_path.exists()
            and
            self.output_path.stat().st_size
            > 0
        )