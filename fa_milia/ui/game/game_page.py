"""Strona rozgrywki (tryb jednoekranowy): ekran gry + pasek prowadzącego."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from fa_milia.core.game_state import GameState, Phase
from fa_milia.core.library import Library
from fa_milia.core.models import ContentKind
from fa_milia.ui.audio import AudioPlayer
from fa_milia.ui.game.controller import GameController
from fa_milia.ui.game.game_screen import GameScreen
from fa_milia.ui.game.host_controls import HostControls


class GamePage(QWidget):
    back_to_menu = Signal()

    def __init__(self, library: Library, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._controller = GameController(self)
        self._audio = AudioPlayer(self)
        # Klucz (runda, kolumna, rząd) ostatnio pokazanego pytania – żeby dźwięk
        # pytania zagrał raz przy otwarciu, a nie przy każdym odświeżeniu.
        self._shown_question_key: tuple[int, int, int] | None = None

        self._screen = GameScreen()
        self._host = HostControls(self._controller)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._screen, stretch=1)
        layout.addWidget(self._host)

        self._screen.tile_clicked.connect(self._controller.open_tile)
        self._screen.advance_requested.connect(self._controller.advance)
        self._screen.replay_requested.connect(self._play_question_sound)
        self._host.menu_requested.connect(self.request_back)
        self._controller.state_changed.connect(self._refresh)

        # Skróty działają, gdy fokus jest na tej stronie lub jej elementach.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        context = Qt.ShortcutContext.WidgetWithChildrenShortcut
        QShortcut(QKeySequence("Space"), self, self._controller.advance, context=context)
        QShortcut(QKeySequence.StandardKey.Undo, self, self._controller.undo, context=context)

    def start(self, state: GameState) -> None:
        self._shown_question_key = None
        self._controller.start(state)
        self.setFocus()

    def is_game_running(self) -> bool:
        state = self._controller.state
        return state is not None and state.phase != Phase.FINISHED

    # --- Odświeżanie -------------------------------------------------------

    def _refresh(self) -> None:
        state = self._controller.state
        self._screen.show_state(state, self._library.media_path)

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
            self.back_to_menu.emit()
            return
        if state.phase == Phase.QUESTION:
            if not state.current.revealed and not state.current.marks:
                self._controller.cancel_question()  # pomyłkowe kliknięcie – pole zostaje
            else:
                self._controller.close_question()
            return
        if state.phase == Phase.FINISHED or self.confirm_quit():
            self._audio.stop()
            self.back_to_menu.emit()

    def confirm_quit(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Przerwać grę?",
            "Gra jest w toku. Czy na pewno ją przerwać?\n"
            "(Zapisywanie i wznawianie gry pojawi się w etapie E5.)",
        )
        return answer == QMessageBox.StandardButton.Yes
