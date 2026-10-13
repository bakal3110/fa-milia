"""Proste odtwarzanie plików dźwiękowych przez Qt Multimedia."""

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    """Odtwarza jeden plik naraz. Brakujący plik po prostu nic nie robi."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Odtwarzacz tworzymy dopiero przy pierwszym użyciu („leniwie”),
        # bo inicjalizacja multimediów chwilę trwa.
        self._player: QMediaPlayer | None = None
        self._output: QAudioOutput | None = None
        self._volume = 1.0

    def _ensure_player(self) -> QMediaPlayer:
        if self._player is None:
            self._output = QAudioOutput(self)
            self._output.setVolume(self._volume)
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(self._output)
        return self._player

    def play(self, path: Path) -> None:
        if not path.is_file():
            return
        player = self._ensure_player()
        player.stop()
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    def set_volume(self, volume: float) -> None:
        """Głośność od 0.0 do 1.0."""
        self._volume = volume
        if self._output is not None:
            self._output.setVolume(volume)
