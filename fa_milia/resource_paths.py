"""Ścieżki do plików dołączonych do programu (ikona, przykładowe media).

Po spakowaniu PyInstallerem pliki programu są rozpakowywane do katalogu
tymczasowego, którego ścieżkę PyInstaller zapisuje w sys._MEIPASS.
"""

import sys
from pathlib import Path


def resources_dir() -> Path:
    # getattr z wartością domyślną: jeśli atrybutu nie ma (zwykłe uruchomienie),
    # dostajemy None zamiast błędu.
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "fa_milia" / "resources"
    return Path(__file__).resolve().parent / "resources"


def resource_path(*parts: str) -> Path:
    """Np. resource_path("icon.svg") albo resource_path("sample_media")."""
    return resources_dir().joinpath(*parts)
