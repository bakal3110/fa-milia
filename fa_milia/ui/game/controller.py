"""Kontroler gry – jedyne miejsce, przez które interfejs zmienia stan gry.

Ekran gry, panel prowadzącego i skróty klawiszowe wywołują metody
kontrolera. Kontroler wykonuje akcję (z zapisem w historii do cofania)
i wysyła sygnał `state_changed`, na który wszystkie widoki się odświeżają.
Dzięki temu oba ekrany zawsze pokazują ten sam stan.
"""

from PySide6.QtCore import QObject, Signal

from fa_milia.core.game_state import GameError, GameState, Phase
from fa_milia.core.history import GameHistory
from fa_milia.ui.game.widgets import format_points


class GameController(QObject):
    state_changed = Signal()
    message = Signal(str)  # komunikat dla prowadzącego (błąd, „Cofnięto: …”)
    sound = Signal(str)  # nazwa dźwięku efektu do odtworzenia (np. "premia")
    answer_marked = Signal(bool)  # prowadzący ocenił odpowiedź w zwykłym pytaniu (dobrze?)

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

    def resume(self, history: GameHistory) -> None:
        """Wznawia zapisaną grę (razem z historią do cofania)."""
        self._history = history
        self._show_scores = False
        self.state_changed.emit()

    @property
    def history(self) -> GameHistory | None:
        return self._history

    @property
    def state(self) -> GameState | None:
        # Uwaga: po cofnięciu historia podmienia obiekt stanu, dlatego zawsze
        # pobieramy go stąd, zamiast zapamiętywać w innych miejscach.
        return self._history.state if self._history else None

    @property
    def show_scores(self) -> bool:
        return self._show_scores

    def toggle_scores(self) -> None:
        self._show_scores = not self._show_scores
        self.state_changed.emit()

    def can_undo(self) -> bool:
        return self._history is not None and self._history.can_undo()

    def last_action(self) -> str | None:
        return self._history.last_label() if self._history else None

    # --- Akcje: plansza i pytania -----------------------------------------

    def reveal_next_category(self) -> None:
        category = self.state.round.next_hidden_category()
        if category is not None:
            self._apply(f"Odsłonięcie kategorii: {category.name}",
                        lambda s: s.reveal_next_category())

    def open_tile(self, column: int, row: int) -> None:
        state = self.state
        name = state.round.categories[column].name
        value = format_points(state.round.value(row))
        if self._apply(f"Otwarcie pola: {name} za {value}", lambda s: s.open_tile(column, row)):
            if self.state.phase == Phase.BONUS:
                self.sound.emit("premia")

    def set_bonus_wager(self, player_index: int, wager: int) -> None:
        name = self.state.players[player_index].name
        self._apply(f"Premia: {name} gra o {format_points(wager)}",
                    lambda s: s.set_bonus_wager(player_index, wager))

    def show_bonus_question(self) -> None:
        self._apply("Pytanie bonusowe", lambda s: s.show_bonus_question())

    def reveal_answer(self, label: str = "Odsłonięcie odpowiedzi") -> None:
        self._apply(label, lambda s: s.reveal_answer())

    def mark(self, player_index: int, correct: bool) -> None:
        state = self.state
        value = state.mark_value(player_index)
        if value is None:
            return
        name = state.players[player_index].name
        change = value if correct else -value
        if self._apply(f"{name} {format_points(change, signed=True)}",
                       lambda s: s.mark(player_index, correct)):
            self.sound.emit("good_answer" if correct else "zla_odpowiedz")
            if self.state.phase == Phase.QUESTION:
                self.answer_marked.emit(correct)

    def close_question(self) -> None:
        self._apply("Powrót do planszy", lambda s: s.close_question())

    def cancel_question(self) -> None:
        self._apply("Zamknięcie pola bez odpowiedzi", lambda s: s.cancel_question())

    def end_round(self) -> None:
        self._apply("Zakończenie rundy", lambda s: s.end_round())

    def next_round(self) -> None:
        if not self._apply("Następny etap gry", lambda s: s.next_round()):
            return
        match self.state.phase:
            case Phase.FINAL_WAGERS:
                self.sound.emit("final")
            case Phase.FINISHED:
                self.sound.emit("zwyciezca")

    def adjust_score(self, player_index: int, change: int) -> None:
        name = self.state.players[player_index].name
        self._apply(f"Korekta: {name} {format_points(change, signed=True)}",
                    lambda s: s.adjust_score(player_index, change))

    # --- Akcje: finał ------------------------------------------------------

    def start_final_question(self, wagers: dict[int, int]) -> None:
        self._apply("Stawki finałowe", lambda s: s.start_final_question(wagers))

    def finish_final(self) -> None:
        if self._apply("Koniec finału", lambda s: s.finish_final()):
            self.sound.emit("zwyciezca")

    # --- „Dalej” i cofanie ---------------------------------------------------

    def advance(self) -> None:
        """„Dalej” – spacja lub kliknięcie w ekran gry."""
        state = self.state
        if state is None:
            return
        if self._show_scores:  # najpierw zamykamy tabelę wyników
            self.toggle_scores()
            return
        match state.phase:
            case Phase.BOARD:
                if not state.round.all_categories_revealed():
                    self.reveal_next_category()
            case Phase.BONUS:
                if state.current.bonus_player is None:
                    self.message.emit("Premia: wybierz w panelu zawodnika i wpisz stawkę.")
                else:
                    self.show_bonus_question()
            case Phase.QUESTION:
                if not state.current.revealed:
                    self.reveal_answer()
                else:
                    self.close_question()
            case Phase.ROUND_END:
                self.next_round()
            case Phase.FINAL_WAGERS:
                self.message.emit("Finał: wpisz w panelu stawki wszystkich uczestników.")
            case Phase.FINAL_QUESTION:
                if not state.final.revealed:
                    self.reveal_answer()
                else:
                    self.finish_final()

    def undo(self) -> None:
        if not self.can_undo():
            self.message.emit("Nie ma nic do cofnięcia.")
            return
        label = self._history.undo()
        self.message.emit(f"Cofnięto: {label}")
        self.state_changed.emit()

    def _apply(self, label: str, action) -> bool:
        """Wykonuje akcję przez historię. Zwraca True, jeśli się udała."""
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
