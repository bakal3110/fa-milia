from fa_milia.core.sounds import (
    INSTRUCTION_FILE,
    SOUND_EVENTS,
    find_sound,
    prepare_sounds_folder,
)


def test_find_sound_ignores_case_and_prefers_wav(tmp_path):
    (tmp_path / "Bonus.MP3").write_bytes(b"x")
    assert find_sound(tmp_path, "bonus").name == "Bonus.MP3"
    (tmp_path / "bonus.wav").write_bytes(b"x")
    assert find_sound(tmp_path, "bonus").name == "bonus.wav"


def test_missing_sound_or_folder_is_not_an_error(tmp_path):
    assert find_sound(tmp_path, "koniec_czasu") is None
    assert find_sound(tmp_path / "nie_ma", "bonus") is None


def test_prepare_folder_writes_instruction_and_defaults_once(tmp_path):
    defaults = tmp_path / "defaults"
    defaults.mkdir()
    (defaults / "bonus.wav").write_bytes(b"domyslny")
    (defaults / "nieznany.wav").write_bytes(b"x")
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    (sounds / "bonus.mp3").write_bytes(b"uzytkownika")

    prepare_sounds_folder(sounds, defaults)
    text = (sounds / INSTRUCTION_FILE).read_text(encoding="utf-8")
    assert all(name in text for name in SOUND_EVENTS)
    # Plik użytkownika (bonus.mp3) wygrywa – domyślny bonus.wav nie jest kopiowany.
    assert not (sounds / "bonus.wav").exists()
    assert not (sounds / "nieznany.wav").exists()

    # Usunięty przez użytkownika dźwięk nie wraca przy kolejnym uruchomieniu.
    (sounds / "bonus.mp3").unlink()
    prepare_sounds_folder(sounds, defaults)
    assert find_sound(sounds, "bonus") is None
