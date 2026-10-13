"""Główne okno programu: przełącza między menu a poszczególnymi ekranami."""

from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from fa_milia.config import APP_NAME
from fa_milia.core.library import Library
from fa_milia.ui.editors.category_editor import CategoryEditorPage
from fa_milia.ui.editors.editor_page import LibraryEditorPage
from fa_milia.ui.editors.final_editor import FinalEditorPage
from fa_milia.ui.menu_screen import MenuScreen

# Pozycje menu, które powstaną w kolejnych etapach: klucz → etap.
NOT_READY_YET = {
    "new_game": "E2",
    "continue": "E5",
    "sets": "E5",
    "transfer": "E5",
    "settings": "E3",
}


def _polish_plural(count: int, one: str, few: str, many: str) -> str:
    """Polska odmiana liczebników: 1 kategoria, 2 kategorie, 5 kategorii."""
    if count == 1:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


class MainWindow(QMainWindow):
    def __init__(self, library: Library) -> None:
        super().__init__()
        self._library = library
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        # QStackedWidget pokazuje jeden „ekran” naraz – jak talia kart.
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._menu = MenuScreen()
        self._category_page = CategoryEditorPage(library)
        self._final_page = FinalEditorPage(library)
        for page in (self._menu, self._category_page, self._final_page):
            self._stack.addWidget(page)

        self._menu.action_requested.connect(self._on_menu_action)
        self._category_page.back_requested.connect(self.show_menu)
        self._final_page.back_requested.connect(self.show_menu)

        for key, stage in NOT_READY_YET.items():
            self._menu.set_action_enabled(key, False, f"Dostępne od etapu {stage}")

        self._setup_shortcuts()
        self.show_menu()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=self._on_escape)

    # --- Nawigacja ---------------------------------------------------------

    def show_menu(self) -> None:
        self._menu.set_info(self._library_summary())
        self._stack.setCurrentWidget(self._menu)
        self._menu.focus_first_enabled()

    def _on_menu_action(self, key: str) -> None:
        # match/case (Python 3.10+) – czytelniejsza wersja długiego if/elif.
        match key:
            case "categories":
                self._open_page(self._category_page)
            case "finals":
                self._open_page(self._final_page)
            case "quit":
                self.close()

    def _open_page(self, page: LibraryEditorPage) -> None:
        page.reload()
        self._stack.setCurrentWidget(page)

    def _on_escape(self) -> None:
        current = self._stack.currentWidget()
        if isinstance(current, LibraryEditorPage):
            current.request_back()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _library_summary(self) -> str:
        categories = len(self._library.categories)
        complete = len(self._library.complete_categories())
        finals = len(self._library.complete_finals())
        category_word = _polish_plural(categories, "kategoria", "kategorie", "kategorii")
        complete_word = _polish_plural(complete, "kompletna", "kompletne", "kompletnych")
        final_word = _polish_plural(finals, "pytanie finałowe", "pytania finałowe",
                                    "pytań finałowych")
        return (f"W bibliotece: {categories} {category_word} ({complete} {complete_word}), "
                f"{finals} {final_word}")

    # --- Zamykanie ---------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Qt wywołuje tę metodę przy próbie zamknięcia okna."""
        current = self._stack.currentWidget()
        if isinstance(current, LibraryEditorPage) and not current.maybe_leave():
            event.ignore()  # użytkownik anulował – okno zostaje otwarte
            return
        event.accept()
