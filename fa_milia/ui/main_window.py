"""Główne okno programu: przełącza między menu a poszczególnymi ekranami."""

from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from fa_milia.config import APP_NAME
from fa_milia.core.game_state import GameError, GameState
from fa_milia.core.library import Library
from fa_milia.core.models import Category
from fa_milia.core.selection import choose_final
from fa_milia.core.settings import Settings, save_settings
from fa_milia.ui.editors.category_editor import CategoryEditorPage
from fa_milia.ui.editors.editor_page import LibraryEditorPage
from fa_milia.ui.editors.final_editor import FinalEditorPage
from fa_milia.ui.game.game_page import GamePage
from fa_milia.ui.menu_screen import MenuScreen
from fa_milia.ui.settings_dialog import SettingsDialog
from fa_milia.ui.setup.category_select_page import CategorySelectPage
from fa_milia.ui.setup.players_page import PlayersPage

# Pozycje menu, które powstaną w kolejnych etapach: klucz → etap.
NOT_READY_YET = {
    "continue": "E5",
    "sets": "E5",
    "transfer": "E5",
}


def _polish_plural(count: int, one: str, few: str, many: str) -> str:
    """Polska odmiana liczebników: 1 kategoria, 2 kategorie, 5 kategorii."""
    if count == 1:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


class MainWindow(QMainWindow):
    def __init__(self, library: Library, settings: Settings) -> None:
        super().__init__()
        self._library = library
        self._settings = settings
        self._player_names: list[str] = []
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        # QStackedWidget pokazuje jeden „ekran” naraz – jak talia kart.
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._menu = MenuScreen()
        self._category_page = CategoryEditorPage(library)
        self._final_page = FinalEditorPage(library)
        self._players_page = PlayersPage()
        self._select_page = CategorySelectPage(library)
        self._game_page = GamePage(library, settings)
        for page in (self._menu, self._category_page, self._final_page,
                     self._players_page, self._select_page, self._game_page):
            self._stack.addWidget(page)

        self._menu.action_requested.connect(self._on_menu_action)
        self._category_page.back_requested.connect(self.show_menu)
        self._final_page.back_requested.connect(self.show_menu)
        self._players_page.back_requested.connect(self.show_menu)
        self._players_page.players_chosen.connect(self._on_players_chosen)
        self._select_page.back_requested.connect(self._show_players_page)
        self._select_page.start_requested.connect(self._start_game)
        self._game_page.back_to_menu.connect(self.show_menu)

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
            case "new_game":
                self._show_players_page()
            case "categories":
                self._open_editor(self._category_page)
            case "finals":
                self._open_editor(self._final_page)
            case "settings":
                self._open_settings()
            case "quit":
                self.close()

    def _open_editor(self, page: LibraryEditorPage) -> None:
        page.reload()
        self._stack.setCurrentWidget(page)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self._library.data_dir.sounds, self)
        # exec() pokazuje okno modalne i czeka, aż użytkownik je zamknie.
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return
        self._settings = dialog.result_settings()
        try:
            save_settings(self._library.data_dir.settings_file, self._settings)
        except OSError as error:
            QMessageBox.warning(self, "Ustawienia", f"Nie udało się zapisać ustawień:\n{error}")
        self._game_page.apply_settings(self._settings)

    def _show_players_page(self) -> None:
        self._stack.setCurrentWidget(self._players_page)
        self._players_page.prepare()

    def _on_players_chosen(self, names: list[str]) -> None:
        self._player_names = names
        self._select_page.prepare()
        self._stack.setCurrentWidget(self._select_page)

    def _start_game(self, round1: list[Category], round2: list[Category],
                    with_final: bool) -> None:
        final_question = None
        if with_final:
            finals = {f.id: f for f in self._library.complete_finals()}
            # Pamięć wykorzystania pojawi się w etapie E5 – na razie „użytych” brak.
            final_id, _was_used = choose_final(list(finals), used_ids=set())
            final_question = finals.get(final_id)
        try:
            state = GameState.new(self._player_names, round1, round2, final_question)
        except GameError as error:
            QMessageBox.warning(self, "Nie można rozpocząć gry", str(error))
            return
        self._stack.setCurrentWidget(self._game_page)
        self._game_page.start(state)

    def _on_escape(self) -> None:
        # Każda strona poza menu ma metodę request_back() – „wstecz” dla tej strony.
        # hasattr sprawdza, czy obiekt ma taki atrybut/metodę.
        current = self._stack.currentWidget()
        if hasattr(current, "request_back"):
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
        if current is self._game_page and self._game_page.is_game_running():
            if not self._game_page.confirm_quit():
                event.ignore()
                return
        self._game_page.shutdown()  # chowa okno ekranu gry na drugim monitorze
        event.accept()
