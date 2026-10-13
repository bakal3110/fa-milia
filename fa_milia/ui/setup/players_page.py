"""Nowa gra, krok 1: liczba zawodników i ich imiona."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fa_milia.config import MAX_PLAYERS, MIN_PLAYERS
from fa_milia.core.game_state import GameError, validate_player_names

DEFAULT_PLAYER_COUNT = 3


def page_title(text: str) -> QLabel:
    """Duży, pogrubiony nagłówek strony (wspólny dla stron przygotowania gry)."""
    label = QLabel(text)
    font = QFont(label.font())
    font.setPointSizeF(font.pointSizeF() * 1.8)
    font.setBold(True)
    label.setFont(font)
    return label


class PlayersPage(QWidget):
    back_requested = Signal()
    players_chosen = Signal(list)  # lista imion

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._count = QSpinBox()
        self._count.setRange(MIN_PLAYERS, MAX_PLAYERS)
        self._count.setValue(DEFAULT_PLAYER_COUNT)
        self._count.valueChanged.connect(self._update_visible_fields)

        self._form = QFormLayout()
        self._form.addRow("Liczba zawodników:", self._count)
        self._name_edits: list[QLineEdit] = []
        for number in range(1, MAX_PLAYERS + 1):
            edit = QLineEdit()
            edit.setMaxLength(20)
            edit.setPlaceholderText(f"Gracz {number}")
            edit.returnPressed.connect(self._focus_next)
            self._form.addRow(f"Zawodnik {number}:", edit)
            self._name_edits.append(edit)

        hint = QLabel("Puste pole = domyślne imię „Gracz N”.")
        hint.setStyleSheet("color: gray;")

        back_button = QPushButton("← Wstecz")
        back_button.clicked.connect(self.back_requested)
        next_button = QPushButton("Dalej: wybór kategorii →")
        next_button.setDefault(True)
        next_button.clicked.connect(self._accept)
        buttons = QHBoxLayout()
        buttons.addWidget(back_button)
        buttons.addStretch()
        buttons.addWidget(next_button)

        column = QVBoxLayout()
        column.addWidget(page_title("Nowa gra – zawodnicy"))
        column.addSpacing(16)
        column.addLayout(self._form)
        column.addWidget(hint)
        column.addSpacing(16)
        column.addLayout(buttons)
        column.addStretch()

        # Formularz wyśrodkowany w poziomie, o stałej szerokości.
        container = QWidget()
        container.setLayout(column)
        container.setFixedWidth(560)
        layout = QHBoxLayout(self)
        layout.addStretch()
        layout.addWidget(container)
        layout.addStretch()

        self._update_visible_fields()

    def prepare(self) -> None:
        """Wywoływane przy wejściu na stronę. Imiona z poprzedniej gry zostają."""
        self._name_edits[0].setFocus()

    def request_back(self) -> None:
        self.back_requested.emit()

    def _update_visible_fields(self) -> None:
        for index, edit in enumerate(self._name_edits):
            self._form.setRowVisible(edit, index < self._count.value())

    def _focus_next(self) -> None:
        """Enter w polu imienia przechodzi do następnego pola albo dalej."""
        visible = self._name_edits[:self._count.value()]
        for index, edit in enumerate(visible):
            if edit.hasFocus():
                if index + 1 < len(visible):
                    visible[index + 1].setFocus()
                else:
                    self._accept()
                return

    def _accept(self) -> None:
        names = [
            edit.text().strip() or edit.placeholderText()
            for edit in self._name_edits[:self._count.value()]
        ]
        try:
            names = validate_player_names(names)
        except GameError as error:
            QMessageBox.warning(self, "Zawodnicy", str(error))
            return
        self.players_chosen.emit(names)
