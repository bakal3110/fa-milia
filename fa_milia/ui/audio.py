"""Proste odtwarzanie plików dźwiękowych przez Qt Multimedia."""

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, QVariantAnimation
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
        self._fade: QVariantAnimation | None = None  # trwające wyciszanie

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
        self._cancel_fade()
        player.stop()
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.play()

    def is_playing(self) -> bool:
        return (self._player is not None
                and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

    def stop(self) -> None:
        self._cancel_fade()
        if self._player is not None:
            self._player.stop()

    def fade_out(self, duration_ms: int = 600) -> None:
        """Łagodnie wycisza i zatrzymuje dźwięk (np. muzykę w tle)."""
        if not self.is_playing() or self._fade is not None:
            return
        # QVariantAnimation płynnie zmienia wartość od startValue do endValue
        # w zadanym czasie; przy każdej zmianie ustawiamy głośność.
        self._fade = QVariantAnimation(self)
        self._fade.setStartValue(self._volume)
        self._fade.setEndValue(0.0)
        self._fade.setDuration(duration_ms)
        self._fade.valueChanged.connect(lambda value: self._output.setVolume(float(value)))
        self._fade.finished.connect(self.stop)
        self._fade.start()

    def _cancel_fade(self) -> None:
        if self._fade is not None:
            self._fade.stop()
            self._fade.deleteLater()
            self._fade = None
        if self._output is not None:
            self._output.setVolume(self._volume)

    def set_volume(self, volume: float) -> None:
        """Głośność od 0.0 do 1.0."""
        self._volume = volume
        if self._output is not None and self._fade is None:
            self._output.setVolume(volume)
