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
from fa_milia.core.history import GameHistory
from fa_milia.core.library import Library
from fa_milia.core.savegame import delete_game, save_game
from fa_milia.core.models import ContentKind
from fa_milia.core.settings import Settings
from fa_milia.core.usage import UsageMemory
from fa_milia.ui.audio import AudioPlayer
from fa_milia.ui.game.controller import GameController
from fa_milia.ui.game.game_screen import GameScreen
from fa_milia.ui.game.game_window import GameWindow
from fa_milia.ui.game.host_panel import HostPanel
from fa_milia.ui.game.timer import GameTimer
from fa_milia.ui.screens import choose_game_screen
from fa_milia.ui.sound_effects import SoundEffects

OVERLAY_MAX_HEIGHT = 0.65  # nakładka zajmuje najwyżej 65% wysokości ekranu
BOARD_FILL_MS = 2500  # czas pojawiania się pól na początku rundy


class GamePage(QWidget):
    back_to_menu = Signal()

    def __init__(self, library: Library, settings: Settings, usage: UsageMemory,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._usage = usage
        self._save_path = library.data_dir.savegame_file
        self._settings = settings
        self._controller = GameController(self)
        self._audio = AudioPlayer(self)  # dźwięk w pytaniu dźwiękowym
        self._effects = SoundEffects(library.data_dir.sounds, self)  # premia, muzyka, …
        self._timer = GameTimer(self)
        self._game_window = GameWindow()
        self._game_screen_monitor: QScreen | None = None  # None = tryb jednoekranowy
        # Klucz ostatnio pokazanego pytania – żeby dźwięk pytania i timer
        # ruszyły raz przy otwarciu, a nie przy każdym odświeżeniu.
        self._shown_question_key: tuple | None = None
        # Rundy (indeksy), dla których już pokazaliśmy pojawianie się planszy.
        self._filled_rounds: set[int] = set()
        # Pytanie czekające na koniec animacji otwierania pola.
        self._pending_question_key: tuple | None = None

        self._screen = GameScreen()
        self._host = HostPanel(self._controller, self._timer)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._screen.tile_clicked.connect(self._controller.open_tile)
        self._screen.advance_requested.connect(self._controller.advance)
        self._screen.replay_requested.connect(self._play_question_sound)
        self._screen.transition_finished.connect(self._on_transition_finished)
        self._host.menu_requested.connect(self.request_back)
        self._host.hide_requested.connect(self.toggle_overlay)
        self._controller.state_changed.connect(self._refresh)
        self._controller.sound.connect(self._effects.play)
        self._controller.answer_marked.connect(self._on_answer_marked)
        self._timer.tick.connect(self._update_timer_display)
        self._timer.expired.connect(self._on_timer_expired)
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
        QShortcut(QKeySequence("P"), owner, self._toggle_timer_pause, context=context)

    def _toggle_timer_pause(self) -> None:
        """Klawisz P: pauza / wznowienie timera."""
        if not self._timer.active:
            self._host.show_message("Timer nie odlicza – nie ma czego wstrzymać.")
            return
        self._timer.toggle_pause()
        self._host.show_message("Timer wstrzymany (P – wznów)." if not self._timer.running
                                else "Timer wznowiony.")

    # --- Start i koniec gry ------------------------------------------------

    def apply_settings(self, settings: Settings) -> None:
        self._settings = settings
        self._screen.set_text_scale(settings.game_scale / 100)
        self._host.set_scale(settings.host_scale / 100)
        self._audio.set_volume(settings.volume / 100)
        self._effects.set_volume(settings.volume / 100)
        self._position_overlay()

    def start(self, state: GameState) -> None:
        """Nowa gra."""
        self._prepare_screens()
        self._controller.start(state)
        self.setFocus()

    def resume(self, history: GameHistory) -> None:
        """Wznowienie zapisanej gry."""
        self._prepare_screens()
        self._controller.resume(history)
        self._host.show_message("Wznowiono zapisaną grę.")
        self.setFocus()

    def _prepare_screens(self) -> None:
        self._shown_question_key = None
        self._filled_rounds = set()
        host_monitor = self.window().screen()
        choice = choose_game_screen(self._settings, host_monitor)
        self._set_mode(choice.screen)
        if choice.message:
            self._host.show_message(choice.message)
        elif choice.screen is None:
            self._host.show_message("Tryb jednoekranowy: F2 pokazuje i ukrywa ten panel.")

    def is_game_running(self) -> bool:
        state = self._controller.state
        return state is not None and state.phase != Phase.FINISHED

    def _leave_game(self) -> None:
        self._audio.stop()
        self._effects.stop_all()
        self._timer.stop()
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
        self._autosave(state)
        self._screen.show_state(state, self._library.media_path, self._controller.show_scores)
        # Liczba widocznych przycisków się zmienia, więc i wysokość panelu.
        # singleShot(0, …) – wykonaj, gdy Qt skończy bieżące przeliczanie układu.
        QTimer.singleShot(0, self._position_overlay)
        self._maybe_play_board_fill(state)

        key = self._question_key(state)
        if key is None:
            # Nie ma pytania na ekranie – cisza i bez timera.
            self._shown_question_key = None
            self._audio.stop()
            self._timer.stop()
            self._effects.fade_out("final_countdown")
            return
        if key != self._shown_question_key:
            # Właśnie pokazało się nowe pytanie.
            self._shown_question_key = key
            if state.phase == Phase.FINAL_QUESTION:
                # Pytanie finałowe jest „użyte” od chwili wyświetlenia.
                self._usage.mark_final(state.final.question.id)
            if self._screen.is_transitioning():
                # Pytanie jeszcze „wyrasta” z pola – timer i dźwięk ruszą po animacji.
                self._pending_question_key = key
            else:
                self._begin_question(state)
        if state.is_revealed():
            self._timer.stop()  # po odsłonięciu odpowiedzi timer znika
            self._effects.fade_out("final_countdown")

    def _begin_question(self, state: GameState) -> None:
        """Pytanie jest już w pełni na ekranie: dźwięk pytania, timer, muzyka finału."""
        if state.is_revealed():
            return
        if state.current_question().kind == ContentKind.SOUND:
            self._play_question_sound()
        if state.phase == Phase.FINAL_QUESTION:
            # Finał ma timer zawsze, a w tle gra muzyka finałowa.
            self._timer.start(self._settings.final_seconds)
            self._effects.play("final_countdown")
        elif self._settings.timer_enabled and not state.current.is_bonus:
            # Pytanie z premią jest bez timera – odpowiada jeden zawodnik o własną stawkę.
            self._timer.start(self._settings.question_seconds)

    def _on_transition_finished(self) -> None:
        """Koniec animacji otwierania pola – startujemy odłożone pytanie."""
        key, self._pending_question_key = self._pending_question_key, None
        state = self._controller.state
        if key is not None and state is not None and self._question_key(state) == key:
            self._begin_question(state)

    def _maybe_play_board_fill(self, state: GameState) -> None:
        """Początek rundy: pola pojawiają się w grupach, w tle gra board_fill."""
        if state.phase != Phase.BOARD or state.round.revealed_categories > 0:
            return
        if state.round_index in self._filled_rounds:
            return
        self._filled_rounds.add(state.round_index)
        self._screen.play_board_fill(BOARD_FILL_MS)
        self._effects.play("board_fill")  # gra w całości, do końca pliku

    def _on_timer_expired(self) -> None:
        state = self._controller.state
        if state is not None and state.phase == Phase.FINAL_QUESTION:
            # Finał: bez dźwięku i bez napisu „Czas!” – pasek po prostu znika,
            # a muzyka finałowa gra do końca. Odpowiedź odsłania prowadzący.
            self._timer.stop()
            self._host.show_message("Czas minął – odsłoń odpowiedź, gdy zawodnicy będą gotowi.")
            return
        self._effects.fade_out("final_countdown", 300)
        self._effects.play("time_up")
        # W zwykłym pytaniu (opcjonalnie) od razu pokazujemy odpowiedź.
        # W finale odpowiedź odsłania prowadzący – zawodnicy kończą zapisywać.
        if (state is not None and state.phase == Phase.QUESTION and not state.current.revealed
                and self._settings.reveal_on_timeout):
            self._controller.reveal_answer("Koniec czasu – odsłonięcie odpowiedzi")

    def _on_answer_marked(self, correct: bool) -> None:
        """Zła odpowiedź: wstrzymany timer rusza dalej (odpowiada następna osoba).

        Dobra odpowiedź pokazuje odpowiedź (robi to logika gry), a timer znika.
        """
        if not correct and self._timer.active and not self._timer.running \
                and self._timer.remaining() > 0:
            self._timer.resume()
            self._host.show_message("Zła odpowiedź – timer wznowiony.")

    def _autosave(self, state: GameState) -> None:
        """Zapis po każdej akcji. Zakończona gra nie jest już potrzebna – kasujemy zapis."""
        try:
            if state.phase == Phase.FINISHED:
                delete_game(self._save_path)
            else:
                save_game(self._save_path, self._controller.history)
        except OSError as error:
            self._host.show_message(f"Nie udało się zapisać gry: {error}")

    @staticmethod
    def _question_key(state: GameState) -> tuple | None:
        """Identyfikator wyświetlanego pytania (None, gdy pytania nie ma na ekranie)."""
        if state.phase == Phase.QUESTION:
            return (state.round_index, state.current.column, state.current.row)
        if state.phase == Phase.FINAL_QUESTION:
            return ("final",)
        return None

    def _update_timer_display(self) -> None:
        remaining = self._timer.remaining() if self._timer.active else None
        self._screen.set_timer(remaining, self._timer.total)

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
        if state.phase == Phase.BONUS:
            self._controller.cancel_question()  # pomyłkowe kliknięcie – pole zostaje
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
            "Wyjść z gry?",
            "Gra jest w toku. Wyjść do menu?\n"
            "Gra jest zapisana – dokończysz ją przez „Kontynuuj grę”.",
        )
        return answer == QMessageBox.StandardButton.Yes

    def shutdown(self) -> None:
        """Wywoływane przy zamykaniu programu – chowa okno ekranu gry."""
        self._audio.stop()
        self._effects.stop_all()
        self._timer.stop()
        self._game_window.release()
