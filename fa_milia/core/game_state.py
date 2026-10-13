"""Stan rozgrywki: zawodnicy, plansze obu rund, otwarte pytanie i punktacja.

Każda zmiana stanu odbywa się przez metodę GameState (open_tile, mark, …).
Metody najpierw sprawdzają, czy akcja jest dozwolona, a dopiero potem
cokolwiek zmieniają. Niedozwolona akcja zgłasza GameError z polskim opisem.
"""

import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fa_milia.config import CATEGORIES_PER_ROUND, MAX_PLAYERS, MIN_PLAYERS, ROUND_VALUES, ROW_COUNT
from fa_milia.core.models import Category, Question


class GameError(Exception):
    """Akcja niedozwolona w bieżącym stanie gry (komunikat po polsku)."""


class Phase(StrEnum):
    BOARD = "board"  # plansza, prowadzący wybiera pole
    QUESTION = "question"  # wyświetlone pytanie (odpowiedź ukryta lub odsłonięta)
    ROUND_END = "round_end"  # koniec rundy, tabela wyników
    FINISHED = "finished"  # koniec gry, ekran zwycięzcy


@dataclass
class Player:
    name: str
    score: int = 0


@dataclass
class RoundState:
    """Plansza jednej rundy."""

    number: int  # 1 albo 2
    categories: list[Category]
    # used[kolumna][rząd - 1] == True, gdy pole zostało już wykorzystane.
    used: list[list[bool]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # __post_init__ wywołuje się automatycznie zaraz po __init__ z dataclass.
        if not self.used:
            self.used = [[False] * ROW_COUNT for _ in self.categories]

    def value(self, row: int) -> int:
        """Wartość pola w danym rzędzie (rzędy numerujemy od 1)."""
        return ROUND_VALUES[self.number][row - 1]

    def is_used(self, column: int, row: int) -> bool:
        return self.used[column][row - 1]

    def remaining(self) -> int:
        return sum(not used for column in self.used for used in column)

    def is_finished(self) -> bool:
        return self.remaining() == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "categories": [c.to_dict() for c in self.categories],
            # Kopiujemy listy! Gdybyśmy zwrócili self.used, migawka w historii
            # wskazywałaby na tę samą listę i zmieniałaby się razem ze stanem gry.
            "used": [list(column) for column in self.used],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoundState":
        return cls(
            number=data["number"],
            categories=[Category.from_dict(c) for c in data["categories"]],
            used=[list(column) for column in data["used"]],
        )


@dataclass
class OpenQuestion:
    """Pytanie, które jest właśnie wyświetlane."""

    column: int
    row: int
    value: int
    revealed: bool = False
    # Kto został już oceniony: indeks zawodnika → True (dobrze) / False (źle).
    marks: dict[int, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "row": self.row,
            "value": self.value,
            "revealed": self.revealed,
            # Klucze słowników w JSON muszą być napisami, więc zapisujemy listę par.
            "marks": [[index, correct] for index, correct in self.marks.items()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenQuestion":
        return cls(
            column=data["column"],
            row=data["row"],
            value=data["value"],
            revealed=data["revealed"],
            marks={index: correct for index, correct in data["marks"]},
        )


def validate_player_names(names: list[str]) -> list[str]:
    """Sprawdza imiona zawodników i zwraca je oczyszczone ze spacji."""
    cleaned = [name.strip() for name in names]
    if not MIN_PLAYERS <= len(cleaned) <= MAX_PLAYERS:
        raise GameError(f"Liczba zawodników musi wynosić od {MIN_PLAYERS} do {MAX_PLAYERS}.")
    if any(not name for name in cleaned):
        raise GameError("Każdy zawodnik musi mieć imię.")
    if len({name.casefold() for name in cleaned}) != len(cleaned):
        raise GameError("Imiona zawodników muszą być różne.")
    return cleaned


@dataclass
class GameState:
    players: list[Player]
    rounds: list[RoundState]
    round_index: int = 0  # 0 = runda 1, 1 = runda 2
    phase: Phase = Phase.BOARD
    current: OpenQuestion | None = None
    # Indeks zawodnika, który ostatnio odpowiedział dobrze (zwykle on wybiera
    # następne pole). None = nikt jeszcze nie odpowiedział dobrze.
    last_correct: int | None = None

    # --- Tworzenie gry -----------------------------------------------------

    @classmethod
    def new(cls, player_names: list[str], round1: list[Category],
            round2: list[Category]) -> "GameState":
        names = validate_player_names(player_names)
        for number, categories in ((1, round1), (2, round2)):
            if len(categories) != CATEGORIES_PER_ROUND:
                raise GameError(f"Runda {number} musi mieć {CATEGORIES_PER_ROUND} kategorii.")
            for category in categories:
                if not category.is_complete():
                    raise GameError(f"Kategoria „{category.name}” jest niekompletna.")
        if {c.id for c in round1} & {c.id for c in round2}:  # & = część wspólna zbiorów
            raise GameError("Ta sama kategoria nie może wystąpić w obu rundach.")
        # deepcopy tworzy niezależne kopie kategorii – późniejsza edycja
        # w edytorze nie zmieni pytań w trwającej grze.
        return cls(
            players=[Player(name) for name in names],
            rounds=[
                RoundState(1, copy.deepcopy(round1)),
                RoundState(2, copy.deepcopy(round2)),
            ],
        )

    # --- Odczyt ------------------------------------------------------------

    @property
    def round(self) -> RoundState:
        """Bieżąca runda."""
        return self.rounds[self.round_index]

    def current_category(self) -> Category | None:
        if self.current is None:
            return None
        return self.round.categories[self.current.column]

    def current_question(self) -> Question | None:
        if self.current is None:
            return None
        return self.current_category().questions[self.current.row - 1]

    def is_last_round(self) -> bool:
        return self.round_index == len(self.rounds) - 1

    def ranking(self) -> list[tuple[int, Player]]:
        """Lista (miejsce, zawodnik) od najlepszego. Remis = to samo miejsce."""
        ordered = sorted(self.players, key=lambda p: p.score, reverse=True)
        # Miejsce = 1 + liczba zawodników z wyższym wynikiem (np. 1, 1, 3).
        return [
            (1 + sum(other.score > player.score for other in self.players), player)
            for player in ordered
        ]

    # --- Akcje -------------------------------------------------------------

    def open_tile(self, column: int, row: int) -> None:
        self._require_phase(Phase.BOARD)
        if not (0 <= column < len(self.round.categories) and 1 <= row <= ROW_COUNT):
            raise GameError("Nie ma takiego pola.")
        if self.round.is_used(column, row):
            raise GameError("To pole zostało już wykorzystane.")
        self.current = OpenQuestion(column, row, self.round.value(row))
        self.phase = Phase.QUESTION

    def reveal_answer(self) -> None:
        self._require_phase(Phase.QUESTION)
        self.current.revealed = True

    def mark(self, player_index: int, correct: bool) -> int:
        """Ocenia odpowiedź zawodnika. Zwraca zmianę punktów (+/−)."""
        self._require_phase(Phase.QUESTION)
        if not 0 <= player_index < len(self.players):
            raise GameError("Nie ma takiego zawodnika.")
        if player_index in self.current.marks:
            raise GameError(f"{self.players[player_index].name} ma już ocenioną odpowiedź.")
        change = self.current.value if correct else -self.current.value
        self.players[player_index].score += change
        self.current.marks[player_index] = correct
        if correct:
            self.last_correct = player_index
        return change

    def close_question(self) -> None:
        """Zamyka pytanie: pole staje się puste, wracamy do planszy."""
        self._require_phase(Phase.QUESTION)
        self.round.used[self.current.column][self.current.row - 1] = True
        self.current = None
        self.phase = Phase.ROUND_END if self.round.is_finished() else Phase.BOARD

    def cancel_question(self) -> None:
        """Wycofuje się z pytania otwartego przez pomyłkę – pole zostaje na planszy."""
        self._require_phase(Phase.QUESTION)
        if self.current.revealed or self.current.marks:
            raise GameError("Odpowiedź została już odsłonięta lub oceniona.")
        self.current = None
        self.phase = Phase.BOARD

    def end_round(self) -> None:
        """Kończy rundę przed wykorzystaniem wszystkich pól."""
        self._require_phase(Phase.BOARD)
        self.phase = Phase.ROUND_END

    def next_round(self) -> None:
        """Po zakończeniu rundy: przejście do rundy 2 albo koniec gry."""
        self._require_phase(Phase.ROUND_END)
        if self.is_last_round():
            self.phase = Phase.FINISHED
        else:
            self.round_index += 1
            self.phase = Phase.BOARD

    def adjust_score(self, player_index: int, change: int) -> None:
        """Ręczna korekta punktów przez prowadzącego."""
        if not 0 <= player_index < len(self.players):
            raise GameError("Nie ma takiego zawodnika.")
        self.players[player_index].score += change

    def _require_phase(self, *allowed: Phase) -> None:
        # *allowed zbiera dowolną liczbę argumentów w krotkę.
        if self.phase not in allowed:
            raise GameError("Ta akcja nie jest teraz możliwa.")

    # --- Zapis do słownika (cofanie, zapis gry) ---------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "players": [{"name": p.name, "score": p.score} for p in self.players],
            "rounds": [r.to_dict() for r in self.rounds],
            "round_index": self.round_index,
            "phase": self.phase.value,
            "current": self.current.to_dict() if self.current else None,
            "last_correct": self.last_correct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        return cls(
            players=[Player(p["name"], p["score"]) for p in data["players"]],
            rounds=[RoundState.from_dict(r) for r in data["rounds"]],
            round_index=data["round_index"],
            phase=Phase(data["phase"]),
            current=OpenQuestion.from_dict(data["current"]) if data["current"] else None,
            # .get – starsze zapisy mogą nie mieć tego pola
            last_correct=data.get("last_correct"),
        )
