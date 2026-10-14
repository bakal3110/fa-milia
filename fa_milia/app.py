"""Uruchomienie aplikacji: przygotowanie danych i otwarcie głównego okna."""

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from fa_milia.config import APP_ID, APP_NAME
from fa_milia.core.library import Library
from fa_milia.core.paths import DataDir, default_data_root
from fa_milia.core.sample_data import install_if_first_run
from fa_milia.core.sets import SetStore
from fa_milia.core.settings import load_settings
from fa_milia.core.sounds import prepare_sounds_folder
from fa_milia.core.usage import UsageMemory
from fa_milia.resource_paths import resource_path
from fa_milia.ui.main_window import MainWindow


def _prepare_environment() -> None:
    """Ustawienia, które muszą zadziałać przed utworzeniem QApplication."""
    # Wyciszamy komunikaty diagnostyczne FFmpeg wypisywane przy każdym dźwięku.
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg*=false")
    if sys.platform == "win32":
        # Własny identyfikator aplikacji – dzięki niemu pasek zadań Windows
        # pokazuje ikonę Fa milii zamiast ikony Pythona.
        import ctypes  # import tylko na Windows

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FaMilia.Gra")


def main() -> int:
    _prepare_environment()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)  # łączy okno z plikiem .desktop (ikona w KDE)
    app.setStyle("Fusion")  # jednolity wygląd niezależnie od motywu systemu
    icon = QIcon(str(resource_path("icon.svg")))
    icon.addFile(str(resource_path("icon.png")))  # zapasowo, gdyby zabrakło obsługi SVG
    app.setWindowIcon(icon)

    data_dir = DataDir(default_data_root())
    data_dir.ensure()
    library = Library(data_dir)
    install_if_first_run(library, resource_path("sample_media"))
    library.remove_unused_media()
    try:
        prepare_sounds_folder(data_dir.sounds, resource_path("default_sounds"))
    except OSError:
        pass  # brak dźwięków nie może zatrzymać programu

    settings = load_settings(data_dir.settings_file)
    usage = UsageMemory(data_dir.usage_file)
    sets = SetStore(data_dir.sets_file)
    window = MainWindow(library, settings, usage, sets)
    if settings.fullscreen:
        window.showFullScreen()
    else:
        window.showMaximized()

    if library.load_errors:
        QMessageBox.warning(
            window,
            "Problem z danymi",
            "Niektórych plików nie udało się wczytać:\n\n" + "\n".join(library.load_errors),
        )

    # app.exec() uruchamia „pętlę zdarzeń” – program czeka na kliknięcia
    # i klawisze aż do zamknięcia okna. Zwraca kod zakończenia.
    return app.exec()
