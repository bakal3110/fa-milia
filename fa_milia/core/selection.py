"""Wybór kategorii do gry: po 6 na rundę, bez powtórzeń między rundami."""

import random

from fa_milia.config import CATEGORIES_PER_ROUND

ROUND_NUMBERS = (1, 2)


class SelectionError(Exception):
    """Niedozwolony wybór (komunikat po polsku)."""


class CategorySelection:
    """Przechowuje identyfikatory kategorii wybranych do rund 1 i 2.

    Kolejność na liście = kolejność kolumn na planszy.
    """

    def __init__(self) -> None:
        self.rounds: dict[int, list[str]] = {number: [] for number in ROUND_NUMBERS}

    def round_of(self, category_id: str) -> int | None:
        for number, ids in self.rounds.items():
            if category_id in ids:
                return number
        return None

    def count(self, round_number: int) -> int:
        return len(self.rounds[round_number])

    def is_full(self, round_number: int) -> bool:
        return self.count(round_number) >= CATEGORIES_PER_ROUND

    def is_complete(self) -> bool:
        return all(self.is_full(number) for number in ROUND_NUMBERS)

    def set_round(self, category_id: str, round_number: int | None) -> None:
        """Przypisuje kategorię do rundy (None = odznacza).

        Kategoria przypisana do drugiej rundy jest z niej przenoszona,
        bo jedna kategoria nie może wystąpić w obu rundach.
        """
        current = self.round_of(category_id)
        if current == round_number:
            return
        if round_number is not None and self.is_full(round_number):
            raise SelectionError(
                f"Runda {round_number} ma już {CATEGORIES_PER_ROUND} kategorii. "
                "Najpierw odznacz którąś z nich."
            )
        if current is not None:
            self.rounds[current].remove(category_id)
        if round_number is not None:
            self.rounds[round_number].append(category_id)

    def clear(self) -> None:
        for ids in self.rounds.values():
            ids.clear()

    def keep_only(self, valid_ids: set[str]) -> None:
        """Usuwa z wyboru kategorie, których już nie ma (np. usunięte w edytorze)."""
        for number in ROUND_NUMBERS:
            self.rounds[number] = [i for i in self.rounds[number] if i in valid_ids]

    def fill_randomly(self, candidate_ids: list[str], used_ids: set[str],
                      rng: random.Random | None = None) -> int:
        """Uzupełnia brakujące miejsca losowymi kategoriami.

        Najpierw losuje spośród kategorii nieużytych, a dopiero gdy ich
        zabraknie – spośród użytych. Zwraca, ile użytych trzeba było dobrać.
        """
        rng = rng or random.Random()
        free = [i for i in candidate_ids if self.round_of(i) is None]
        fresh = [i for i in free if i not in used_ids]
        old = [i for i in free if i in used_ids]
        rng.shuffle(fresh)
        rng.shuffle(old)
        pool = fresh + old  # najpierw nieużyte

        taken_used = 0
        for number in ROUND_NUMBERS:
            while not self.is_full(number) and pool:
                category_id = pool.pop(0)
                self.rounds[number].append(category_id)
                if category_id in used_ids:
                    taken_used += 1
        return taken_used
