from __future__ import annotations

import random
from pathlib import Path


MUSIC_DIR = Path(__file__).resolve().parent / "music"

SUPPORTED_AUDIO = {
    ".mp3",
    ".m4a",
    ".wav",
    ".ogg",
}


class MusicManager:
    def __init__(self, music_dir: Path = MUSIC_DIR):
        self.music_dir = Path(music_dir)
        self.recent: list[str] = []

    def _tracks(self) -> list[Path]:
        if not self.music_dir.exists():
            return []

        return [
            path
            for path in self.music_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_AUDIO
        ]

    def pick(self) -> Path | None:
        tracks = self._tracks()

        if not tracks:
            return None

        recent_names = set(self.recent)

        available = [
            path for path in tracks
            if path.name not in recent_names
        ]

        if not available:
            self.recent.clear()
            available = tracks

        chosen = random.choice(available)
        self.recent.append(chosen.name)

        max_history = max(1, min(5, len(tracks) - 1))

        if len(self.recent) > max_history:
            self.recent = self.recent[-max_history:]

        return chosen


music_manager = MusicManager()