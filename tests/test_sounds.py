from fa_milia.core.sounds import (
    INSTRUCTION_FILE,
    SOUND_EVENTS,
    find_sound,
    prepare_sounds_folder,
)


def test_find_sound_ignores_case_and_prefers_mp3(tmp_path):
    (tmp_path / "Premia.WAV").write_bytes(b"x")
    assert find_sound(tmp_path, "premia").name == "Premia.WAV"
    (tmp_path / "premia.mp3").write_bytes(b"x")
    assert find_sound(tmp_path, "premia").name == "premia.mp3"


def test_legacy_names_are_used_only_without_new_file(tmp_path):
    (tmp_path / "bonus.wav").write_bytes(b"x")
    (tmp_path / "koniec_czasu.wav").write_bytes(b"x")
    assert find_sound(tmp_path, "premia").name == "bonus.wav"
    assert find_sound(tmp_path, "time_up").name == "koniec_czasu.wav"
    (tmp_path / "time_up.mp3").write_bytes(b"x")
    assert find_sound(tmp_path, "time_up").name == "time_up.mp3"


def test_missing_sound_or_folder_is_not_an_error(tmp_path):
    assert find_sound(tmp_path, "koniec_czasu") is None
    assert find_sound(tmp_path / "nie_ma", "bonus") is None


def test_prepare_folder_writes_instruction_and_removes_old_default_copies(tmp_path):
    defaults = tmp_path / "defaults"
    defaults.mkdir()
    (defaults / "premia.mp3").write_bytes(b"wbudowany")
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    (sounds / "premia.mp3").write_bytes(b"wbudowany")  # nietknięta kopia wbudowanego
    (sounds / "time_up.mp3").write_bytes(b"moj wlasny")  # plik użytkownika
    (sounds / ".domyslne_dzwieki_dodane").write_text("x")

    removed = prepare_sounds_folder(sounds, defaults)
    assert removed == ["premia.mp3"]
    assert (sounds / "time_up.mp3").exists()
    assert not (sounds / ".domyslne_dzwieki_dodane").exists()
    text = (sounds / INSTRUCTION_FILE).read_text(encoding="utf-8")
    assert all(name in text for name in SOUND_EVENTS)


def test_old_generated_default_copies_are_recognised(tmp_path):
    """Stare kopie (np. bonus.wav z poprzedniej wersji) są rozpoznawane po sumie SHA-256."""
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    from tests.conftest import SAMPLE_MEDIA
    generated = SAMPLE_MEDIA.parent / "default_sounds" / "zla_odpowiedz.wav"
    (sounds / "zla_odpowiedz.wav").write_bytes(generated.read_bytes())
    assert prepare_sounds_folder(sounds, None) == ["zla_odpowiedz.wav"]


def test_user_file_wins_over_builtin(tmp_path):
    defaults = tmp_path / "defaults"
    defaults.mkdir()
    (defaults / "premia.mp3").write_bytes(b"wbudowany")
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    assert find_sound(sounds, "premia", defaults) == defaults / "premia.mp3"
    (sounds / "bonus.wav").write_bytes(b"stara nazwa")
    assert find_sound(sounds, "premia", defaults).name == "bonus.wav"
    (sounds / "Premia.ogg").write_bytes(b"nowy")
    assert find_sound(sounds, "premia", defaults).name == "Premia.ogg"
    assert find_sound(sounds, "nie_ma", defaults) is None


def test_all_events_have_builtin_sounds():
    from tests.conftest import SAMPLE_MEDIA
    defaults = SAMPLE_MEDIA.parent / "default_sounds"
    empty = defaults / "nie_istnieje"
    for name in SOUND_EVENTS:
        assert find_sound(empty, name, defaults) is not None, name
