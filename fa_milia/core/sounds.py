"""Dźwięki efektów: nazwy plików, instrukcja i wyszukiwanie w folderze sounds/."""

import shutil
from pathlib import Path

# Kolejność sprawdzania rozszerzeń (opisana w instrukcji).
SOUND_EXTENSIONS_ORDER = (".wav", ".ogg", ".mp3")

# Nazwa pliku (bez rozszerzenia) → kiedy jest odtwarzany.
SOUND_EVENTS = {
    "bonus": "trafienie na pole bonusowe (zalecany)",
    "koniec_czasu": "upływ czasu na odpowiedź (zalecany)",
    "dobra_odpowiedz": "prowadzący oznaczył dobrą odpowiedź",
    "zla_odpowiedz": "prowadzący oznaczył złą odpowiedź",
    "start_rundy": "początek rundy 1 i rundy 2",
    "final": "początek finału",
    "zwyciezca": "ekran zwycięzcy",
}

INSTRUCTION_FILE = "INSTRUKCJA.txt"
DEFAULTS_MARKER = ".domyslne_dzwieki_dodane"

INSTRUCTION_TEXT = """DŹWIĘKI W GRZE FA MILIA
=======================

Do tego folderu możesz wrzucić własne dźwięki. Program odtwarza je
w określonych momentach gry. Plik musi mieć jedną z poniższych nazw
(wielkość liter bez znaczenia) i rozszerzenie .wav, .ogg albo .mp3.

{events}

Przykład: plik „bonus.mp3” zagra, gdy ktoś trafi na pole bonusowe.

Jeśli są dwa pliki o tej samej nazwie (np. bonus.wav i bonus.mp3),
program użyje pierwszego w kolejności: .wav, .ogg, .mp3.

Brak pliku nie jest błędem – program po prostu nie zagra dźwięku.
Głośność ustawisz w programie: Ustawienia → Timer i dźwięk.

Przy pierwszym uruchomieniu program dodał tu proste dźwięki domyślne.
Możesz je dowolnie podmienić albo usunąć – nie wrócą.
"""


def instruction_text() -> str:
    events = "\n".join(f"  {name:<16} – {description}"
                       for name, description in SOUND_EVENTS.items())
    return INSTRUCTION_TEXT.format(events=events)


def prepare_sounds_folder(sounds_dir: Path, defaults_dir: Path | None) -> None:
    """Tworzy folder dźwięków z instrukcją; przy pierwszym razie dodaje dźwięki domyślne.

    Istniejące pliki użytkownika nigdy nie są nadpisywane.
    """
    sounds_dir.mkdir(parents=True, exist_ok=True)
    instruction = sounds_dir / INSTRUCTION_FILE
    if not instruction.exists():
        instruction.write_text(instruction_text(), encoding="utf-8")

    marker = sounds_dir / DEFAULTS_MARKER
    if marker.exists() or defaults_dir is None or not defaults_dir.is_dir():
        return
    for source in sorted(defaults_dir.iterdir()):
        name = source.stem.lower()
        if name in SOUND_EVENTS and find_sound(sounds_dir, name) is None:
            shutil.copyfile(source, sounds_dir / source.name)
    marker.write_text("Dźwięki domyślne zostały dodane.\n", encoding="utf-8")


def find_sound(sounds_dir: Path, name: str) -> Path | None:
    """Szuka pliku dźwięku o danej nazwie (np. "bonus"). None, jeśli go nie ma."""
    if not sounds_dir.is_dir():
        return None
    # Słownik: nazwa pliku małymi literami → ścieżka (żeby „Bonus.MP3” też działał).
    files = {path.name.lower(): path for path in sounds_dir.iterdir() if path.is_file()}
    for extension in SOUND_EXTENSIONS_ORDER:
        path = files.get(name + extension)
        if path is not None:
            return path
    return None
