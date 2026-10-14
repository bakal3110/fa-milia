"""Położenie katalogu z danymi użytkownika.

- Linux: ~/.local/share/fa-milia/ (standard XDG).
- Windows, program spakowany do .exe: folder „Fa milia - dane” obok pliku .exe
  (wersja „przenośna”). Gdy tam nie da się zapisywać (np. Program Files),
  awaryjnie %APPDATA%\\fa-milia.
- Windows, uruchomienie z kodu źródłowego: %APPDATA%\\fa-milia.

Zmienna środowiskowa FA_MILIA_DATA_DIR pozwala wskazać dowolny inny katalog,
co przydaje się w testach i przy eksperymentach.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from fa_milia.config import APP_ID

PORTABLE_FOLDER_NAME = "Fa milia - dane"


def _is_writable(folder: Path) -> bool:
    """Sprawdza w praktyce, czy w folderze da się utworzyć plik."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".test_zapisu"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _windows_appdata() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / APP_ID


def default_data_root() -> Path:
    """Zwraca ścieżkę katalogu danych (w razie potrzeby sprawdza możliwość zapisu)."""
    override = os.environ.get("FA_MILIA_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        # sys.frozen ustawia PyInstaller – oznacza „uruchomiono spakowany .exe”.
        if getattr(sys, "frozen", False):
            portable = Path(sys.executable).resolve().parent / PORTABLE_FOLDER_NAME
            if _is_writable(portable):
                return portable
        return _windows_appdata()

    # XDG_DATA_HOME zwykle nie jest ustawione – wtedy standard mówi o ~/.local/share.
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_ID


# frozen=True sprawia, że obiektu nie da się zmienić po utworzeniu.
# To bezpieczne, bo ścieżki nie powinny się zmieniać w trakcie działania.
@dataclass(frozen=True)
class DataDir:
    """Wszystkie ścieżki w katalogu danych w jednym miejscu."""

    root: Path

    # @property pozwala odczytywać metodę jak zwykły atrybut:
    # data_dir.categories zamiast data_dir.categories().
    @property
    def categories(self) -> Path:
        return self.root / "categories"

    @property
    def finals(self) -> Path:
        return self.root / "finals"

    @property
    def media(self) -> Path:
        return self.root / "media"

    @property
    def sounds(self) -> Path:
        return self.root / "sounds"

    @property
    def sets_file(self) -> Path:
        return self.root / "sets.json"

    @property
    def usage_file(self) -> Path:
        return self.root / "usage.json"

    @property
    def settings_file(self) -> Path:
        return self.root / "settings.json"

    @property
    def savegame_file(self) -> Path:
        return self.root / "savegame.json"

    @property
    def sample_marker(self) -> Path:
        """Plik-znacznik: istnieje, jeśli przykładowe dane zostały już dodane."""
        return self.root / ".sample_data_installed"

    def ensure(self) -> None:
        """Tworzy brakujące katalogi (istniejące zostawia w spokoju)."""
        for folder in (self.root, self.categories, self.finals, self.media, self.sounds):
            folder.mkdir(parents=True, exist_ok=True)
