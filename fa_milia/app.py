"""Uruchomienie aplikacji: przygotowanie danych i otwarcie głównego okna."""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from fa_milia.config import APP_ID, APP_NAME
from fa_milia.core.library import Library
from fa_milia.core.paths import DataDir, default_data_root
from fa_milia.core.sample_data import install_if_first_run
from fa_milia.resource_paths import resource_path
from fa_milia.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)  # łączy okno z plikiem .desktop (ikona w KDE)
    app.setStyle("Fusion")  # jednolity wygląd niezależnie od motywu systemu
    app.setWindowIcon(QIcon(str(resource_path("icon.svg"))))

    data_dir = DataDir(default_data_root())
    data_dir.ensure()
    library = Library(data_dir)
    install_if_first_run(library, resource_path("sample_media"))
    library.remove_unused_media()

    window = MainWindow(library)
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
