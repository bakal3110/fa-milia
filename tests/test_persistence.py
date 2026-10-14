"""Pamięć wykorzystania, zestawy, zapis gry i kopia zapasowa."""

import zipfile

import pytest

from fa_milia.core.backup import BackupError, create_backup, restore_backup
from fa_milia.core.history import GameHistory
from fa_milia.core.library import Library
from fa_milia.core.models import ContentKind, Question
from fa_milia.core.savegame import delete_game, describe_game, load_game, save_game
from fa_milia.core.sets import GameSet, SetStore, set_problems
from fa_milia.core.usage import UsageMemory
from tests.test_game_state import make_game
from tests.test_models import complete_category

# --- Pamięć wykorzystania ---------------------------------------------------------


def test_usage_survives_restart_and_reset(data_dir):
    usage = UsageMemory(data_dir.usage_file)
    usage.mark_categories(["a", "b"])
    usage.mark_final("f1")

    restarted = UsageMemory(data_dir.usage_file)
    assert restarted.is_category_used("a") and restarted.is_final_used("f1")
    assert restarted.used_category_ids() == {"a", "b"}

    restarted.unmark_category("a")
    assert UsageMemory(data_dir.usage_file).used_category_ids() == {"b"}

    restarted.reset()
    fresh = UsageMemory(data_dir.usage_file)
    assert fresh.used_category_ids() == set() and fresh.used_final_ids() == set()


def test_marking_twice_keeps_first_date(data_dir):
    usage = UsageMemory(data_dir.usage_file)
    usage.categories["a"] = "2020-01-01T10:00"
    usage.mark_categories(["a"])
    assert usage.categories["a"] == "2020-01-01T10:00"


def test_broken_usage_file_means_nothing_used(data_dir):
    data_dir.usage_file.write_text("{{{", encoding="utf-8")
    assert UsageMemory(data_dir.usage_file).used_category_ids() == set()


# --- Zestawy ----------------------------------------------------------------------


def test_sets_store_put_replace_delete(data_dir):
    store = SetStore(data_dir.sets_file)
    store.put(GameSet("Wieczór", ["a"] * 6, ["b"] * 6, "f"))
    store.put(GameSet("wieczór", ["c"] * 6, ["d"] * 6))  # ta sama nazwa → zastępuje
    assert len(SetStore(data_dir.sets_file).sets) == 1
    assert SetStore(data_dir.sets_file).find("WIECZÓR").round1 == ["c"] * 6

    store.put(GameSet("Nowa nazwa", ["c"] * 6, ["d"] * 6), replace_name="Wieczór")
    assert [s.name for s in SetStore(data_dir.sets_file).sets] == ["Nowa nazwa"]
    store.delete("nowa nazwa")
    assert SetStore(data_dir.sets_file).sets == []


def test_set_problems_report_deleted_and_incomplete(library):
    categories = [complete_category(f"K{i}") for i in range(12)]
    for category in categories:
        library.save_category(category)
    ids = [c.id for c in categories]
    good = GameSet("Dobry", ids[:6], ids[6:])
    assert set_problems(good, library) == []

    library.delete_category(ids[0])
    categories[1].questions[0].answer = ""
    library.save_category(categories[1])
    problems = set_problems(GameSet("Zły", ids[:6], ids[6:], final="brak"), library)
    assert "runda 1: kategoria została usunięta" in problems
    assert "runda 1: kategoria „K1” jest niekompletna" in problems
    assert "pytanie finałowe zostało usunięte" in problems


# --- Zapis gry ------------------------------------------------------------------------


def test_save_and_load_game_keeps_history(data_dir):
    history = GameHistory(make_game())
    history.apply("otwarcie", lambda s: s.open_tile(0, 1))
    history.apply("Ania +100", lambda s: s.mark(0, True))
    save_game(data_dir.savegame_file, history)

    loaded = load_game(data_dir.savegame_file)
    assert loaded.state == history.state
    assert loaded.undo() == "Ania +100"
    assert loaded.state.players[0].score == 0
    assert describe_game(history) == "Ania, Bartek, Celina · runda 1"

    delete_game(data_dir.savegame_file)
    assert load_game(data_dir.savegame_file) is None


def test_broken_savegame_is_ignored(data_dir):
    data_dir.savegame_file.write_text('{"version": 1}', encoding="utf-8")
    assert load_game(data_dir.savegame_file) is None


def test_media_of_saved_game_is_not_cleaned_up(library, data_dir, sample_image):
    media = library.import_media(sample_image)
    category = complete_category("Z obrazkiem")
    category.questions[0] = Question(ContentKind.IMAGE, "", media, "Flaga")
    library.save_category(category)
    others = [complete_category(f"K{i}") for i in range(11)]
    from fa_milia.core.game_state import GameState
    state = GameState.new(["A"], [category] + others[:5], others[5:], bonus_tiles=[[], []])
    save_game(data_dir.savegame_file, GameHistory(state))

    library.delete_category(category.id)  # kategoria usunięta z biblioteki w trakcie gry
    library.remove_unused_media()
    assert library.media_path(media).exists()


# --- Kopia zapasowa ---------------------------------------------------------------


def test_backup_and_restore_whole_data_dir(tmp_path, library, data_dir, sample_image):
    category = complete_category("Do kopii")
    library.save_category(category)
    media = library.import_media(sample_image)
    UsageMemory(data_dir.usage_file).mark_categories([category.id])
    (data_dir.sounds / "bonus.mp3").write_bytes(b"dzwiek")
    data_dir.settings_file.write_text('{"game_scale": 150}', encoding="utf-8")

    backup = tmp_path / "kopia.zip"
    assert create_backup(data_dir, backup) >= 5

    # Psujemy dane po zrobieniu kopii…
    library.delete_category(category.id)
    library.media_path(media).unlink()
    data_dir.settings_file.write_text("{}", encoding="utf-8")

    previous = restore_backup(data_dir, backup)
    restored = Library(data_dir)
    assert restored.categories[category.id].name == "Do kopii"
    assert restored.media_path(media).exists()
    assert UsageMemory(data_dir.usage_file).is_category_used(category.id)
    assert (data_dir.sounds / "bonus.mp3").read_bytes() == b"dzwiek"
    assert "150" in data_dir.settings_file.read_text(encoding="utf-8")
    assert previous.exists()  # stare dane odłożone na bok, nie skasowane


def test_restore_rejects_foreign_zip(tmp_path, data_dir):
    foreign = tmp_path / "obcy.zip"
    with zipfile.ZipFile(foreign, "w") as archive:
        archive.writestr("cokolwiek.txt", "x")
    with pytest.raises(BackupError, match="nie jest kopia"):
        restore_backup(data_dir, foreign)
    not_zip = tmp_path / "x.zip"
    not_zip.write_text("abc")
    with pytest.raises(BackupError):
        restore_backup(data_dir, not_zip)
    assert data_dir.root.exists()


def test_savegame_stays_small_with_long_history(data_dir):
    """Migawki nie zawierają treści pytań, więc zapis nie puchnie z każdą akcją."""
    history = GameHistory(make_game())
    for column in range(6):
        for row in range(1, 6):
            history.apply("o", lambda s, c=column, r=row: s.open_tile(c, r))
            history.apply("p", lambda s: s.mark(0, True))
            history.apply("z", lambda s: s.close_question())
    save_game(data_dir.savegame_file, history)
    assert data_dir.savegame_file.stat().st_size < 400_000
    loaded = load_game(data_dir.savegame_file)
    for _ in range(90):
        loaded.undo()
    assert loaded.state.round.remaining() == 30
    assert [p.score for p in loaded.state.players] == [0, 0, 0]
    assert loaded.state.rounds[0].categories[0].name == "R1 K0"  # treść pytań zachowana


def test_restore_keeps_data_when_folder_cannot_be_moved(tmp_path, data_dir, monkeypatch):
    backup = tmp_path / "kopia.zip"
    create_backup(data_dir, backup)
    (data_dir.categories / "moja.json").write_text("{}", encoding="utf-8")

    original_rename = type(data_dir.root).rename

    def locked_rename(self, target):
        if self == data_dir.root:
            raise PermissionError("plik w użyciu")
        return original_rename(self, target)

    monkeypatch.setattr(type(data_dir.root), "rename", locked_rename)
    with pytest.raises(BackupError, match="w użyciu"):
        restore_backup(data_dir, backup)
    assert (data_dir.categories / "moja.json").exists()
    assert not data_dir.root.with_name(data_dir.root.name + "-przywracanie").exists()
