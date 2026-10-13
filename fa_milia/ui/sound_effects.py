"""Odtwarzanie dźwięków efektów z folderu sounds/ (bonus, koniec czasu, …)."""

from pathlib import Path

from PySide6.QtCore import QObject

from fa_milia.core.sounds import find_sound
from fa_milia.ui.audio import AudioPlayer


class SoundEffects(QObject):
    def __init__(self, sounds_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sounds_dir = sounds_dir
        self._volume = 0.8
        # Osobny odtwarzacz dla każdego efektu – dzięki temu np. „dobra odpowiedź”
        # nie urywa dźwięku „bonus”, jeśli zagrają tuż po sobie.
        self._players: dict[str, AudioPlayer] = {}

    def set_volume(self, volume: float) -> None:
        self._volume = volume
        for player in self._players.values():
            player.set_volume(volume)

    def play(self, name: str) -> None:
        # Plik szukamy przy każdym odtworzeniu – można więc dorzucać dźwięki
        # do folderu w trakcie działania programu.
        path = find_sound(self._sounds_dir, name)
        if path is None:
            return  # brak pliku = brak dźwięku, bez błędu
        if name not in self._players:
            player = AudioPlayer(self)
            player.set_volume(self._volume)
            self._players[name] = player
        self._players[name].play(path)

    def stop_all(self) -> None:
        for player in self._players.values():
            player.stop()
