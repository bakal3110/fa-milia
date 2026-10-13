import random

import pytest

from fa_milia.core.selection import CategorySelection, SelectionError

IDS = [f"k{i}" for i in range(20)]


def test_seventh_category_is_blocked():
    selection = CategorySelection()
    for category_id in IDS[:6]:
        selection.set_round(category_id, 1)
    with pytest.raises(SelectionError, match="Runda 1 ma już 6"):
        selection.set_round(IDS[6], 1)
    assert selection.count(1) == 6


def test_category_moves_between_rounds_instead_of_duplicating():
    selection = CategorySelection()
    selection.set_round("k0", 1)
    selection.set_round("k0", 2)
    assert selection.rounds == {1: [], 2: ["k0"]}
    selection.set_round("k0", None)
    assert selection.round_of("k0") is None


def test_move_to_full_round_is_blocked_and_keeps_original():
    selection = CategorySelection()
    for category_id in IDS[:6]:
        selection.set_round(category_id, 2)
    selection.set_round("k10", 1)
    with pytest.raises(SelectionError):
        selection.set_round("k10", 2)
    assert selection.round_of("k10") == 1


def test_complete_only_with_six_plus_six():
    selection = CategorySelection()
    for category_id in IDS[:6]:
        selection.set_round(category_id, 1)
    assert not selection.is_complete()
    for category_id in IDS[6:12]:
        selection.set_round(category_id, 2)
    assert selection.is_complete()


def test_random_fill_keeps_manual_choices_and_prefers_unused():
    selection = CategorySelection()
    selection.set_round("k0", 1)
    used = set(IDS[12:])  # 12 nieużytych: k0..k11
    taken_used = selection.fill_randomly(IDS, used, random.Random(1))
    assert taken_used == 0
    assert selection.is_complete()
    assert selection.rounds[1][0] == "k0"
    chosen = selection.rounds[1] + selection.rounds[2]
    assert set(chosen) == set(IDS[:12])
    assert len(chosen) == len(set(chosen))  # bez powtórzeń


def test_random_fill_falls_back_to_used_categories():
    selection = CategorySelection()
    used = set(IDS[5:14])
    taken_used = selection.fill_randomly(IDS[:14], used, random.Random(2))
    assert selection.is_complete()
    assert taken_used == 7  # tylko 5 nieużytych, 7 trzeba dobrać z użytych


def test_random_fill_with_too_few_categories_fills_what_it_can():
    selection = CategorySelection()
    selection.fill_randomly(IDS[:8], set())
    assert selection.count(1) == 6 and selection.count(2) == 2
    assert not selection.is_complete()


def test_keep_only_drops_deleted_categories():
    selection = CategorySelection()
    selection.set_round("k0", 1)
    selection.set_round("k1", 2)
    selection.keep_only({"k1"})
    assert selection.rounds == {1: [], 2: ["k1"]}
