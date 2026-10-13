"""Losowanie położenia pól bonusowych."""

import random

from fa_milia.config import (
    BONUS_ROW_WEIGHTS,
    BONUS_SAME_CATEGORY_FACTOR,
    BONUSES_PER_ROUND,
    ROW_COUNT,
)


def draw_bonus_tiles(
    columns: int,
    rng: random.Random | None = None,
    count: int = BONUSES_PER_ROUND,
    row_weights: dict[int, float] = BONUS_ROW_WEIGHTS,
    same_category_factor: float = BONUS_SAME_CATEGORY_FACTOR,
) -> list[tuple[int, int]]:
    """Losuje `count` różnych pól bonusowych. Zwraca listę (kolumna, rząd).

    Każde pole ma wagę zależną od rzędu (rząd 1 ma wagę 0, więc nigdy nie
    zostanie wylosowany). Jeśli w danej kolumnie jest już bonus, waga
    kolejnych pól z tej kolumny jest mnożona przez same_category_factor.
    """
    rng = rng or random.Random()
    chosen: list[tuple[int, int]] = []
    for _ in range(count):
        used_columns = {column for column, _row in chosen}
        candidates = []
        weights = []
        for column in range(columns):
            for row in range(1, ROW_COUNT + 1):
                weight = row_weights.get(row, 0.0)
                if weight <= 0 or (column, row) in chosen:
                    continue
                if column in used_columns:
                    weight *= same_category_factor
                candidates.append((column, row))
                weights.append(weight)
        if not candidates:
            break
        # random.choices losuje z uwzględnieniem wag; [0] – bierzemy jeden wynik.
        chosen.append(rng.choices(candidates, weights=weights)[0])
    return chosen
