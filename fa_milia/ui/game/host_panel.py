"""Panel prowadzącego: zawodnicy, punkty, poprawna odpowiedź i sterowanie grą.

Panel działa w dwóch trybach:
- dwa ekrany: zajmuje całe okno na laptopie prowadzącego,
- jeden ekran: jest nakładką na ekran gry (F2 pokazuje/ukrywa). Wtedy
  odpowiedź jest zasłonięta, dopóki prowadzący nie przytrzyma „Pokaż mi”,
  bo ekran może być zdublowany na telewizorze.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.game_state import GameState, Phase
from fa_milia.core.models import ContentKind
from fa_milia.ui.game.controller import GameController
from fa_milia.ui.game.timer import GameTimer, format_seconds
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
    #HostPanel #GoodButton:disabled, #HostPanel #BadButton:disabled {{ color: #a8acb5; }}
    #HostPanel #BonusBox, #HostPanel #FinalBox {{ background: #fff0c2; border: 2px solid #e2b007;
                                                 border-radius: 6px; }}
    #HostPanel #BoxTitle {{ font-size: {pt(14)}; font-weight: bold; color: #8a5a00; }}
    #HostPanel #TimerLabel {{ font-size: {pt(16)}; font-weight: bold; }}
    #HostPanel #BonusInfo {{ color: #8a5a00; }}
    #HostPanel QSpinBox, #HostPanel QComboBox {{ font-size: {pt(12)}; }}
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

    def __init__(self, controller: GameController, timer: GameTimer,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HostPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._controller = controller
        self._timer = timer
        self._rows: list[PlayerRow] = []
        self._overlay = False
        self._peeking = False  # czy prowadzący trzyma wciśnięte „Pokaż mi”
        self._final_spins: dict[int, QSpinBox] = {}  # stawki finałowe: zawodnik → pole
        self._bonus_key: tuple | None = None  # które pole bonusowe jest wyświetlane

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.addLayout(info_row)
        layout.addWidget(self._build_answer_box())
        layout.addWidget(self._build_bonus_box())
        layout.addWidget(self._build_final_box())
        layout.addWidget(self._build_timer_row())
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(4)
        layout.addLayout(self._rows_layout)
        layout.addLayout(self._build_actions())
        self._message = QLabel()
        self._message.setObjectName("MessageLabel")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)
        layout.addStretch()

        controller.state_changed.connect(self.refresh)
        controller.message.connect(self._message.setText)
        timer.tick.connect(self._update_timer)
        self.set_scale(1.0)

    # --- Budowa części panelu ----------------------------------------------

    def _build_answer_box(self) -> QFrame:
        """Treść pytania i poprawna odpowiedź – tylko dla prowadzącego."""
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
        box_layout = QVBoxLayout(self._answer_box)
        box_layout.addWidget(self._question_text)
        box_layout.addLayout(answer_row)
        return self._answer_box

    def _build_bonus_box(self) -> QFrame:
        """Bonus: wybór zawodnika i stawki."""
        self._bonus_box = QFrame()
        self._bonus_box.setObjectName("BonusBox")
        title = QLabel("BONUS – kto odpowiada i o ile gra?")
        title.setObjectName("BoxTitle")
        self._bonus_player = QComboBox()
        self._bonus_player.currentIndexChanged.connect(self._update_bonus_limit)
        self._bonus_wager = QSpinBox()
        self._bonus_wager.setSingleStep(100)
        self._bonus_limit = QLabel()
        confirm = _button("Zatwierdź stawkę")
        confirm.clicked.connect(self._confirm_bonus_wager)
        self._bonus_show_button = _button("Pokaż pytanie ▶", "Spacja")
        self._bonus_show_button.clicked.connect(self._controller.show_bonus_question)

        row = QHBoxLayout()
        row.addWidget(QLabel("Zawodnik:"))
        row.addWidget(self._bonus_player, stretch=1)
        row.addWidget(QLabel("Stawka:"))
        row.addWidget(self._bonus_wager)
        row.addWidget(self._bonus_limit)
        row.addWidget(confirm)
        row.addWidget(self._bonus_show_button)
        box_layout = QVBoxLayout(self._bonus_box)
        box_layout.addWidget(title)
        box_layout.addLayout(row)
        return self._bonus_box

    def _build_final_box(self) -> QFrame:
        """Finał: stawki wszystkich uczestników."""
        self._final_box = QFrame()
        self._final_box.setObjectName("FinalBox")
        title = QLabel("FINAŁ – wpisz stawki uczestników (od 0 do ich wyniku)")
        title.setObjectName("BoxTitle")
        self._final_grid = QGridLayout()
        self._final_grid.setColumnStretch(3, 1)  # pusta kolumna „wypycha” pola w lewo
        self._final_grid.setHorizontalSpacing(24)
        confirm = _button("Zatwierdź stawki i pokaż pytanie ▶")
        confirm.clicked.connect(self._confirm_final_wagers)
        box_layout = QVBoxLayout(self._final_box)
        box_layout.addWidget(title)
        box_layout.addLayout(self._final_grid)
        box_layout.addWidget(confirm, alignment=Qt.AlignmentFlag.AlignRight)
        return self._final_box

    def _build_timer_row(self) -> QWidget:
        self._timer_row = QWidget()
        self._timer_label = QLabel()
        self._timer_label.setObjectName("TimerLabel")
        self._timer_pause = _button("⏸ Pauza", "Klawisz P")
        self._timer_pause.clicked.connect(self._timer.toggle_pause)
        restart = _button("↻ Od nowa")
        restart.clicked.connect(self._timer.restart)
        stop = _button("Wyłącz timer")
        stop.clicked.connect(self._timer.stop)
        row = QHBoxLayout(self._timer_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._timer_label)
        row.addWidget(self._timer_pause)
        row.addWidget(restart)
        row.addWidget(stop)
        row.addStretch()
        return self._timer_row

    def _build_actions(self) -> QGridLayout:
        controller = self._controller
        self._reveal_button = _button("Odsłoń odpowiedź", "Spacja")
        self._close_button = _button("Wróć do planszy")
        self._next_button = _button("Dalej", "Spacja")
        self._end_round_button = _button("Zakończ rundę")
        self._finish_final_button = _button("Zakończ finał – ekran zwycięzcy")
        self._scores_button = _button("Pokaż wyniki na ekranie")
        self._undo_button = _button("↶ Cofnij", "Ctrl+Z")
        self._menu_button = _button("Menu", "Esc")
        self._reveal_button.clicked.connect(controller.reveal_answer)
        self._close_button.clicked.connect(controller.close_question)
        self._next_button.clicked.connect(controller.advance)
        self._end_round_button.clicked.connect(self._confirm_end_round)
        self._finish_final_button.clicked.connect(self._confirm_finish_final)
        self._scores_button.clicked.connect(controller.toggle_scores)
        self._undo_button.clicked.connect(controller.undo)
        self._menu_button.clicked.connect(self.menu_requested)

        # Domyślnie wyłączone – żeby przypadkiem nie zdradzić bonusów graczom.
        self._show_bonuses = QCheckBox("Pokaż mi położenie bonusów")
        self._show_bonuses.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._show_bonuses.setToolTip("Widoczne tylko w tym panelu. W trybie jednoekranowym "
                                      "pamiętaj, że panel może być widoczny dla graczy.")
        self._show_bonuses.toggled.connect(self.refresh)
        self._bonus_info = QLabel()
        self._bonus_info.setObjectName("BonusInfo")

        actions = QGridLayout()
        actions.addWidget(self._reveal_button, 0, 0)
        actions.addWidget(self._close_button, 0, 1)
        actions.addWidget(self._next_button, 0, 2)
        actions.addWidget(self._end_round_button, 0, 3)
        actions.addWidget(self._finish_final_button, 0, 2)
        actions.addWidget(self._scores_button, 1, 0)
        actions.addWidget(self._undo_button, 1, 1)
        actions.addWidget(self._menu_button, 1, 3)
        actions.addWidget(self._show_bonuses, 2, 0)
        actions.addWidget(self._bonus_info, 2, 1, 1, 3)  # zajmuje 3 kolumny
        return actions

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
        phase = state.phase

        for index, (row, player) in enumerate(zip(self._rows, state.players)):
            row.update_row(player.name, player.score,
                           can_mark=state.mark_value(index) is not None,
                           mark=state.current_mark(index),
                           value=self._shown_value(state, index),
                           last_correct=index == state.last_correct)

        if state.last_correct is None:
            self._turn.setText("★ Wybiera: dowolny zawodnik")
        else:
            self._turn.setText(f"★ Ostatnio dobrze: {state.players[state.last_correct].name}")

        self._info.setText(self._info_text(state))
        shows_question = phase in (Phase.QUESTION, Phase.FINAL_WAGERS, Phase.FINAL_QUESTION)
        self._answer_box.setVisible(shows_question)
        if shows_question:
            question = state.current_question()
            self._question_text.setText(f"Pytanie: {question.text}" if question.text
                                        else "Pytanie: (bez tekstu)")
            self._update_answer_text()

        self._bonus_box.setVisible(phase == Phase.BONUS)
        if phase == Phase.BONUS:
            self._refresh_bonus_box(state)
        self._final_box.setVisible(phase == Phase.FINAL_WAGERS)
        if phase == Phase.FINAL_WAGERS:
            self._refresh_final_box(state)
        else:
            self._final_spins = {}  # przy następnym finale zbudujemy pola od nowa

        revealed = state.is_revealed()
        self._reveal_button.setVisible(phase in (Phase.QUESTION, Phase.FINAL_QUESTION)
                                       and not revealed)
        self._close_button.setVisible(phase == Phase.QUESTION)
        self._close_button.setText("Wróć do planszy" if state.current and state.current.marks
                                   else "Nikt – wróć do planszy")
        self._next_button.setVisible(phase == Phase.ROUND_END)
        self._end_round_button.setVisible(phase == Phase.BOARD)
        self._finish_final_button.setVisible(phase == Phase.FINAL_QUESTION and revealed)
        self._scores_button.setVisible(phase not in (Phase.ROUND_END, Phase.FINISHED))
        self._scores_button.setText("Pokaż grę na ekranie" if self._controller.show_scores
                                    else "Pokaż wyniki na ekranie")
        self._undo_button.setEnabled(self._controller.can_undo())
        last = self._controller.last_action()
        self._undo_button.setToolTip(f"Ctrl+Z – cofnij: {last}" if last else "Ctrl+Z")

        self._show_bonuses.setVisible(phase in (Phase.BOARD, Phase.BONUS, Phase.QUESTION))
        self._bonus_info.setVisible(self._show_bonuses.isVisible()
                                    and self._show_bonuses.isChecked())
        self._bonus_info.setText(self._bonus_locations(state))
        self._update_timer()

    @staticmethod
    def _shown_value(state: GameState, index: int) -> int:
        """Ile punktów pokazać na przyciskach oceny danego zawodnika."""
        if state.phase == Phase.FINAL_QUESTION:
            return state.final.wagers.get(index, 0)
        return state.current.value if state.current else 0

    @staticmethod
    def _info_text(state: GameState) -> str:
        match state.phase:
            case Phase.BOARD:
                return (f"<b>Runda {state.round.number}</b> · pozostało pól: "
                        f"{state.round.remaining()}")
            case Phase.BONUS:
                return (f"<b>BONUS</b> · {state.current_category().name} · "
                        f"pole za {format_points(state.round.value(state.current.row))}")
            case Phase.QUESTION:
                current = state.current
                question = state.current_question()
                kind = {ContentKind.IMAGE: " (obraz)", ContentKind.SOUND: " (dźwięk)"}.get(
                    question.kind, "")
                status = "odsłonięta" if current.revealed else "ukryta przed graczami"
                if current.is_bonus:
                    player = state.players[current.bonus_player].name
                    worth = f"BONUS: {player} gra o {format_points(current.value)}"
                else:
                    worth = f"{format_points(current.value)} pkt"
                return (f"<b>{state.current_category().name}</b> · {worth}{kind} · "
                        f"odpowiedź {status}")
            case Phase.ROUND_END:
                return f"<b>Koniec rundy {state.round.number}</b>"
            case Phase.FINAL_WAGERS:
                return f"<b>FINAŁ</b> · kategoria: {state.final.question.category}"
            case Phase.FINAL_QUESTION:
                status = "odsłonięta" if state.final.revealed else "ukryta przed graczami"
                return f"<b>FINAŁ</b> · {state.final.question.category} · odpowiedź {status}"
            case Phase.FINISHED:
                if state.final_skipped:
                    return "<b>Koniec gry</b> · finał pominięty (nikt nie miał punktów > 0)"
                return "<b>Koniec gry</b>"
        return ""

    @staticmethod
    def _bonus_locations(state: GameState) -> str:
        parts = []
        for column, row in state.round.bonuses:
            name = state.round.categories[column].name
            text = f"{name} – {format_points(state.round.value(row))}"
            if state.round.is_used(column, row):
                text += " (wykorzystany)"
            parts.append(text)
        return "Bonusy w tej rundzie: " + (" · ".join(parts) if parts else "brak")

    def _refresh_bonus_box(self, state: GameState) -> None:
        names = [player.name for player in state.players]
        if [self._bonus_player.itemText(i) for i in range(self._bonus_player.count())] != names:
            self._bonus_player.blockSignals(True)
            self._bonus_player.clear()
            self._bonus_player.addItems(names)
            self._bonus_player.blockSignals(False)
        current = state.current
        key = (state.round_index, current.column, current.row)
        if current.bonus_player is not None:
            self._bonus_player.setCurrentIndex(current.bonus_player)
        elif key != self._bonus_key and state.last_correct is not None:
            # Nowy bonus – podpowiedź: zwykle trafia go ten, kto wybierał pole.
            self._bonus_player.setCurrentIndex(state.last_correct)
        if key != self._bonus_key:
            self._bonus_wager.setValue(0)
        self._bonus_key = key
        self._update_bonus_limit()
        if current.bonus_player is not None:
            self._bonus_wager.setValue(current.value)
        self._bonus_show_button.setEnabled(current.bonus_player is not None)

    def _update_bonus_limit(self) -> None:
        state = self._controller.state
        index = self._bonus_player.currentIndex()
        if state is None or state.phase != Phase.BONUS or index < 0:
            return
        limit = state.max_bonus_wager(index)
        self._bonus_wager.setRange(0, limit)
        self._bonus_limit.setText(f"(maks. {format_points(limit)})")

    def _refresh_final_box(self, state: GameState) -> None:
        participants = state.final.participants
        if list(self._final_spins) == participants:
            return  # już zbudowane – nie kasujemy wpisanych stawek
        while self._final_grid.count():
            self._final_grid.takeAt(0).widget().deleteLater()
        self._final_spins = {}
        for line, index in enumerate(participants):
            player = state.players[index]
            spin = QSpinBox()
            spin.setRange(0, player.score)
            spin.setSingleStep(100)
            spin.setMinimumWidth(140)
            self._final_grid.addWidget(QLabel(f"<b>{player.name}</b>"), line, 0)
            self._final_grid.addWidget(QLabel(f"wynik: {format_points(player.score)}"), line, 1)
            self._final_grid.addWidget(spin, line, 2)
            self._final_spins[index] = spin

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

    def _update_timer(self) -> None:
        self._timer_row.setVisible(self._timer.active)
        if not self._timer.active:
            return
        remaining = self._timer.remaining()
        text = format_seconds(remaining) if remaining > 0 else "koniec czasu!"
        self._timer_label.setText(f"⏱ {text}")
        self._timer_pause.setText("⏸ Pauza (P)" if self._timer.running else "▶ Wznów (P)")
        self._timer_pause.setEnabled(remaining > 0)

    # --- Akcje z potwierdzeniem i okna dialogowe ----------------------------

    def _confirm_bonus_wager(self) -> None:
        index = self._bonus_player.currentIndex()
        if index >= 0:
            self._controller.set_bonus_wager(index, self._bonus_wager.value())

    def _confirm_final_wagers(self) -> None:
        wagers = {index: spin.value() for index, spin in self._final_spins.items()}
        self._controller.start_final_question(wagers)

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

    def _confirm_finish_final(self) -> None:
        state = self._controller.state
        missing = [state.players[i].name for i in state.final.participants
                   if i not in state.final.marks]
        if missing:
            answer = QMessageBox.question(
                self,
                "Zakończyć finał?",
                "Nie oceniono jeszcze: " + ", ".join(missing) + ".\n"
                "Ich wyniki się nie zmienią. Zakończyć finał?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._controller.finish_final()

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
