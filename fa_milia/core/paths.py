"""Położenie katalogu z danymi użytkownika.

Domyślnie jest to ~/.local/share/fa-milia/ (standard XDG w Linuksie).
Zmienna środowiskowa FA_MILIA_DATA_DIR pozwala wskazać inny katalog,
co przydaje się w testach i przy eksperymentach.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from fa_milia.config import APP_ID


def default_data_root() -> Path:
    """Zwraca ścieżkę katalogu danych (jeszcze go nie tworzy)."""
    override = os.environ.get("FA_MILIA_DATA_DIR")
    if override:
        return Path(override).expanduser()

    # XDG_DATA_HOME zwykle nie jest ustawione – wtedy standard mówi
    # o ~/.local/share.
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
