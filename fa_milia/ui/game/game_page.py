"""Strona rozgrywki: łączy kontroler, ekran gry i panel prowadzącego.

Dwa tryby:
- dwa ekrany: ekran gry w osobnym oknie (GameWindow) na telewizorze,
  a panel prowadzącego wypełnia główne okno na laptopie;
- jeden ekran: ekran gry wypełnia główne okno, a panel prowadzącego jest
  nakładką na dole (F2 pokazuje/ukrywa), z zasłoniętą odpowiedzią.
"""

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QScreen, QShortcut
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from fa_milia.core.game_state import GameState, Phase
from fa_milia.core.library import Library
from fa_milia.core.models import ContentKind
from fa_milia.core.settings import Settings
from fa_milia.ui.audio import AudioPlayer
from fa_milia.ui.game.controller import GameController
from fa_milia.ui.game.game_screen import GameScreen
from fa_milia.ui.game.game_window import GameWindow
from fa_milia.ui.game.host_panel import HostPanel
from fa_milia.ui.screens import choose_game_screen

OVERLAY_MAX_HEIGHT = 0.65  # nakładka zajmuje najwyżej 65% wysokości ekranu


class GamePage(QWidget):
    back_to_menu = Signal()

    def __init__(self, library: Library, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._settings = settings
        self._controller = GameController(self)
        self._audio = AudioPlayer(self)
        self._game_window = GameWindow()
        self._game_screen_monitor: QScreen | None = None  # None = tryb jednoekranowy
        # Klucz (runda, kolumna, rząd) ostatnio pokazanego pytania – żeby dźwięk
        # pytania zagrał raz przy otwarciu, a nie przy każdym odświeżeniu.
        self._shown_question_key: tuple[int, int, int] | None = None

        self._screen = GameScreen()
        self._host = HostPanel(self._controller)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._screen.tile_clicked.connect(self._controller.open_tile)
        self._screen.advance_requested.connect(self._controller.advance)
        self._screen.replay_requested.connect(self._play_question_sound)
        self._host.menu_requested.connect(self.request_back)
        self._host.hide_requested.connect(self.toggle_overlay)
        self._controller.state_changed.connect(self._refresh)
        QGuiApplication.instance().screenRemoved.connect(self._on_screen_removed)

        # Skróty: na tej stronie (okno prowadzącego) i w oknie ekranu gry.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        page_context = Qt.ShortcutContext.WidgetWithChildrenShortcut
        self._add_shortcuts(self, page_context)
        self._add_shortcuts(self._game_window, Qt.ShortcutContext.WindowShortcut)
        QShortcut(QKeySequence("F2"), self, self.toggle_overlay, context=page_context)
        QShortcut(QKeySequence("Escape"), self._game_window, self.request_back,
                  context=Qt.ShortcutContext.WindowShortcut)
        QShortcut(QKeySequence("F11"), self._game_window, self._game_window.toggle_fullscreen,
                  context=Qt.ShortcutContext.WindowShortcut)

        self.apply_settings(settings)

    def _add_shortcuts(self, owner: QObject, context: Qt.ShortcutContext) -> None:
        QShortcut(QKeySequence("Space"), owner, self._controller.advance, context=context)
        QShortcut(QKeySequence.StandardKey.Undo, owner, self._controller.undo, context=context)

    # --- Start i koniec gry ------------------------------------------------

    def apply_settings(self, settings: Settings) -> None:
        self._settings = settings
        self._screen.set_text_scale(settings.game_scale / 100)
        self._host.set_scale(settings.host_scale / 100)
        self._audio.set_volume(settings.volume / 100)
        self._position_overlay()

    def start(self, state: GameState) -> None:
        self._shown_question_key = None
        host_monitor = self.window().screen()
        choice = choose_game_screen(self._settings, host_monitor)
        self._set_mode(choice.screen)
        self._controller.start(state)
        if choice.message:
            self._host.show_message(choice.message)
        elif choice.screen is None:
            self._host.show_message("Tryb jednoekranowy: F2 pokazuje i ukrywa ten panel.")
        self.setFocus()

    def is_game_running(self) -> bool:
        state = self._controller.state
        return state is not None and state.phase != Phase.FINISHED

    def _leave_game(self) -> None:
        self._audio.stop()
        self._game_window.release()
        self.back_to_menu.emit()

    # --- Tryb jedno- i dwuekranowy ----------------------------------------

    def _set_mode(self, game_monitor: QScreen | None) -> None:
        self._game_screen_monitor = game_monitor
        # Najpierw zdejmujemy oba widżety z układu strony…
        self._layout.removeWidget(self._screen)
        self._layout.removeWidget(self._host)

        if game_monitor is not None:
            # …dwa ekrany: ekran gry do osobnego okna, panel na całą stronę.
            self._game_window.attach(self._screen)
            self._game_window.show_on(game_monitor, self._settings.fullscreen)
            self._host.set_overlay(False)
            self._layout.addWidget(self._host)
            self._host.show()
            # Okno gry pojawia się na wierzchu – przywracamy aktywność oknu prowadzącego.
            self.window().activateWindow()
        else:
            # …jeden ekran: ekran gry na stronie, panel jako nakładka nad nim.
            self._game_window.release()
            self._layout.addWidget(self._screen)
            self._screen.show()
            self._host.setParent(self)
            self._host.set_overlay(True)
            self._host.show()
            self._host.raise_()  # na wierzch, nad ekranem gry
            self._position_overlay()

    def _is_single_screen(self) -> bool:
        return self._game_screen_monitor is None

    def toggle_overlay(self) -> None:
        """F2: pokazuje lub ukrywa panel prowadzącego (tylko w trybie jednoekranowym)."""
        if not self._is_single_screen():
            return
        self._host.setVisible(not self._host.isVisible())
        if self._host.isVisible():
            self._host.raise_()
            self._position_overlay()
        self.setFocus()

    def _position_overlay(self) -> None:
        if not self._is_single_screen():
            return
        # activate() przelicza układ od razu – bez tego sizeHint bywa nieaktualny
        # tuż po dodaniu nowych wierszy zawodników.
        self._host.layout().activate()
        height = min(self._host.sizeHint().height(), int(self.height() * OVERLAY_MAX_HEIGHT))
        self._host.setGeometry(0, self.height() - height, self.width(), height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_overlay()

    def _on_screen_removed(self, screen: QScreen) -> None:
        """Odłączono monitor z ekranem gry – przechodzimy na jeden ekran."""
        if screen is self._game_screen_monitor:
            self._set_mode(None)
            self._refresh()
            self._host.show_message("Odłączono monitor z ekranem gry – tryb jednoekranowy "
                                    "(F2 pokazuje i ukrywa panel).")

    # --- Odświeżanie -------------------------------------------------------

    def _refresh(self) -> None:
        state = self._controller.state
        self._screen.show_state(state, self._library.media_path, self._controller.show_scores)
        # Liczba widocznych przycisków się zmienia, więc i wysokość panelu.
        # singleShot(0, …) – wykonaj, gdy Qt skończy bieżące przeliczanie układu.
        QTimer.singleShot(0, self._position_overlay)

        if state.phase == Phase.QUESTION:
            key = (state.round_index, state.current.column, state.current.row)
            if key != self._shown_question_key:
                self._shown_question_key = key
                if state.current_question().kind == ContentKind.SOUND:
                    self._play_question_sound()
        else:
            self._shown_question_key = None
            self._audio.stop()

    def _play_question_sound(self) -> None:
        question = self._controller.state.current_question()
        if question and question.media:
            self._audio.play(self._library.media_path(question.media))

    # --- Esc ---------------------------------------------------------------

    def request_back(self) -> None:
        """Esc: wyjście z pytania albo (z potwierdzeniem) powrót do menu."""
        state = self._controller.state
        if state is None:
            self._leave_game()
            return
        if self._controller.show_scores:
            self._controller.toggle_scores()
            return
        if state.phase == Phase.QUESTION:
            if not state.current.revealed and not state.current.marks:
                self._controller.cancel_question()  # pomyłkowe kliknięcie – pole zostaje
            else:
                self._controller.close_question()
            return
        if state.phase == Phase.FINISHED or self.confirm_quit():
            self._leave_game()

    def confirm_quit(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Przerwać grę?",
            "Gra jest w toku. Czy na pewno ją przerwać?\n"
            "(Zapisywanie i wznawianie gry pojawi się w etapie E5.)",
        )
        return answer == QMessageBox.StandardButton.Yes

    def shutdown(self) -> None:
        """Wywoływane przy zamykaniu programu – chowa okno ekranu gry."""
        self._audio.stop()
        self._game_window.release()
