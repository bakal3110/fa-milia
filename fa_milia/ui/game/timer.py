"""Odliczanie czasu na odpowiedź."""

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

TICK_MS = 100


class GameTimer(QObject):
    """Timer z pauzą.

    QTimer „tyka” co 100 ms, ale pozostały czas liczymy z QElapsedTimer
    (dokładny pomiar upływu czasu), żeby odliczanie się nie spóźniało.
    """

    tick = Signal()  # zmiana stanu lub kolejne „tyknięcie”
    expired = Signal()  # czas minął

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ticker = QTimer(self)
        self._ticker.setInterval(TICK_MS)
        self._ticker.timeout.connect(self._on_tick)
        self._clock = QElapsedTimer()
        self._total = 0.0
        self._remaining_at_start = 0.0  # pozostały czas w chwili (wz)nowienia
        self._active = False  # czy timer jest w użyciu (także w pauzie)
        self._running = False  # czy właśnie odlicza

    # --- Odczyt ------------------------------------------------------------

    @property
    def active(self) -> bool:
        return self._active

    @property
    def running(self) -> bool:
        return self._running

    @property
    def total(self) -> float:
        return self._total

    def remaining(self) -> float:
        """Pozostały czas w sekundach."""
        if self._running:
            elapsed = self._clock.elapsed() / 1000
            return max(0.0, self._remaining_at_start - elapsed)
        return self._remaining_at_start

    # --- Sterowanie --------------------------------------------------------

    def start(self, seconds: float) -> None:
        self._total = seconds
        self._remaining_at_start = seconds
        self._active = True
        self._resume_clock()

    def pause(self) -> None:
        if self._running:
            self._remaining_at_start = self.remaining()
            self._running = False
            self._ticker.stop()
            self.tick.emit()

    def resume(self) -> None:
        if self._active and not self._running and self._remaining_at_start > 0:
            self._resume_clock()

    def toggle_pause(self) -> None:
        if self._running:
            self.pause()
        else:
            self.resume()

    def restart(self) -> None:
        if self._active:
            self.start(self._total)

    def stop(self) -> None:
        """Wyłącza timer całkowicie (znika z ekranu)."""
        if self._active or self._running:
            self._active = False
            self._running = False
            self._ticker.stop()
            self.tick.emit()

    def _resume_clock(self) -> None:
        self._running = True
        self._clock.start()
        self._ticker.start()
        self.tick.emit()

    def _on_tick(self) -> None:
        if self.remaining() <= 0:
            self._remaining_at_start = 0.0
            self._running = False
            self._ticker.stop()
            self.tick.emit()
            self.expired.emit()
        else:
            self.tick.emit()


def format_seconds(seconds: float) -> str:
    """12.3 → „0:13” (zaokrąglamy w górę, żeby „0:00” oznaczało koniec)."""
    whole = int(seconds) + (1 if seconds % 1 > 0 else 0)
    return f"{whole // 60}:{whole % 60:02d}"
