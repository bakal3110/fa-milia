"""Kontroler gry – jedyne miejsce, przez które interfejs zmienia stan gry.

Ekran gry, sterowanie prowadzącego i skróty klawiszowe wywołują metody
kontrolera. Kontroler wykonuje akcję (z zapisem w historii do cofania)
i wysyła sygnał `state_changed`, na który wszystkie widoki się odświeżają.
Dzięki temu oba ekrany (w etapie E3) zawsze pokazują ten sam stan.
"""

from PySide6.QtCore import QObject, Signal

from fa_milia.core.game_state import GameError, GameState, Phase
from fa_milia.core.history import GameHistory
from fa_milia.ui.game.widgets import format_points


class GameController(QObject):
    state_changed = Signal()
    message = Signal(str)  # komunikat dla prowadzącego (błąd, „Cofnięto: …”)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._history: GameHistory | None = None
        # Czy ekran gry pokazuje tabelę wyników zamiast planszy/pytania.
        # To tylko widok – nie jest częścią stanu gry i nie trafia do historii.
        self._show_scores = False

    # --- Dostęp do stanu ---------------------------------------------------

    def start(self, state: GameState) -> None:
        self._history = GameHistory(state)
        self._show_scores = False
        self.state_changed.emit()

    @property
    def show_scores(self) -> bool:
        return self._show_scores

    def toggle_scores(self) -> None:
        self._show_scores = not self._show_scores
        self.state_changed.emit()

    @property
    def state(self) -> GameState | None:
        # Uwaga: po cofnięciu historia podmienia obiekt stanu, dlatego zawsze
        # pobieramy go stąd, zamiast zapamiętywać w innych miejscach.
        return self._history.state if self._history else None

    def can_undo(self) -> bool:
        return self._history is not None and self._history.can_undo()

    def last_action(self) -> str | None:
        return self._history.last_label() if self._history else None

    # --- Akcje -------------------------------------------------------------

    def open_tile(self, column: int, row: int) -> None:
        state = self.state
        name = state.round.categories[column].name
        value = format_points(state.round.value(row))
        self._apply(f"Otwarcie pola: {name} za {value}", lambda s: s.open_tile(column, row))

    def reveal_answer(self) -> None:
        self._apply("Odsłonięcie odpowiedzi", lambda s: s.reveal_answer())

    def mark(self, player_index: int, correct: bool) -> None:
        state = self.state
        if state.current is None:
            return
        name = state.players[player_index].name
        change = state.current.value if correct else -state.current.value
        self._apply(f"{name} {format_points(change, signed=True)}",
                    lambda s: s.mark(player_index, correct))

    def close_question(self) -> None:
        self._apply("Powrót do planszy", lambda s: s.close_question())

    def cancel_question(self) -> None:
        self._apply("Zamknięcie pytania bez odpowiedzi", lambda s: s.cancel_question())

    def end_round(self) -> None:
        self._apply("Zakończenie rundy", lambda s: s.end_round())

    def next_round(self) -> None:
        self._apply("Następna runda", lambda s: s.next_round())

    def adjust_score(self, player_index: int, change: int) -> None:
        name = self.state.players[player_index].name
        self._apply(f"Korekta: {name} {format_points(change, signed=True)}",
                    lambda s: s.adjust_score(player_index, change))

    def advance(self) -> None:
        """„Dalej” – spacja lub kliknięcie w ekran gry."""
        state = self.state
        if state is None:
            return
        if self._show_scores:  # najpierw zamykamy tabelę wyników
            self.toggle_scores()
            return
        if state.phase == Phase.QUESTION:
            if not state.current.revealed:
                self.reveal_answer()
            else:
                self.close_question()
        elif state.phase == Phase.ROUND_END:
            self.next_round()

    def undo(self) -> None:
        if not self.can_undo():
            self.message.emit("Nie ma nic do cofnięcia.")
            return
        label = self._history.undo()
        self.message.emit(f"Cofnięto: {label}")
        self.state_changed.emit()

    def _apply(self, label: str, action) -> bool:
        if self._history is None:
            return False
        try:
            self._history.apply(label, action)
        except GameError as error:
            self.message.emit(str(error))
            return False
        self.message.emit("")
        self.state_changed.emit()
        return True
