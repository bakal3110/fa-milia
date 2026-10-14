"""Dźwięki i muzyka: nazwy plików, instrukcja i wyszukiwanie w folderze sounds/."""

import shutil
from pathlib import Path

# Kolejność sprawdzania rozszerzeń (opisana w instrukcji).
SOUND_EXTENSIONS_ORDER = (".mp3", ".ogg", ".wav")

# Nazwa pliku (bez rozszerzenia) → kiedy jest odtwarzany.
SOUND_EVENTS = {
    "board_fill": "muzyka przy pojawianiu się planszy na początku rundy (ok. 2,5 s)",
    "premia": "trafienie na pole z premią",
    "good_answer": "dobra odpowiedź",
    "zla_odpowiedz": "zła odpowiedź",
    "time_up": "upływ czasu timera",
    "final": "początek finału (ekran z kategorią finałową)",
    "final_countdown": "muzyka w trakcie pytania finałowego (ok. 30 s)",
    "zwyciezca": "ekran zwycięzcy",
}

# Starsze nazwy plików – używane, gdy brak pliku o nowej nazwie.
# Dzięki temu dźwięki dodane wcześniej (np. bonus.wav) nadal działają.
LEGACY_NAMES = {
    "board_fill": ["start_rundy"],
    "premia": ["bonus"],
    "good_answer": ["dobra_odpowiedz"],
    "time_up": ["koniec_czasu"],
}

INSTRUCTION_FILE = "INSTRUKCJA.txt"
DEFAULTS_MARKER = ".domyslne_dzwieki_dodane"

INSTRUCTION_TEXT = """DŹWIĘKI I MUZYKA W GRZE FA MILIA
================================

Do tego folderu możesz wrzucić własne dźwięki i muzykę. Program odtwarza je
w określonych momentach gry. Plik musi mieć jedną z poniższych nazw
(wielkość liter bez znaczenia) i rozszerzenie .mp3, .ogg albo .wav.

{events}

Przykład: plik „premia.mp3” zagra, gdy ktoś trafi na pole z premią.

Jeśli są dwa pliki o tej samej nazwie (np. premia.mp3 i premia.wav),
program użyje pierwszego w kolejności: .mp3, .ogg, .wav.

Starsze nazwy (bonus, koniec_czasu, dobra_odpowiedz, start_rundy) nadal
działają, jeśli nie ma pliku o nowej nazwie.

Brak pliku nie jest błędem – program po prostu nie zagra dźwięku.
Głośność ustawisz w programie: Ustawienia → Timer i dźwięk.

Ten plik jest odtwarzany na nowo przy każdym uruchomieniu programu.
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
    # Instrukcję zapisujemy zawsze – po aktualizacji programu opisuje nowe nazwy.
    (sounds_dir / INSTRUCTION_FILE).write_text(instruction_text(), encoding="utf-8")

    marker = sounds_dir / DEFAULTS_MARKER
    if marker.exists() or defaults_dir is None or not defaults_dir.is_dir():
        return
    for source in sorted(defaults_dir.iterdir()):
        name = source.stem.lower()
        if name in SOUND_EVENTS and find_sound(sounds_dir, name) is None:
            shutil.copyfile(source, sounds_dir / source.name)
    marker.write_text("Dźwięki domyślne zostały dodane.\n", encoding="utf-8")


def find_sound(sounds_dir: Path, name: str) -> Path | None:
    """Szuka pliku dźwięku o danej nazwie (np. "premia"). None, jeśli go nie ma.

    Najpierw nowa nazwa we wszystkich rozszerzeniach, potem starsze nazwy.
    """
    if not sounds_dir.is_dir():
        return None
    # Słownik: nazwa pliku małymi literami → ścieżka (żeby „Premia.MP3” też działała).
    files = {path.name.lower(): path for path in sounds_dir.iterdir() if path.is_file()}
    for candidate in [name] + LEGACY_NAMES.get(name, []):
        for extension in SOUND_EXTENSIONS_ORDER:
            path = files.get(candidate + extension)
            if path is not None:
                return path
    return None
