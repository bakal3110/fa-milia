import pytest

from fa_milia.config import ROUND_VALUES, ROW_COUNT
from fa_milia.core.game_state import GameError, GameState, Phase
from fa_milia.core.history import GameHistory
from tests.test_models import complete_category


def make_game(players=("Ania", "Bartek", "Celina")) -> GameState:
    round1 = [complete_category(f"R1 K{i}") for i in range(6)]
    round2 = [complete_category(f"R2 K{i}") for i in range(6)]
    return GameState.new(list(players), round1, round2)


def play_tile(game: GameState, column: int, row: int) -> None:
    game.open_tile(column, row)
    game.reveal_answer()
    game.close_question()


# --- Tworzenie gry -----------------------------------------------------------


def test_new_game_starts_on_round_one_board():
    game = make_game()
    assert game.phase == Phase.BOARD
    assert game.round.number == 1
    assert [p.score for p in game.players] == [0, 0, 0]
    assert game.round.remaining() == 30


@pytest.mark.parametrize("names, message", [
    ([], "od 1 do 8"),
    ([f"G{i}" for i in range(9)], "od 1 do 8"),
    (["Ania", "  "], "musi mieć imię"),
    (["Ania", "ania "], "muszą być różne"),
])
def test_invalid_players_are_rejected(names, message):
    with pytest.raises(GameError, match=message):
        make_game(names)


def test_names_are_trimmed():
    assert make_game(["  Ania "]).players[0].name == "Ania"


def test_round_needs_six_complete_categories():
    categories = [complete_category(f"K{i}") for i in range(12)]
    with pytest.raises(GameError, match="6 kategorii"):
        GameState.new(["A"], categories[:5], categories[6:])
    categories[0].questions[0].answer = ""
    with pytest.raises(GameError, match="niekompletna"):
        GameState.new(["A"], categories[:6], categories[6:])


def test_category_cannot_be_in_both_rounds():
    categories = [complete_category(f"K{i}") for i in range(11)]
    with pytest.raises(GameError, match="obu rundach"):
        GameState.new(["A"], categories[:6], categories[5:])


def test_game_uses_copies_of_categories():
    round1 = [complete_category(f"K{i}") for i in range(6)]
    round2 = [complete_category(f"L{i}") for i in range(6)]
    game = GameState.new(["A"], round1, round2)
    round1[0].questions[0].text = "zmienione w edytorze"
    assert game.rounds[0].categories[0].questions[0].text == "Pytanie 1"


# --- Wartości pól ------------------------------------------------------------


def test_tile_values_depend_on_row_and_round():
    game = make_game()
    assert [game.rounds[0].value(r) for r in range(1, 6)] == [100, 200, 300, 400, 500]
    assert [game.rounds[1].value(r) for r in range(1, 6)] == [200, 400, 600, 800, 1000]
    assert ROUND_VALUES[1] == (100, 200, 300, 400, 500)


def test_open_tile_shows_question_from_matching_row():
    game = make_game()
    game.open_tile(2, 4)
    assert game.phase == Phase.QUESTION
    assert game.current.value == 400
    assert game.current_category().name == "R1 K2"
    assert game.current_question().text == "Pytanie 4"


# --- Punktacja ---------------------------------------------------------------


def test_correct_and_wrong_answers_change_score():
    game = make_game()
    game.open_tile(0, 3)
    game.reveal_answer()
    assert game.mark(0, correct=False) == -300
    assert game.mark(1, correct=True) == 300
    assert [p.score for p in game.players] == [-300, 300, 0]


def test_player_cannot_be_marked_twice_for_one_question():
    game = make_game()
    game.open_tile(0, 1)
    game.mark(0, True)
    with pytest.raises(GameError, match="ma już ocenioną"):
        game.mark(0, False)
    assert game.players[0].score == 100


def test_marking_does_not_close_the_question():
    game = make_game()
    game.open_tile(0, 1)
    game.mark(0, True)
    assert game.phase == Phase.QUESTION


def test_close_question_empties_tile():
    game = make_game()
    play_tile(game, 1, 2)
    assert game.phase == Phase.BOARD
    assert game.round.is_used(1, 2)
    with pytest.raises(GameError, match="wykorzystane"):
        game.open_tile(1, 2)


def test_cancel_question_keeps_tile_on_board():
    game = make_game()
    game.open_tile(1, 2)
    game.cancel_question()
    assert game.phase == Phase.BOARD
    assert not game.round.is_used(1, 2)


def test_cannot_cancel_after_reveal():
    game = make_game()
    game.open_tile(1, 2)
    game.reveal_answer()
    with pytest.raises(GameError):
        game.cancel_question()


def test_actions_in_wrong_phase_are_rejected():
    game = make_game()
    with pytest.raises(GameError):
        game.mark(0, True)  # brak otwartego pytania
    game.open_tile(0, 1)
    with pytest.raises(GameError):
        game.open_tile(0, 2)  # pytanie już otwarte


def test_manual_score_adjustment():
    game = make_game()
    game.adjust_score(2, 150)
    game.adjust_score(2, -50)
    assert game.players[2].score == 100


# --- Przebieg rund -----------------------------------------------------------


def test_round_ends_after_all_tiles():
    game = make_game()
    for column in range(6):
        for row in range(1, ROW_COUNT + 1):
            play_tile(game, column, row)
    assert game.phase == Phase.ROUND_END
    game.next_round()
    assert game.phase == Phase.BOARD
    assert game.round.number == 2
    assert game.round.remaining() == 30


def test_round_can_end_early_and_game_finishes_after_round_two():
    game = make_game()
    play_tile(game, 0, 1)
    game.end_round()
    game.next_round()
    game.end_round()
    game.next_round()
    assert game.phase == Phase.FINISHED


def test_ranking_shares_place_on_tie():
    game = make_game(["Ania", "Bartek", "Celina", "Darek"])
    for index, score in enumerate([300, 500, 300, -100]):
        game.adjust_score(index, score)
    ranking = [(place, player.name) for place, player in game.ranking()]
    assert ranking == [(1, "Bartek"), (2, "Ania"), (2, "Celina"), (4, "Darek")]


def test_state_round_trip_through_dict():
    game = make_game()
    game.open_tile(3, 5)
    game.mark(1, True)
    restored = GameState.from_dict(game.to_dict())
    assert restored == game


# --- Cofanie -----------------------------------------------------------------


def test_undo_reverts_score_and_restores_tile():
    history = GameHistory(make_game())
    history.apply("otwarcie", lambda s: s.open_tile(0, 2))
    history.apply("Ania +200", lambda s: s.mark(0, True))
    history.apply("zamknięcie", lambda s: s.close_question())
    assert history.state.round.is_used(0, 2)

    assert history.undo() == "zamknięcie"
    assert history.state.phase == Phase.QUESTION
    assert not history.state.round.is_used(0, 2)
    assert history.undo() == "Ania +200"
    assert history.state.players[0].score == 0
    assert history.undo() == "otwarcie"
    assert history.state.phase == Phase.BOARD
    assert history.undo() is None


def test_failed_action_leaves_no_history_and_no_changes():
    history = GameHistory(make_game())
    with pytest.raises(GameError):
        history.apply("błąd", lambda s: s.mark(0, True))
    assert not history.can_undo()
    assert history.state.players[0].score == 0


def test_history_round_trip_through_dict():
    history = GameHistory(make_game())
    history.apply("otwarcie", lambda s: s.open_tile(0, 1))
    restored = GameHistory.from_dict(history.to_dict())
    assert restored.state == history.state
    assert restored.last_label() == "otwarcie"
    restored.undo()
    assert restored.state.phase == Phase.BOARD
