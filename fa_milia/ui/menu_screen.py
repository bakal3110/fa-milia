"""Menu główne."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from fa_milia.config import APP_NAME
from fa_milia.ui.style import MENU_STYLE

# (klucz akcji, napis na przycisku)
MENU_ITEMS = [
    ("new_game", "Nowa gra"),
    ("continue", "Kontynuuj grę"),
    ("categories", "Kategorie"),
    ("finals", "Pytania finałowe"),
    ("sets", "Zestawy"),
    ("transfer", "Import / Eksport"),
    ("settings", "Ustawienia"),
    ("quit", "Wyjście"),
]


class MenuScreen(QWidget):
    """Ekran z listą przycisków. Kliknięcie wysyła sygnał z kluczem akcji."""

    # Signal to „powiadomienie”, które inne obiekty mogą odbierać
    # (connect). Menu nie musi wiedzieć, kto i jak zareaguje na kliknięcie.
    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MenuScreen")
        # Bez tego atrybutu tło z arkusza stylów nie byłoby rysowane.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(MENU_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setObjectName("MenuTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("rodzinny teleturniej")
        subtitle.setObjectName("MenuSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        self._buttons: dict[str, QPushButton] = {}
        for key, label in MENU_ITEMS:
            button = QPushButton(label)
            button.setFixedWidth(440)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            # lambda z domyślnym argumentem `key=key` „zamraża” bieżącą wartość.
            # Bez tego wszystkie przyciski wysyłałyby ostatni klucz z pętli.
            button.clicked.connect(lambda _checked=False, key=key: self.action_requested.emit(key))
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._buttons[key] = button

        layout.addSpacing(24)
        self._info = QLabel()
        self._info.setObjectName("MenuInfo")
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info)

    def set_action_enabled(self, key: str, enabled: bool, tooltip: str = "") -> None:
        button = self._buttons[key]
        button.setEnabled(enabled)
        button.setToolTip(tooltip)

    def set_info(self, text: str) -> None:
        self._info.setText(text)

    def focus_first_enabled(self) -> None:
        for button in self._buttons.values():
            if button.isEnabled():
                button.setFocus()
                return
