"""Panel prowadzącego: zawodnicy, punkty, poprawna odpowiedź i sterowanie grą.

Panel działa w dwóch trybach:
- dwa ekrany: zajmuje całe okno na laptopie prowadzącego,
- jeden ekran: jest nakładką na ekran gry (F2 pokazuje/ukrywa). Wtedy
  odpowiedź jest zasłonięta, dopóki prowadzący nie przytrzyma „Pokaż mi”,
  bo ekran może być zdublowany na telewizorze.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
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

HIDDEN_ANSWER = "●●●●●●  (przytrzymaj „Pokaż mi”)"


def host_style(scale: float) -> str:
    """Arkusz stylów panelu. Rozmiary czcionek mnożymy przez skalę z ustawień."""

    def pt(size: float) -> str:
        return f"{size * scale:.1f}pt"

    return f"""
    #HostPanel {{ background: #e9ecf3; }}
    #HostPanel[overlay="true"] {{ background: rgba(233, 236, 243, 240);
                                 border-top: 3px solid #f2c94c; }}
    #HostPanel QLabel, #HostPanel QPushButton {{ font-size: {pt(11)}; }}
    #HostPanel QPushButton {{ padding: {4 * scale:.0f}px {10 * scale:.0f}px; }}
    #HostPanel #InfoLabel {{ font-size: {pt(13)}; }}
    #HostPanel #TurnLabel {{ font-size: {pt(13)}; color: #8a5a00; font-weight: bold; }}
    #HostPanel #AnswerBox {{ background: #fff6d5; border: 1px solid #e0c060; border-radius: 6px; }}
    #HostPanel #QuestionLabel {{ font-size: {pt(12)}; color: #333; }}
    #HostPanel #AnswerLabel {{ font-size: {pt(17)}; font-weight: bold; color: #5a3d00; }}
    #HostPanel #MessageLabel {{ color: #b03030; }}
    #HostPanel #PlayerRow {{ background: white; border: 1px solid #c5cbd8; border-radius: 6px; }}
    #HostPanel #PlayerRow[lastCorrect="true"] {{ background: #fff8dc; border: 3px solid #e2b007; }}
    #HostPanel #PlayerName {{ font-size: {pt(14)}; font-weight: bold; }}
    #HostPanel #PlayerScore {{ font-size: {pt(16)}; font-weight: bold; }}
    #HostPanel #Star {{ font-size: {pt(16)}; color: #e2b007; }}
    #HostPanel #GoodButton {{ color: #1d7a3a; font-weight: bold; }}
    #HostPanel #BadButton {{ color: #b03030; font-weight: bold; }}
    """


def _button(text: str, tooltip: str = "", name: str = "") -> QPushButton:
    button = QPushButton(text)
    # Przyciski nie przejmują fokusu klawiatury – inaczej spacja „klikałaby”
    # ostatnio użyty przycisk, zamiast działać jako „dalej”.
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    button.setToolTip(tooltip)
    if name:
        button.setObjectName(name)
    return button


def _set_property(widget: QWidget, name: str, value) -> None:
    """Zmienia właściwość używaną w arkuszu stylów i odświeża wygląd widżetu.

    Qt nie przelicza stylów sam po zmianie właściwości, stąd unpolish/polish.
    """
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class PlayerRow(QFrame):
    """Wiersz zawodnika: znacznik ★, imię, wynik, ocena odpowiedzi, korekta."""

    mark_requested = Signal(int, bool)  # (indeks zawodnika, czy dobrze)
    adjust_requested = Signal(int)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerRow")
        self._index = index
        self._star = QLabel()
        self._star.setObjectName("Star")
        self._star.setFixedWidth(28)
        self._name = QLabel()
        self._name.setObjectName("PlayerName")
        self._score = QLabel()
        self._score.setObjectName("PlayerScore")
        self._score.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._score.setMinimumWidth(90)
        self._good = _button("✔ Dobrze", name="GoodButton")
        self._bad = _button("✘ Źle", name="BadButton")
        self._adjust = _button("± Korekta", "Ręczna zmiana punktów")
        self._good.clicked.connect(lambda: self.mark_requested.emit(self._index, True))
        self._bad.clicked.connect(lambda: self.mark_requested.emit(self._index, False))
        self._adjust.clicked.connect(lambda: self.adjust_requested.emit(self._index))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self._star)
        layout.addWidget(self._name, stretch=1)
        layout.addWidget(self._score)
        layout.addSpacing(12)
        layout.addWidget(self._good)
        layout.addWidget(self._bad)
        layout.addWidget(self._adjust)

    def update_row(self, name: str, score: int, can_mark: bool, mark: bool | None,
                   value: int, last_correct: bool) -> None:
        self._name.setText(name)
        self._score.setText(format_points(score))
        self._star.setText("★" if last_correct else "")
        self.setToolTip("Ostatnio odpowiedział(a) dobrze" if last_correct else "")
        _set_property(self, "lastCorrect", last_correct)
        self._good.setEnabled(can_mark and mark is None)
        self._bad.setEnabled(can_mark and mark is None)
        # Po ocenie przycisk pokazuje, ile punktów przyznano/odjęto.
        self._good.setText(f"✔ {format_points(value, signed=True)}" if mark is True else "✔ Dobrze")
        self._bad.setText(f"✘ {format_points(-value)}" if mark is False else "✘ Źle")


class HostPanel(QWidget):
    menu_requested = Signal()
    hide_requested = Signal()  # „Ukryj (F2)” w trybie nakładki

    def __init__(self, controller: GameController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HostPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._controller = controller
        self._rows: list[PlayerRow] = []
        self._overlay = False
        self._peeking = False  # czy prowadzący trzyma wciśnięte „Pokaż mi”

        # --- Informacje ---
        self._info = QLabel()
        self._info.setObjectName("InfoLabel")
        self._turn = QLabel()
        self._turn.setObjectName("TurnLabel")
        self._hide_button = _button("Ukryj panel (F2)")
        self._hide_button.clicked.connect(self.hide_requested)
        info_row = QHBoxLayout()
        info_row.addWidget(self._info, stretch=1)
        info_row.addWidget(self._turn)
        info_row.addWidget(self._hide_button)

        # --- Odpowiedź (tylko dla prowadzącego) ---
        self._answer_box = QFrame()
        self._answer_box.setObjectName("AnswerBox")
        self._question_text = QLabel()
        self._question_text.setObjectName("QuestionLabel")
        self._question_text.setWordWrap(True)
        self._answer = QLabel()
        self._answer.setObjectName("AnswerLabel")
        self._answer.setWordWrap(True)
        self._answer.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._peek_button = _button("Pokaż mi", "Przytrzymaj, aby zobaczyć odpowiedź")
        # pressed/released – odpowiedź widać tylko, dopóki przycisk jest wciśnięty.
        self._peek_button.pressed.connect(lambda: self._set_peeking(True))
        self._peek_button.released.connect(lambda: self._set_peeking(False))
        answer_row = QHBoxLayout()
        answer_row.addWidget(self._answer, stretch=1)
        answer_row.addWidget(self._peek_button)
        answer_layout = QVBoxLayout(self._answer_box)
        answer_layout.addWidget(self._question_text)
        answer_layout.addLayout(answer_row)

        # --- Zawodnicy ---
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(4)

        # --- Sterowanie ---
        self._reveal_button = _button("Odsłoń odpowiedź", "Spacja")
        self._close_button = _button("Wróć do planszy")
        self._next_button = _button("Dalej", "Spacja")
        self._end_round_button = _button("Zakończ rundę")
        self._scores_button = _button("Pokaż wyniki na ekranie")
        self._undo_button = _button("↶ Cofnij", "Ctrl+Z")
        self._menu_button = _button("Menu", "Esc")
        self._reveal_button.clicked.connect(controller.reveal_answer)
        self._close_button.clicked.connect(controller.close_question)
        self._next_button.clicked.connect(controller.advance)
        self._end_round_button.clicked.connect(self._confirm_end_round)
        self._scores_button.clicked.connect(controller.toggle_scores)
        self._undo_button.clicked.connect(controller.undo)
        self._menu_button.clicked.connect(self.menu_requested)

        self._message = QLabel()
        self._message.setObjectName("MessageLabel")
        self._message.setWordWrap(True)

        actions = QGridLayout()
        actions.addWidget(self._reveal_button, 0, 0)
        actions.addWidget(self._close_button, 0, 1)
        actions.addWidget(self._next_button, 0, 2)
        actions.addWidget(self._end_round_button, 0, 3)
        actions.addWidget(self._scores_button, 1, 0)
        actions.addWidget(self._undo_button, 1, 1)
        actions.addWidget(self._menu_button, 1, 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.addLayout(info_row)
        layout.addWidget(self._answer_box)
        layout.addLayout(self._rows_layout)
        layout.addLayout(actions)
        layout.addWidget(self._message)
        layout.addStretch()

        controller.state_changed.connect(self.refresh)
        controller.message.connect(self._message.setText)
        self.set_scale(1.0)

    # --- Konfiguracja ------------------------------------------------------

    def set_scale(self, scale: float) -> None:
        self.setStyleSheet(host_style(scale))

    def set_overlay(self, overlay: bool) -> None:
        """Tryb nakładki: odpowiedź zasłonięta, przycisk „Ukryj panel”."""
        self._overlay = overlay
        self._peeking = False
        _set_property(self, "overlay", overlay)
        self._hide_button.setVisible(overlay)
        self.refresh()

    def show_message(self, text: str) -> None:
        self._message.setText(text)

    # --- Odświeżanie -------------------------------------------------------

    def _rebuild_rows(self, count: int) -> None:
        for row in self._rows:
            row.deleteLater()
        self._rows = []
        for index in range(count):
            row = PlayerRow(index)
            row.mark_requested.connect(self._controller.mark)
            row.adjust_requested.connect(self._ask_adjustment)
            self._rows_layout.addWidget(row)
            # Qt pokazuje nowe widżety w układzie z opóźnieniem; show() od razu
            # sprawia, że są wliczane do wymaganej wysokości panelu.
            row.show()
            self._rows.append(row)

    def refresh(self) -> None:
        state = self._controller.state
        if state is None:
            return
        if len(self._rows) != len(state.players):
            self._rebuild_rows(len(state.players))

        in_question = state.phase == Phase.QUESTION
        current = state.current
        for index, (row, player) in enumerate(zip(self._rows, state.players)):
            mark = current.marks.get(index) if current else None
            row.update_row(player.name, player.score, in_question, mark,
                           current.value if current else 0, index == state.last_correct)

        if state.last_correct is None:
            self._turn.setText("★ Wybiera: dowolny zawodnik")
        else:
            self._turn.setText(f"★ Ostatnio dobrze: {state.players[state.last_correct].name}")

        self._answer_box.setVisible(in_question)
        if in_question:
            question = state.current_question()
            kind = {ContentKind.IMAGE: " (obraz)", ContentKind.SOUND: " (dźwięk)"}.get(
                question.kind, "")
            status = "odsłonięta" if current.revealed else "ukryta przed graczami"
            self._info.setText(f"<b>{state.current_category().name}</b> · "
                               f"{format_points(current.value)} pkt{kind} · odpowiedź {status}")
            self._question_text.setText(f"Pytanie: {question.text}" if question.text
                                        else "Pytanie: (bez tekstu)")
            self._update_answer_text()
        else:
            match state.phase:
                case Phase.BOARD:
                    self._info.setText(f"<b>Runda {state.round.number}</b> · pozostało pól: "
                                       f"{state.round.remaining()}")
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
        self._scores_button.setVisible(state.phase in (Phase.BOARD, Phase.QUESTION))
        self._scores_button.setText("Pokaż grę na ekranie" if self._controller.show_scores
                                    else "Pokaż wyniki na ekranie")
        self._undo_button.setEnabled(self._controller.can_undo())
        last = self._controller.last_action()
        self._undo_button.setToolTip(f"Ctrl+Z – cofnij: {last}" if last else "Ctrl+Z")

    def _update_answer_text(self) -> None:
        question = self._controller.state.current_question()
        if question is None:
            return
        hidden = self._overlay and not self._peeking
        self._answer.setText("Odpowiedź: " + (HIDDEN_ANSWER if hidden else question.answer))
        self._peek_button.setVisible(self._overlay)

    def _set_peeking(self, peeking: bool) -> None:
        self._peeking = peeking
        self._update_answer_text()

    # --- Okna dialogowe ----------------------------------------------------

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

    def _ask_adjustment(self, player_index: int) -> None:
        player = self._controller.state.players[player_index]
        # getInt zwraca parę: (liczba, czy kliknięto OK).
        change, accepted = QInputDialog.getInt(
            self,
            "Korekta punktów",
            f"{player.name} ma teraz {format_points(player.score)} pkt.\n"
            "O ile zmienić wynik? (liczba ujemna odejmuje punkty)",
            0, -100000, 100000, 100,
        )
        if accepted and change != 0:
            self._controller.adjust_score(player_index, change)
