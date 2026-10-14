"""Stan rozgrywki: zawodnicy, plansze obu rund, bonusy, finał i punktacja.

Każda zmiana stanu odbywa się przez metodę GameState (open_tile, mark, …).
Metody najpierw sprawdzają, czy akcja jest dozwolona, a dopiero potem
cokolwiek zmieniają. Niedozwolona akcja zgłasza GameError z polskim opisem.

Przebieg gry (fazy):

    BOARD ──► QUESTION ──► BOARD …             zwykłe pole
    BOARD ──► BONUS ──► QUESTION ──► BOARD …   pole bonusowe (najpierw stawka)
    … ──► ROUND_END ──► BOARD (runda 2) … ──► ROUND_END
      ──► FINAL_WAGERS ──► FINAL_QUESTION ──► FINISHED   (gdy finał włączony)
      ──► FINISHED                                       (bez finału)
"""

import copy
import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fa_milia.config import CATEGORIES_PER_ROUND, MAX_PLAYERS, MIN_PLAYERS, ROUND_VALUES, ROW_COUNT
from fa_milia.core.bonus import draw_bonus_tiles
from fa_milia.core.models import Category, FinalQuestion, Question


class GameError(Exception):
    """Akcja niedozwolona w bieżącym stanie gry (komunikat po polsku)."""


class Phase(StrEnum):
    BOARD = "board"  # plansza, prowadzący wybiera pole
    BONUS = "bonus"  # ekran BONUS, prowadzący wybiera zawodnika i stawkę
    QUESTION = "question"  # wyświetlone pytanie (odpowiedź ukryta lub odsłonięta)
    ROUND_END = "round_end"  # koniec rundy, tabela wyników
    FINAL_WAGERS = "final_wagers"  # finał: kategoria na ekranie, prowadzący wpisuje stawki
    FINAL_QUESTION = "final_question"  # finał: pytanie, odpowiedź, ocena
    FINISHED = "finished"  # koniec gry, ekran zwycięzcy


def _pairs_to_dict(pairs: list) -> dict[int, Any]:
    """[[0, True], [2, False]] → {0: True, 2: False}.

    W JSON klucze słowników muszą być napisami, więc słowniki z kluczami
    liczbowymi zapisujemy jako listy par i tak je odczytujemy.
    """
    return {key: value for key, value in pairs}


def _dict_to_pairs(data: dict[int, Any]) -> list:
    return [[key, value] for key, value in data.items()]


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
    # Położenie pól z premią (bonusów): lista (kolumna, rząd).
    bonuses: list[tuple[int, int]] = field(default_factory=list)
    # Ile kategorii (od lewej) prowadzący już odsłonił na początku rundy.
    revealed_categories: int = 0

    def __post_init__(self) -> None:
        # __post_init__ wywołuje się automatycznie zaraz po __init__ z dataclass.
        if not self.used:
            self.used = [[False] * ROW_COUNT for _ in self.categories]
        self.bonuses = [tuple(tile) for tile in self.bonuses]

    def value(self, row: int) -> int:
        """Wartość pola w danym rzędzie (rzędy numerujemy od 1)."""
        return ROUND_VALUES[self.number][row - 1]

    def max_value(self) -> int:
        """Najwyższa wartość pola w tej rundzie (500 albo 1000)."""
        return ROUND_VALUES[self.number][-1]

    def is_used(self, column: int, row: int) -> bool:
        return self.used[column][row - 1]

    def is_bonus(self, column: int, row: int) -> bool:
        return (column, row) in self.bonuses

    def remaining(self) -> int:
        return sum(not used for column in self.used for used in column)

    def all_categories_revealed(self) -> bool:
        return self.revealed_categories >= len(self.categories)

    def next_hidden_category(self) -> Category | None:
        """Kategoria, którą prowadzący odsłoni jako następną (od lewej do prawej)."""
        if self.all_categories_revealed():
            return None
        return self.categories[self.revealed_categories]

    def is_finished(self) -> bool:
        return self.remaining() == 0

    def to_dict(self, content: bool = True) -> dict[str, Any]:
        data = {
            "number": self.number,
            # Kopiujemy listy! Gdybyśmy zwrócili self.used, migawka w historii
            # wskazywałaby na tę samą listę i zmieniałaby się razem ze stanem gry.
            "used": [list(column) for column in self.used],
            "bonuses": [list(tile) for tile in self.bonuses],
            "revealed_categories": self.revealed_categories,
        }
        if content:
            data["categories"] = [c.to_dict() for c in self.categories]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any],
                  categories: list[Category] | None = None) -> "RoundState":
        if categories is None:
            categories = [Category.from_dict(c) for c in data["categories"]]
        return cls(
            number=data["number"],
            categories=categories,
            used=[list(column) for column in data["used"]],
            bonuses=[tuple(tile) for tile in data.get("bonuses", [])],
            # Starsze zapisy nie mają tego pola – wtedy wszystkie kategorie są odsłonięte.
            revealed_categories=data.get("revealed_categories", len(categories)),
        )


@dataclass
class OpenQuestion:
    """Pytanie, które jest właśnie wyświetlane."""

    column: int
    row: int
    value: int  # przy bonusie: stawka (0, dopóki prowadzący jej nie wpisze)
    revealed: bool = False
    # Kto został już oceniony: indeks zawodnika → True (dobrze) / False (źle).
    marks: dict[int, bool] = field(default_factory=dict)
    is_bonus: bool = False
    bonus_player: int | None = None  # przy bonusie: kto odpowiada

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "row": self.row,
            "value": self.value,
            "revealed": self.revealed,
            "marks": _dict_to_pairs(self.marks),
            "is_bonus": self.is_bonus,
            "bonus_player": self.bonus_player,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenQuestion":
        return cls(
            column=data["column"],
            row=data["row"],
            value=data["value"],
            revealed=data["revealed"],
            marks=_pairs_to_dict(data["marks"]),
            is_bonus=data.get("is_bonus", False),
            bonus_player=data.get("bonus_player"),
        )


@dataclass
class FinalState:
    """Przebieg finału."""

    question: FinalQuestion
    participants: list[int] = field(default_factory=list)  # indeksy zawodników
    wagers: dict[int, int] = field(default_factory=dict)
    marks: dict[int, bool] = field(default_factory=dict)
    revealed: bool = False

    def to_dict(self, content: bool = True) -> dict[str, Any]:
        data = {
            "participants": list(self.participants),
            "wagers": _dict_to_pairs(self.wagers),
            "marks": _dict_to_pairs(self.marks),
            "revealed": self.revealed,
        }
        if content:
            data["question"] = self.question.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any],
                  question: FinalQuestion | None = None) -> "FinalState":
        return cls(
            question=question or FinalQuestion.from_dict(data["question"]),
            participants=list(data["participants"]),
            wagers=_pairs_to_dict(data["wagers"]),
            marks=_pairs_to_dict(data["marks"]),
            revealed=data["revealed"],
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
    final: FinalState | None = None  # None = gra bez finału
    final_skipped: bool = False  # finał pominięty, bo nikt nie miał punktów > 0

    # --- Tworzenie gry -----------------------------------------------------

    @classmethod
    def new(cls, player_names: list[str], round1: list[Category], round2: list[Category],
            final_question: FinalQuestion | None = None,
            rng: random.Random | None = None,
            bonus_tiles: list[list[tuple[int, int]]] | None = None) -> "GameState":
        """Tworzy nową grę.

        bonus_tiles pozwala podać położenie bonusów wprost (używane w testach);
        domyślnie bonusy są losowane.
        """
        names = validate_player_names(player_names)
        for number, categories in ((1, round1), (2, round2)):
            if len(categories) != CATEGORIES_PER_ROUND:
                raise GameError(f"Runda {number} musi mieć {CATEGORIES_PER_ROUND} kategorii.")
            for category in categories:
                if not category.is_complete():
                    raise GameError(f"Kategoria „{category.name}” jest niekompletna.")
        if {c.id for c in round1} & {c.id for c in round2}:  # & = część wspólna zbiorów
            raise GameError("Ta sama kategoria nie może wystąpić w obu rundach.")
        if final_question is not None and not final_question.is_complete():
            raise GameError("Pytanie finałowe jest niekompletne.")

        if bonus_tiles is None:
            rng = rng or random.Random()
            bonus_tiles = [draw_bonus_tiles(CATEGORIES_PER_ROUND, rng) for _ in range(2)]

        # deepcopy tworzy niezależne kopie – późniejsza edycja w edytorze
        # nie zmieni pytań w trwającej grze.
        return cls(
            players=[Player(name) for name in names],
            rounds=[
                RoundState(1, copy.deepcopy(round1), bonuses=bonus_tiles[0]),
                RoundState(2, copy.deepcopy(round2), bonuses=bonus_tiles[1]),
            ],
            final=FinalState(copy.deepcopy(final_question)) if final_question else None,
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
        """Wyświetlane pytanie: z planszy albo – w finale – finałowe."""
        if self.phase in (Phase.FINAL_WAGERS, Phase.FINAL_QUESTION):
            return self.final.question.question
        if self.current is None:
            return None
        return self.current_category().questions[self.current.row - 1]

    def is_revealed(self) -> bool:
        """Czy odpowiedź na bieżące pytanie (zwykłe lub finałowe) jest odsłonięta."""
        if self.phase == Phase.FINAL_QUESTION:
            return self.final.revealed
        return self.current is not None and self.current.revealed

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

    def max_bonus_wager(self, player_index: int) -> int:
        """Najwyższa stawka bonusu: większa z (wynik zawodnika, najwyższe pole rundy)."""
        return max(self.players[player_index].score, self.round.max_value())

    def mark_value(self, player_index: int) -> int | None:
        """Za ile punktów można teraz ocenić zawodnika (None = nie można go oceniać)."""
        if self.phase == Phase.QUESTION:
            if player_index in self.current.marks:
                return None
            if self.current.is_bonus and player_index != self.current.bonus_player:
                return None
            return self.current.value
        if self.phase == Phase.FINAL_QUESTION:
            if player_index not in self.final.participants or player_index in self.final.marks:
                return None
            return self.final.wagers[player_index]
        return None

    def current_mark(self, player_index: int) -> bool | None:
        """Ocena zawodnika w bieżącym pytaniu: True/False albo None (brak)."""
        if self.phase == Phase.FINAL_QUESTION:
            return self.final.marks.get(player_index)
        if self.current is not None:
            return self.current.marks.get(player_index)
        return None

    # --- Akcje: plansza i pytania -----------------------------------------

    def reveal_next_category(self) -> Category:
        """Początek rundy: odsłania nazwę kolejnej kategorii (od lewej). Zwraca ją."""
        self._require_phase(Phase.BOARD)
        category = self.round.next_hidden_category()
        if category is None:
            raise GameError("Wszystkie kategorie są już odsłonięte.")
        self.round.revealed_categories += 1
        return category

    def open_tile(self, column: int, row: int) -> None:
        self._require_phase(Phase.BOARD)
        if not self.round.all_categories_revealed():
            raise GameError("Najpierw odsłoń wszystkie kategorie (spacja).")
        if not (0 <= column < len(self.round.categories) and 1 <= row <= ROW_COUNT):
            raise GameError("Nie ma takiego pola.")
        if self.round.is_used(column, row):
            raise GameError("To pole zostało już wykorzystane.")
        if self.round.is_bonus(column, row):
            self.current = OpenQuestion(column, row, value=0, is_bonus=True)
            self.phase = Phase.BONUS
        else:
            self.current = OpenQuestion(column, row, self.round.value(row))
            self.phase = Phase.QUESTION

    def set_bonus_wager(self, player_index: int, wager: int) -> None:
        """Premia: prowadzący wskazuje zawodnika i jego stawkę."""
        self._require_phase(Phase.BONUS)
        self._check_player(player_index)
        limit = self.max_bonus_wager(player_index)
        if not 0 <= wager <= limit:
            raise GameError(f"Stawka musi wynosić od 0 do {limit}.")
        self.current.bonus_player = player_index
        self.current.value = wager

    def show_bonus_question(self) -> None:
        """Premia: po ustaleniu stawki przechodzimy do pytania."""
        self._require_phase(Phase.BONUS)
        if self.current.bonus_player is None:
            raise GameError("Najpierw wybierz zawodnika i stawkę.")
        self.phase = Phase.QUESTION

    def reveal_answer(self) -> None:
        self._require_phase(Phase.QUESTION, Phase.FINAL_QUESTION)
        if self.phase == Phase.FINAL_QUESTION:
            self.final.revealed = True
        else:
            self.current.revealed = True

    def mark(self, player_index: int, correct: bool) -> int:
        """Ocenia odpowiedź zawodnika (zwykłe pytanie, bonus lub finał).

        Zwraca zmianę punktów (+/−).
        """
        self._require_phase(Phase.QUESTION, Phase.FINAL_QUESTION)
        self._check_player(player_index)
        value = self.mark_value(player_index)
        if value is None:
            name = self.players[player_index].name
            if self.current_mark(player_index) is not None:
                raise GameError(f"{name} ma już ocenioną odpowiedź.")
            raise GameError(f"{name} nie odpowiada na to pytanie.")
        change = value if correct else -value
        self.players[player_index].score += change
        if self.phase == Phase.FINAL_QUESTION:
            self.final.marks[player_index] = correct
        else:
            self.current.marks[player_index] = correct
            if correct:
                # Dobra odpowiedź w zwykłym pytaniu (i premii) od razu pokazuje odpowiedź.
                self.current.revealed = True
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
        """Wycofuje się z pola otwartego przez pomyłkę – pole zostaje na planszy."""
        self._require_phase(Phase.QUESTION, Phase.BONUS)
        if self.current.revealed or self.current.marks:
            raise GameError("Odpowiedź została już odsłonięta lub oceniona.")
        self.current = None
        self.phase = Phase.BOARD

    def end_round(self) -> None:
        """Kończy rundę przed wykorzystaniem wszystkich pól."""
        self._require_phase(Phase.BOARD)
        self.phase = Phase.ROUND_END

    def next_round(self) -> None:
        """Po zakończeniu rundy: runda 2, finał albo koniec gry."""
        self._require_phase(Phase.ROUND_END)
        if not self.is_last_round():
            self.round_index += 1
            self.phase = Phase.BOARD
            return
        if self.final is None:
            self.phase = Phase.FINISHED
            return
        # W finale grają tylko zawodnicy z dodatnim wynikiem.
        participants = [i for i, player in enumerate(self.players) if player.score > 0]
        if participants:
            self.final.participants = participants
            self.phase = Phase.FINAL_WAGERS
        else:
            self.final_skipped = True
            self.phase = Phase.FINISHED

    # --- Akcje: finał ------------------------------------------------------

    def start_final_question(self, wagers: dict[int, int]) -> None:
        """Finał: zapisuje stawki wszystkich uczestników i pokazuje pytanie."""
        self._require_phase(Phase.FINAL_WAGERS)
        if set(wagers) != set(self.final.participants):
            raise GameError("Podaj stawki wszystkich uczestników finału.")
        for index, wager in wagers.items():
            score = self.players[index].score
            if not 0 <= wager <= score:
                raise GameError(f"Stawka zawodnika {self.players[index].name} "
                                f"musi wynosić od 0 do {score}.")
        self.final.wagers = dict(wagers)
        self.phase = Phase.FINAL_QUESTION

    def finish_final(self) -> None:
        """Finał: po odsłonięciu odpowiedzi kończy grę (ekran zwycięzcy)."""
        self._require_phase(Phase.FINAL_QUESTION)
        if not self.final.revealed:
            raise GameError("Najpierw odsłoń odpowiedź.")
        self.phase = Phase.FINISHED

    # --- Inne --------------------------------------------------------------

    def adjust_score(self, player_index: int, change: int) -> None:
        """Ręczna korekta punktów przez prowadzącego."""
        self._check_player(player_index)
        self.players[player_index].score += change

    def _check_player(self, player_index: int) -> None:
        if not 0 <= player_index < len(self.players):
            raise GameError("Nie ma takiego zawodnika.")

    def _require_phase(self, *allowed: Phase) -> None:
        # *allowed zbiera dowolną liczbę argumentów w krotkę.
        if self.phase not in allowed:
            raise GameError("Ta akcja nie jest teraz możliwa.")

    # --- Zapis do słownika (cofanie, zapis gry) ---------------------------

    def to_dict(self, content: bool = True) -> dict[str, Any]:
        """Stan gry jako słownik (do JSON).

        content=False pomija treść pytań (kategorie i pytanie finałowe), która
        nie zmienia się w trakcie gry. Tak zapisujemy migawki w historii cofania –
        dzięki temu są małe, a plik zapisu gry nie rośnie do wielu megabajtów.
        """
        return {
            "players": [{"name": p.name, "score": p.score} for p in self.players],
            "rounds": [r.to_dict(content) for r in self.rounds],
            "round_index": self.round_index,
            "phase": self.phase.value,
            "current": self.current.to_dict() if self.current else None,
            "last_correct": self.last_correct,
            "final": self.final.to_dict(content) if self.final else None,
            "final_skipped": self.final_skipped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any],
                  content_from: "GameState | None" = None) -> "GameState":
        """Odtwarza stan ze słownika.

        content_from: stan, z którego bierzemy treść pytań, gdy słownik
        jej nie zawiera (migawka zapisana z content=False).
        """
        final = data.get("final")  # .get – starsze zapisy mogą nie mieć tych pól
        if content_from is not None:
            rounds = [RoundState.from_dict(r, source.categories)
                      for r, source in zip(data["rounds"], content_from.rounds)]
            final_question = content_from.final.question if content_from.final else None
        else:
            rounds = [RoundState.from_dict(r) for r in data["rounds"]]
            final_question = None
        return cls(
            players=[Player(p["name"], p["score"]) for p in data["players"]],
            rounds=rounds,
            round_index=data["round_index"],
            phase=Phase(data["phase"]),
            current=OpenQuestion.from_dict(data["current"]) if data["current"] else None,
            last_correct=data.get("last_correct"),
            final=FinalState.from_dict(final, final_question) if final else None,
            final_skipped=data.get("final_skipped", False),
        )
