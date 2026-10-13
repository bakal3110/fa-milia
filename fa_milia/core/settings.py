"""Ustawienia programu zapisywane w settings.json."""

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from fa_milia.core.jsonio import read_json, write_json

MIN_SCALE = 50
MAX_SCALE = 250


def _clamp(value: int, low: int, high: int) -> int:
    """Ogranicza wartość do przedziału [low, high]."""
    return max(low, min(high, value))


@dataclass
class Settings:
    # Nazwa monitora (np. "HDMI-A-1") dla ekranu gry. None = wybór automatyczny.
    game_screen: str | None = None
    fullscreen: bool = True
    game_scale: int = 100  # skalowanie tekstu na ekranie gry, w procentach
    host_scale: int = 100  # skalowanie panelu prowadzącego, w procentach
    # Poniższe ustawienia są używane od etapu E4.
    timer_enabled: bool = False
    question_seconds: int = 30
    final_seconds: int = 60
    volume: int = 80  # 0–100

    def normalized(self) -> "Settings":
        """Zwraca kopię z wartościami poprawionymi do dozwolonych zakresów."""
        return Settings(
            game_screen=self.game_screen or None,
            fullscreen=bool(self.fullscreen),
            game_scale=_clamp(int(self.game_scale), MIN_SCALE, MAX_SCALE),
            host_scale=_clamp(int(self.host_scale), MIN_SCALE, MAX_SCALE),
            timer_enabled=bool(self.timer_enabled),
            question_seconds=_clamp(int(self.question_seconds), 5, 600),
            final_seconds=_clamp(int(self.final_seconds), 5, 600),
            volume=_clamp(int(self.volume), 0, 100),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        # Bierzemy tylko znane klucze – nieznane (np. z nowszej wersji) pomijamy.
        known = {f.name for f in fields(cls)}
        values = {key: value for key, value in data.items() if key in known}
        try:
            return cls(**values).normalized()  # ** przekazuje słownik jako argumenty nazwane
        except (TypeError, ValueError):
            return cls()


def load_settings(path: Path) -> Settings:
    """Wczytuje ustawienia; przy braku lub uszkodzeniu pliku zwraca domyślne."""
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    return Settings.from_dict(data)


def save_settings(path: Path, settings: Settings) -> None:
    write_json(path, asdict(settings.normalized()))
