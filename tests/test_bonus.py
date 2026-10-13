import random
from collections import Counter

import pytest

from fa_milia.config import BONUS_ROW_WEIGHTS
from fa_milia.core.bonus import draw_bonus_tiles

DRAWS = 20000


def test_two_distinct_bonuses_never_in_row_one():
    rng = random.Random(42)
    for _ in range(2000):
        tiles = draw_bonus_tiles(6, rng)
        assert len(tiles) == 2
        assert tiles[0] != tiles[1]
        assert all(row != 1 for _column, row in tiles)
        assert all(0 <= column < 6 and 2 <= row <= 5 for column, row in tiles)


def test_first_bonus_follows_row_weights():
    """Rząd 2 ma wagę 1.0, rzędy 3–5 po 1.5, więc rząd 2 to 1/5.5 ≈ 18% losowań."""
    rng = random.Random(1)
    rows = Counter(draw_bonus_tiles(6, rng, count=1)[0][1] for _ in range(DRAWS))
    total_weight = sum(BONUS_ROW_WEIGHTS.values())
    for row, weight in BONUS_ROW_WEIGHTS.items():
        expected = weight / total_weight
        assert rows[row] / DRAWS == pytest.approx(expected, abs=0.015)


def test_second_bonus_rarely_in_same_category():
    """Waga pól w kolumnie pierwszego bonusu jest mnożona przez 0.3.

    Po pierwszym bonusie (w rzędzie r) zostaje w jego kolumnie 5.5 − w(r)
    wagi (×0.3), a w pozostałych 5 kolumnach 5 × 5.5. Średnio daje to ok. 4,3%.
    """
    rng = random.Random(7)
    same = sum(1 for _ in range(DRAWS)
               if len({column for column, _row in draw_bonus_tiles(6, rng)}) == 1)
    assert 0.03 < same / DRAWS < 0.065


def test_same_category_possible_when_factor_is_one():
    rng = random.Random(3)
    same = sum(1 for _ in range(5000)
               if len({c for c, _ in draw_bonus_tiles(6, rng, same_category_factor=1.0)}) == 1)
    assert same > 5000 * 0.10  # bez kary ok. 13%


def test_draw_stops_when_no_candidates():
    weights = {1: 0.0, 2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0}
    assert len(draw_bonus_tiles(1, random.Random(), count=3, row_weights=weights)) == 1
