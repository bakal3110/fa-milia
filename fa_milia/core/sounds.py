"""Dźwięki i muzyka: nazwy plików, instrukcja i wyszukiwanie.

Program ma wbudowane dźwięki domyślne (fa_milia/resources/default_sounds/).
Folder sounds/ w katalogu danych służy tylko do ich podmiany: plik o tej
samej nazwie w sounds/ ma pierwszeństwo przed dźwiękiem wbudowanym.
"""

import hashlib
from pathlib import Path

# Kolejność sprawdzania rozszerzeń (opisana w instrukcji).
SOUND_EXTENSIONS_ORDER = (".mp3", ".ogg", ".wav")

# Nazwa pliku (bez rozszerzenia) → kiedy jest odtwarzany.
SOUND_EVENTS = {
    "board_fill": "muzyka przy pojawianiu się planszy na początku rundy",
    "premia": "trafienie na pole z premią",
    "good_answer": "dobra odpowiedź",
    "zla_odpowiedz": "zła odpowiedź",
    "time_up": "upływ czasu timera",
    "final": "początek finału (ekran z kategorią finałową)",
    "final_countdown": "muzyka w trakcie pytania finałowego (ok. 30 s)",
    "zwyciezca": "ekran zwycięzcy",
}

# Starsze nazwy plików w folderze użytkownika – używane, gdy brak pliku o nowej nazwie.
LEGACY_NAMES = {
    "board_fill": ["start_rundy"],
    "premia": ["bonus"],
    "good_answer": ["dobra_odpowiedz"],
    "time_up": ["koniec_czasu"],
}

INSTRUCTION_FILE = "INSTRUKCJA.txt"
OLD_DEFAULTS_MARKER = ".domyslne_dzwieki_dodane"

# Sumy kontrolne (SHA-256) dźwięków domyślnych, które starsze wersje programu
# kopiowały do folderu użytkownika. Takie nietknięte kopie usuwamy – inaczej
# przesłaniałyby nowe dźwięki wbudowane. Pliki użytkownika nigdy nie pasują do tych sum.
OLD_DEFAULT_HASHES = {
    "107a48a615a678ef1d34064a32718f769b2a26a705c1712139607148f44eed28",  # bonus.wav
    "07e4ef23e70db197359cc1557efff3621aa3b00f46f6cc55bf0d01c39d45ff36",  # dobra_odpowiedz.wav
    "ebe47e6229a5d05289fe836b860c91ad05c18113cb2fb92db09abbcb449012e8",  # final.wav
    "449f3c2f05b7bf7d42b1118ea18dc98e2617536520646344ad3840d0eb6733c7",  # koniec_czasu.wav
    "50cd799856b2bee7bea3a9f53b2e8650ab119114adab4dc0d729ee5a34629ae8",  # start_rundy.wav
    "67cecade8acec4bfb9be6d163705bfe11828f60ba4c594d26f4715d01cd07fc3",  # zla_odpowiedz.wav
    "a6274a904aa0dc9e379b823923c68a11fa6c5f7feeac4b37fbb5de3a6e3dc63c",  # zwyciezca.wav
}

INSTRUCTION_TEXT = """DŹWIĘKI I MUZYKA W GRZE FA MILIA
================================

Program ma wbudowane dźwięki i muzykę. Ten folder służy do ich PODMIANY:
wrzuć tu plik o jednej z poniższych nazw (wielkość liter bez znaczenia,
rozszerzenie .mp3, .ogg albo .wav), a program zagra go zamiast dźwięku
wbudowanego.

{events}

Przykład: plik „premia.mp3” w tym folderze zagra zamiast wbudowanej premii.
Żeby wrócić do dźwięku wbudowanego, usuń swój plik.

Jeśli są dwa pliki o tej samej nazwie (np. premia.mp3 i premia.wav),
program użyje pierwszego w kolejności: .mp3, .ogg, .wav.

Starsze nazwy (bonus, koniec_czasu, dobra_odpowiedz, start_rundy) nadal
działają, jeśli nie ma pliku o nowej nazwie.

Głośność ustawisz w programie: Ustawienia → Timer i dźwięk.
Ten plik jest odtwarzany na nowo przy każdym uruchomieniu programu.
"""


def instruction_text() -> str:
    events = "\n".join(f"  {name:<16} – {description}"
                       for name, description in SOUND_EVENTS.items())
    return INSTRUCTION_TEXT.format(events=events)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_sounds_folder(sounds_dir: Path, defaults_dir: Path | None) -> list[str]:
    """Tworzy folder dźwięków z instrukcją i usuwa stare, nietknięte kopie dźwięków domyślnych.

    Zwraca nazwy usuniętych plików.
    """
    sounds_dir.mkdir(parents=True, exist_ok=True)
    # Instrukcję zapisujemy zawsze – po aktualizacji programu opisuje nowe zasady.
    (sounds_dir / INSTRUCTION_FILE).write_text(instruction_text(), encoding="utf-8")

    known = set(OLD_DEFAULT_HASHES)
    if defaults_dir is not None and defaults_dir.is_dir():
        known.update(_file_hash(p) for p in defaults_dir.iterdir() if p.is_file())
    removed = []
    for path in sorted(sounds_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SOUND_EXTENSIONS_ORDER \
                and _file_hash(path) in known:
            path.unlink()
            removed.append(path.name)
    (sounds_dir / OLD_DEFAULTS_MARKER).unlink(missing_ok=True)
    return removed


def _find_in(folder: Path, names: list[str]) -> Path | None:
    if not folder.is_dir():
        return None
    # Słownik: nazwa pliku małymi literami → ścieżka (żeby „Premia.MP3” też działała).
    files = {path.name.lower(): path for path in folder.iterdir() if path.is_file()}
    for candidate in names:
        for extension in SOUND_EXTENSIONS_ORDER:
            path = files.get(candidate + extension)
            if path is not None:
                return path
    return None


def find_sound(sounds_dir: Path, name: str, defaults_dir: Path | None = None) -> Path | None:
    """Szuka dźwięku: najpierw w folderze użytkownika (nowa i starsze nazwy),
    potem wśród dźwięków wbudowanych. None, jeśli nigdzie go nie ma."""
    found = _find_in(sounds_dir, [name] + LEGACY_NAMES.get(name, []))
    if found is None and defaults_dir is not None:
        found = _find_in(defaults_dir, [name])
    return found


def is_builtin(path: Path, defaults_dir: Path | None) -> bool:
    return defaults_dir is not None and path.parent == defaults_dir
