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


def test_prepare_folder_writes_instruction_and_defaults_once(tmp_path):
    defaults = tmp_path / "defaults"
    defaults.mkdir()
    (defaults / "premia.wav").write_bytes(b"domyslny")
    (defaults / "nieznany.wav").write_bytes(b"x")
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    (sounds / "premia.mp3").write_bytes(b"uzytkownika")

    prepare_sounds_folder(sounds, defaults)
    text = (sounds / INSTRUCTION_FILE).read_text(encoding="utf-8")
    assert all(name in text for name in SOUND_EVENTS)
    # Plik użytkownika (premia.mp3) wygrywa – domyślny premia.wav nie jest kopiowany.
    assert not (sounds / "premia.wav").exists()
    assert not (sounds / "nieznany.wav").exists()

    # Usunięty przez użytkownika dźwięk nie wraca przy kolejnym uruchomieniu.
    (sounds / "premia.mp3").unlink()
    prepare_sounds_folder(sounds, defaults)
    assert find_sound(sounds, "premia") is None
