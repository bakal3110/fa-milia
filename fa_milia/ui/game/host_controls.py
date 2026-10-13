"""Sterowanie prowadzącego: zawodnicy, punkty, poprawna odpowiedź, przebieg gry.

W etapie E2 ten panel jest paskiem pod ekranem gry. W etapie E3 trafi do
osobnego okna na laptopie prowadzącego.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.game_state import Phase
from fa_milia.core.models import ContentKind
from fa_milia.ui.game.controller import GameController
from fa_milia.ui.game.widgets import format_points

HOST_STYLE = """
#HostControls { background: #e9ecf3; }
#PlayerCard { background: white; border: 1px solid #c5cbd8; border-radius: 6px; }
#PlayerName { font-weight: bold; }
#PlayerScore { font-size: 15pt; font-weight: bold; }
#AnswerLabel { font-size: 13pt; color: #8a5a00; font-weight: bold; }
#MessageLabel { color: #b03030; }
"""


def _button(text: str, tooltip: str = "") -> QPushButton:
    button = QPushButton(text)
    # Przyciski nie przejmują fokusu klawiatury – inaczej spacja „klikałaby”
    # ostatnio użyty przycisk, zamiast działać jako „dalej”.
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    button.setToolTip(tooltip)
    return button


class PlayerCard(QFrame):
    """Karta zawodnika: imię, wynik i przyciski oceny odpowiedzi."""

    mark_requested = Signal(int, bool)  # (indeks zawodnika, czy dobrze)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerCard")
        self._index = index
        self._name = QLabel()
        self._name.setObjectName("PlayerName")
        self._score = QLabel()
        self._score.setObjectName("PlayerScore")
        self._good = _button("✔ Dobrze")
        self._bad = _button("✘ Źle")
        self._good.setStyleSheet("color: #1d7a3a;")
        self._bad.setStyleSheet("color: #b03030;")
        self._good.clicked.connect(lambda: self.mark_requested.emit(self._index, True))
        self._bad.clicked.connect(lambda: self.mark_requested.emit(self._index, False))

        buttons = QHBoxLayout()
        buttons.addWidget(self._good)
        buttons.addWidget(self._bad)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(self._name, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._score, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(buttons)

    def update_card(self, name: str, score: int, can_mark: bool, mark: bool | None,
                    value: int) -> None:
        self._name.setText(name)
        self._score.setText(format_points(score))
        self._good.setEnabled(can_mark and mark is None)
        self._bad.setEnabled(can_mark and mark is None)
        # Po ocenie przycisk pokazuje, ile punktów przyznano/odjęto.
        self._good.setText(f"✔ {format_points(value, signed=True)}" if mark is True else "✔ Dobrze")
        self._bad.setText(f"✘ {format_points(-value)}" if mark is False else "✘ Źle")


class HostControls(QWidget):
    menu_requested = Signal()

    def __init__(self, controller: GameController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HostControls")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(HOST_STYLE)
        self._controller = controller
        self._cards: list[PlayerCard] = []

        self._info = QLabel()
        self._answer = QLabel()
        self._answer.setObjectName("AnswerLabel")
        self._answer.setWordWrap(True)
        self._message = QLabel()
        self._message.setObjectName("MessageLabel")

        self._cards_layout = QHBoxLayout()

        self._reveal_button = _button("Odsłoń odpowiedź", "Spacja")
        self._close_button = _button("Wróć do planszy")
        self._next_button = _button("Dalej", "Spacja")
        self._end_round_button = _button("Zakończ rundę")
        self._undo_button = _button("↶ Cofnij", "Ctrl+Z")
        self._menu_button = _button("Menu", "Esc")
        self._reveal_button.clicked.connect(controller.reveal_answer)
        self._close_button.clicked.connect(controller.close_question)
        self._next_button.clicked.connect(controller.advance)
        self._end_round_button.clicked.connect(self._confirm_end_round)
        self._undo_button.clicked.connect(controller.undo)
        self._menu_button.clicked.connect(self.menu_requested)

        actions = QHBoxLayout()
        for button in (self._reveal_button, self._close_button, self._next_button,
                       self._end_round_button):
            actions.addWidget(button)
        actions.addStretch()
        actions.addWidget(self._message)
        actions.addWidget(self._undo_button)
        actions.addWidget(self._menu_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.addWidget(self._info)
        layout.addWidget(self._answer)
        layout.addLayout(self._cards_layout)
        layout.addLayout(actions)

        controller.state_changed.connect(self.refresh)
        controller.message.connect(self._message.setText)

    def _rebuild_cards(self, count: int) -> None:
        """Tworzy karty zawodników (tylko gdy zmieni się ich liczba)."""
        for card in self._cards:
            card.deleteLater()
        self._cards = []
        while self._cards_layout.count():
            self._cards_layout.takeAt(0)
        for index in range(count):
            card = PlayerCard(index)
            card.mark_requested.connect(self._controller.mark)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

    def refresh(self) -> None:
        state = self._controller.state
        if state is None:
            return
        if len(self._cards) != len(state.players):
            self._rebuild_cards(len(state.players))

        in_question = state.phase == Phase.QUESTION
        current = state.current
        for index, (card, player) in enumerate(zip(self._cards, state.players)):
            mark = current.marks.get(index) if current else None
            card.update_card(player.name, player.score, in_question, mark,
                             current.value if current else 0)

        # Opis sytuacji i poprawna odpowiedź – widoczne tylko dla prowadzącego.
        if in_question:
            question = state.current_question()
            kind = {ContentKind.IMAGE: " (obraz)", ContentKind.SOUND: " (dźwięk)"}.get(
                question.kind, "")
            status = "odsłonięta" if current.revealed else "ukryta przed graczami"
            self._info.setText(f"<b>{state.current_category().name}</b> · "
                               f"{format_points(current.value)} pkt{kind} · odpowiedź {status}")
            self._answer.setText(f"Odpowiedź: {question.answer}")
        else:
            self._answer.setText("")
            match state.phase:
                case Phase.BOARD:
                    self._info.setText(f"<b>Runda {state.round.number}</b> · pozostało pól: "
                                       f"{state.round.remaining()} · wybierz pole na planszy")
                case Phase.ROUND_END:
                    self._info.setText(f"<b>Koniec rundy {state.round.number}</b>")
                case Phase.FINISHED:
                    self._info.setText("<b>Koniec gry</b>")

        self._reveal_button.setVisible(in_question and not current.revealed)
        self._close_button.setVisible(in_question)
        self._close_button.setText("Wróć do planszy" if current and current.marks
                                   else "Nikt – wróć do planszy")
        self._next_button.setVisible(state.phase == Phase.ROUND_END)
        self._end_round_button.setVisible(state.phase == Phase.BOARD)
        self._undo_button.setEnabled(self._controller.can_undo())
        last = self._controller.last_action()
        self._undo_button.setToolTip(f"Ctrl+Z – cofnij: {last}" if last else "Ctrl+Z")

    def _confirm_end_round(self) -> None:
        state = self._controller.state
        answer = QMessageBox.question(
            self,
            "Zakończyć rundę?",
            f"Na planszy zostało jeszcze {state.round.remaining()} pól.\n"
            f"Czy na pewno zakończyć rundę {state.round.number}?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._controller.end_round()
