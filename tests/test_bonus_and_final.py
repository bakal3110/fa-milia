import random

import pytest

from fa_milia.core.game_state import GameError, GameState, Phase
from fa_milia.core.history import GameHistory
from fa_milia.core.models import FinalQuestion, Question
from fa_milia.core.selection import choose_final
from tests.test_game_state import make_game, play_tile

BONUS = [(1, 3)]  # bonus w kolumnie 1, rząd 3 (300 pkt w rundzie 1)


def final_question() -> FinalQuestion:
    return FinalQuestion("Historia", Question(text="Kiedy chrzest Polski?", answer="966"))


# --- Bonus ---------------------------------------------------------------------


def test_new_game_draws_two_bonuses_per_round():
    game = GameState.new(["A"], make_game().rounds[0].categories,
                         make_game().rounds[1].categories, rng=random.Random(5))
    assert all(len(r.bonuses) == 2 for r in game.rounds)
    assert all(row != 1 for r in game.rounds for _c, row in r.bonuses)


def test_opening_bonus_tile_shows_bonus_screen():
    game = make_game(bonus_tiles=(BONUS, []))
    game.open_tile(1, 3)
    assert game.phase == Phase.BONUS
    assert game.current.is_bonus


def test_bonus_wager_limit_is_max_of_score_and_highest_tile():
    game = make_game(bonus_tiles=(BONUS, []))
    game.adjust_score(0, 1200)
    game.adjust_score(1, -400)
    game.open_tile(1, 3)
    assert game.max_bonus_wager(0) == 1200
    assert game.max_bonus_wager(1) == 500  # najwyższe pole rundy 1
    with pytest.raises(GameError, match="od 0 do 500"):
        game.set_bonus_wager(1, 600)
    with pytest.raises(GameError):
        game.set_bonus_wager(1, -1)
    game.set_bonus_wager(0, 1200)
    assert game.current.value == 1200


def test_bonus_question_needs_wager_first():
    game = make_game(bonus_tiles=(BONUS, []))
    game.open_tile(1, 3)
    with pytest.raises(GameError, match="Najpierw wybierz"):
        game.show_bonus_question()


def test_only_bonus_player_answers_for_wager():
    game = make_game(bonus_tiles=(BONUS, []))
    game.open_tile(1, 3)
    game.set_bonus_wager(2, 250)
    game.show_bonus_question()
    assert game.phase == Phase.QUESTION
    assert game.mark_value(0) is None
    with pytest.raises(GameError, match="nie odpowiada"):
        game.mark(0, True)
    assert game.mark(2, False) == -250
    assert game.players[2].score == -250
    game.close_question()
    assert game.round.is_used(1, 3)


def test_bonus_in_round_two_allows_up_to_1000():
    game = make_game(bonus_tiles=([], [(0, 2)]))
    game.end_round()
    game.next_round()
    game.open_tile(0, 2)
    assert game.max_bonus_wager(0) == 1000


def test_bonus_can_be_cancelled_before_question():
    game = make_game(bonus_tiles=(BONUS, []))
    game.open_tile(1, 3)
    game.cancel_question()
    assert game.phase == Phase.BOARD
    assert not game.round.is_used(1, 3)


def test_undo_bonus_wager():
    history = GameHistory(make_game(bonus_tiles=(BONUS, [])))
    history.apply("otwarcie", lambda s: s.open_tile(1, 3))
    history.apply("stawka", lambda s: s.set_bonus_wager(0, 300))
    history.undo()
    assert history.state.current.bonus_player is None
    assert history.state.phase == Phase.BONUS


# --- Finał ---------------------------------------------------------------------


def finish_rounds(game: GameState) -> None:
    for _ in range(2):
        game.end_round()
        game.next_round()


def test_game_without_final_finishes_after_round_two():
    game = make_game()
    finish_rounds(game)
    assert game.phase == Phase.FINISHED
    assert not game.final_skipped


def test_final_includes_only_players_with_positive_score():
    game = make_game(["Ania", "Bartek", "Celina"], final=final_question())
    game.adjust_score(0, 500)
    game.adjust_score(2, -100)  # Bartek ma 0 – też odpada
    finish_rounds(game)
    assert game.phase == Phase.FINAL_WAGERS
    assert game.final.participants == [0]
    assert game.current_question().text == "Kiedy chrzest Polski?"


def test_final_is_skipped_when_nobody_has_points():
    game = make_game(final=final_question())
    finish_rounds(game)
    assert game.phase == Phase.FINISHED
    assert game.final_skipped


def test_final_wagers_are_validated():
    game = make_game(["Ania", "Bartek"], final=final_question())
    game.adjust_score(0, 500)
    game.adjust_score(1, 300)
    finish_rounds(game)
    with pytest.raises(GameError, match="wszystkich"):
        game.start_final_question({0: 100})
    with pytest.raises(GameError, match="od 0 do 300"):
        game.start_final_question({0: 100, 1: 400})
    game.start_final_question({0: 500, 1: 0})
    assert game.phase == Phase.FINAL_QUESTION


def test_final_scoring_and_finish():
    game = make_game(["Ania", "Bartek", "Celina"], final=final_question())
    game.adjust_score(0, 500)
    game.adjust_score(1, 300)
    finish_rounds(game)
    game.start_final_question({0: 400, 1: 300})
    with pytest.raises(GameError, match="odsłoń"):
        game.finish_final()
    game.reveal_answer()
    assert game.is_revealed()
    assert game.mark(0, False) == -400
    assert game.mark(1, True) == 300
    with pytest.raises(GameError, match="nie odpowiada"):
        game.mark(2, True)  # Celina nie gra w finale
    with pytest.raises(GameError, match="ma już"):
        game.mark(1, True)
    game.finish_final()
    assert game.phase == Phase.FINISHED
    assert [p.score for p in game.players] == [100, 600, 0]


def test_game_with_final_round_trips_through_dict():
    game = make_game(["Ania"], bonus_tiles=(BONUS, [(2, 5)]), final=final_question())
    game.adjust_score(0, 100)
    finish_rounds(game)
    game.start_final_question({0: 50})
    assert GameState.from_dict(game.to_dict()) == game


def test_incomplete_final_question_is_rejected():
    with pytest.raises(GameError, match="finałowe"):
        make_game(final=FinalQuestion("Historia", Question(text="Pytanie bez odpowiedzi")))


def test_choose_final_prefers_unused():
    rng = random.Random(0)
    for _ in range(50):
        assert choose_final(["a", "b", "c"], {"a", "b"}, rng) == ("c", False)
    chosen, was_used = choose_final(["a", "b"], {"a", "b"}, rng)
    assert chosen in {"a", "b"} and was_used
    assert choose_final([], set(), rng) == (None, False)


def test_play_tile_helper_still_works_with_bonus_elsewhere():
    game = make_game(bonus_tiles=(BONUS, []))
    play_tile(game, 0, 3)
    assert game.phase == Phase.BOARD
