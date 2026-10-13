"""Osobne okno ekranu gry – wyświetlane na telewizorze lub rzutniku."""

from PySide6.QtGui import QCloseEvent, QScreen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from fa_milia.config import APP_NAME


class GameWindow(QWidget):
    def __init__(self) -> None:
        # Brak rodzica = samodzielne okno najwyższego poziomu.
        super().__init__(None)
        self.setWindowTitle(f"{APP_NAME} – ekran gry")
        self.setStyleSheet("background: #0b1a4a;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._allow_close = False

    def attach(self, widget: QWidget) -> None:
        """Umieszcza w oknie widżet ekranu gry (zabierając go z poprzedniego miejsca)."""
        self._layout.addWidget(widget)
        widget.show()

    def show_on(self, screen: QScreen, fullscreen: bool) -> None:
        self._allow_close = False
        # Na Waylandzie (domyślnie w KDE Plasma) program nie może sam ustawiać
        # położenia okien, ale może poprosić o pełny ekran na konkretnym monitorze.
        self.setScreen(screen)
        self.setGeometry(screen.availableGeometry())
        if fullscreen:
            self.showFullScreen()
        else:
            self.showMaximized()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def release(self) -> None:
        """Chowa okno (np. po zakończeniu gry)."""
        self._allow_close = True
        self.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Przypadkowe zamknięcie okna na telewizorze (Alt+F4) nie przerywa gry.
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
