"""Ekran gry – to, co widzą zawodnicy (telewizor/rzutnik).

Ten ekran NIGDY nie pokazuje odpowiedzi przed jej odsłonięciem ani położenia
bonusów. Wszystkie informacje tylko dla prowadzącego trafiają do HostPanel.
"""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.game_state import GameState, Phase
from fa_milia.core.models import ContentKind, Question
from fa_milia.ui.game.board_widget import BoardWidget
from fa_milia.ui.game.timer import format_seconds
from fa_milia.ui.game.widgets import FitTextLabel, ScaledImage, draw_fitted_text, format_points
from fa_milia.ui.style import GOLD, NAVY

SCREEN_STYLE = f"""
#GameScreen, #GameScreen QStackedWidget, #GameScreen QWidget#View {{
    background: {NAVY};
}}
#GameScreen QPushButton {{
    background: #1d3fb3;
    color: white;
    border: 2px solid {GOLD};
    border-radius: 12px;
    padding: 10px 24px;
    font-size: 20pt;
    font-weight: bold;
}}
"""

TIMER_WARNING_SECONDS = 5  # ostatnie sekundy – pasek robi się czerwony


class ClickableView(QWidget):
    """Widok, który po kliknięciu w dowolnym miejscu wysyła sygnał `clicked`."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("View")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, event) -> None:
        # Etykiety FitTextLabel nie obsługują kliknięć, więc te „przepływają”
        # do rodzica – tutaj. Przyciski (np. „Odtwórz ponownie”) obsługują je same.
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class TimerBar(QWidget):
    """Pasek odliczania: kurczy się z upływem czasu, obok pozostałe sekundy."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._remaining: float | None = None  # None = timer nieaktywny (nic nie rysujemy)
        self._total = 1.0
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_time(self, remaining: float | None, total: float) -> None:
        self._remaining = remaining
        self._total = max(total, 0.1)
        self.update()

    def paintEvent(self, event) -> None:
        if self._remaining is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = self.height()
        text_width = height * 2.6
        bar = QRectF(0, height * 0.3, self.width() - text_width - 10, height * 0.4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#22357a"))
        painter.drawRoundedRect(bar, bar.height() / 2, bar.height() / 2)

        warning = self._remaining <= TIMER_WARNING_SECONDS
        color = QColor("#e5484d") if warning else QColor(GOLD)
        filled = QRectF(bar)
        filled.setWidth(bar.width() * self._remaining / self._total)
        painter.setBrush(color)
        if filled.width() > 0:
            painter.drawRoundedRect(filled, bar.height() / 2, bar.height() / 2)

        text = format_seconds(self._remaining) if self._remaining > 0 else "Czas!"
        text_rect = QRectF(self.width() - text_width, 0, text_width, height)
        draw_fitted_text(painter, text_rect, text, color, int(height * 0.9))


class QuestionView(ClickableView):
    """Pytanie (tekst, obraz lub dźwięk), opcjonalny podpis i – po odsłonięciu – odpowiedź."""

    replay_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._header = FitTextLabel("#9fb4f0", max_ratio=0.6)
        self._timer = TimerBar()

        self._text = FitTextLabel("#ffffff", max_ratio=0.16, shadow=True)
        self._image = ScaledImage()
        self._sound_panel = QWidget()
        sound_layout = QVBoxLayout(self._sound_panel)
        self._sound_icon = FitTextLabel(GOLD, max_ratio=0.9)
        self._sound_icon.set_text("♪")
        self._replay_button = QPushButton("↻ Odtwórz ponownie")
        self._replay_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # spacja nie „kliknie” przycisku
        self._replay_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._replay_button.clicked.connect(self.replay_requested)
        sound_layout.addWidget(self._sound_icon, stretch=1)
        sound_layout.addWidget(self._replay_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._content = QStackedWidget()
        for widget in (self._text, self._image, self._sound_panel):
            self._content.addWidget(widget)

        self._caption = FitTextLabel("#ffffff", max_ratio=0.5)
        self._answer = FitTextLabel(GOLD, max_ratio=0.45, shadow=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 30)
        # stretch = proporcje wysokości poszczególnych części ekranu
        layout.addWidget(self._header, stretch=2)
        layout.addWidget(self._timer, stretch=1)
        layout.addWidget(self._content, stretch=15)
        layout.addWidget(self._caption, stretch=4)
        layout.addWidget(self._answer, stretch=6)

    def show_question(self, header: str, question: Question, media_path: Path | None,
                      revealed: bool) -> None:
        self._header.set_text(header)
        if question.kind == ContentKind.TEXT:
            self._text.set_text(question.text)
            self._content.setCurrentWidget(self._text)
            self._caption.set_text("")
        else:
            if question.kind == ContentKind.IMAGE:
                pixmap = QPixmap(str(media_path)) if media_path else QPixmap()
                self._image.set_pixmap(pixmap)
                self._content.setCurrentWidget(self._image)
            else:
                self._content.setCurrentWidget(self._sound_panel)
            self._caption.set_text(question.text)
        # Odpowiedź pojawia się dopiero po odsłonięciu. Miejsce jest zarezerwowane
        # od początku, więc nic na ekranie nie „skacze”.
        self._answer.set_text(question.answer if revealed else "")

    def set_timer(self, remaining: float | None, total: float) -> None:
        self._timer.set_time(remaining, total)


class SplashView(ClickableView):
    """Duży napis z dwoma liniami pod spodem – ekran BONUS i ekran kategorii finału."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = FitTextLabel(GOLD, max_ratio=0.75, shadow=True)
        self._subtitle = FitTextLabel("#ffffff", max_ratio=0.6, shadow=True)
        self._detail = FitTextLabel("#9fb4f0", max_ratio=0.5)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.addStretch(1)
        layout.addWidget(self._title, stretch=5)
        layout.addWidget(self._subtitle, stretch=2)
        layout.addWidget(self._detail, stretch=2)
        layout.addStretch(1)

    def show_splash(self, title: str, subtitle: str, detail: str) -> None:
        self._title.set_text(title)
        self._subtitle.set_text(subtitle)
        self._detail.set_text(detail)


class ScoresView(ClickableView):
    """Tabela wyników: tytuł, lista (miejsce, imię, punkty) i podpowiedź na dole."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = 1.0
        self._title = FitTextLabel(GOLD, max_ratio=0.7, shadow=True)
        self._rows_widget = QWidget()
        self._rows = QGridLayout(self._rows_widget)
        self._rows.setColumnStretch(0, 1)
        self._rows.setColumnStretch(1, 5)
        self._rows.setColumnStretch(2, 3)
        self._hint = FitTextLabel("#8fa3dc", max_ratio=0.5, bold=False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 30, 80, 30)
        layout.addWidget(self._title, stretch=2)
        layout.addWidget(self._rows_widget, stretch=8)
        layout.addWidget(self._hint, stretch=1)

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self._title.set_scale(scale)
        self._hint.set_scale(scale)

    def show_scores(self, title: str, ranking: list[tuple[int, str, int]], hint: str = "",
                    highlight_winners: bool = False) -> None:
        self._title.set_text(title)
        self._hint.set_text(hint)
        # Usuwamy stare wiersze i budujemy nowe (graczy jest najwyżej 8 – to tanie).
        while self._rows.count():
            self._rows.takeAt(0).widget().deleteLater()
        for line, (place, name, score) in enumerate(ranking):
            color = GOLD if highlight_winners and place == 1 else "#ffffff"
            place_label = FitTextLabel(color, max_ratio=0.6)
            place_label.set_text(f"{place}.")
            name_label = FitTextLabel(color, max_ratio=0.6)
            name_label.set_text(name)
            score_label = FitTextLabel(color, max_ratio=0.6)
            score_label.set_text(format_points(score))
            for label in (place_label, name_label, score_label):
                label.set_scale(self._scale)
            self._rows.addWidget(place_label, line, 0)
            self._rows.addWidget(name_label, line, 1)
            self._rows.addWidget(score_label, line, 2)
        # Przy małej liczbie graczy wiersze nie powinny być gigantyczne:
        # każdy wiersz (także pusty, do co najmniej 6) dostaje tę samą wysokość.
        for line in range(max(6, len(ranking))):
            self._rows.setRowStretch(line, 1)


def _ranking_rows(state: GameState) -> list[tuple[int, str, int]]:
    return [(place, player.name, player.score) for place, player in state.ranking()]


def winner_title(state: GameState) -> str:
    winners = [player.name for place, player in state.ranking() if place == 1]
    if len(winners) == 1:
        return f"Zwycięża {winners[0]}!"
    return "Remis: " + ", ".join(winners[:-1]) + " i " + winners[-1] + "!"


class GameScreen(QWidget):
    """Przełącza widoki (plansza / pytanie / ekrany specjalne / wyniki) zależnie od stanu."""

    tile_clicked = Signal(int, int)
    advance_requested = Signal()  # kliknięcie w pytanie, ekran BONUS lub tabelę wyników
    replay_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GameScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(SCREEN_STYLE)

        self._board = BoardWidget()
        self._question = QuestionView()
        self._splash = SplashView()
        self._scores = ScoresView()
        self._stack = QStackedWidget()
        for view in (self._board, self._question, self._splash, self._scores):
            self._stack.addWidget(view)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._board.tile_clicked.connect(self.tile_clicked)
        self._question.clicked.connect(self.advance_requested)
        self._question.replay_requested.connect(self.replay_requested)
        self._splash.clicked.connect(self.advance_requested)
        self._scores.clicked.connect(self.advance_requested)

    def set_text_scale(self, scale: float) -> None:
        """Skalowanie tekstu z ustawień (1.0 = 100%)."""
        self._board.set_scale(scale)
        self._scores.set_scale(scale)
        # findChildren znajduje wszystkie widżety danego typu wewnątrz widoku.
        for view in (self._question, self._splash):
            for label in view.findChildren(FitTextLabel):
                label.set_scale(scale)

    def set_timer(self, remaining: float | None, total: float) -> None:
        """remaining=None ukrywa pasek timera."""
        self._question.set_timer(remaining, total)

    def show_state(self, state: GameState, media_path: Callable[[str], Path],
                   show_scores: bool = False) -> None:
        """Pokazuje widok odpowiadający fazie gry.

        media_path to funkcja zamieniająca nazwę pliku mediów na pełną ścieżkę.
        show_scores=True: prowadzący poprosił o tabelę wyników (zamiast planszy/pytania).
        """
        if show_scores and state.phase not in (Phase.ROUND_END, Phase.FINISHED):
            self._scores.show_scores("Wyniki", _ranking_rows(state),
                                     "Kliknij lub naciśnij spację, aby wrócić do gry")
            self._stack.setCurrentWidget(self._scores)
            return

        match state.phase:
            case Phase.BOARD:
                self._board.set_round(state.round)
                self._stack.setCurrentWidget(self._board)

            case Phase.BONUS:
                current = state.current
                if current.bonus_player is None:
                    detail = ""
                else:
                    name = state.players[current.bonus_player].name
                    detail = f"{name} gra o {format_points(current.value)}"
                self._splash.show_splash("BONUS", state.current_category().name.upper(), detail)
                self._stack.setCurrentWidget(self._splash)

            case Phase.QUESTION:
                current = state.current
                question = state.current_question()
                category = state.current_category().name.upper()
                if current.is_bonus:
                    player = state.players[current.bonus_player].name
                    header = f"BONUS · {category} · {player} gra o {format_points(current.value)}"
                else:
                    header = f"{category}  ·  {format_points(current.value)}"
                self._show_question(header, question, media_path, current.revealed)

            case Phase.ROUND_END:
                if not state.is_last_round():
                    hint = f"Kliknij lub naciśnij spację, aby rozpocząć rundę {state.round.number + 1}"
                elif state.final is not None:
                    hint = "Kliknij lub naciśnij spację, aby przejść do finału"
                else:
                    hint = "Kliknij lub naciśnij spację, aby zobaczyć wyniki końcowe"
                self._scores.show_scores(f"Koniec rundy {state.round.number}",
                                         _ranking_rows(state), hint)
                self._stack.setCurrentWidget(self._scores)

            case Phase.FINAL_WAGERS:
                self._splash.show_splash("FINAŁ", state.final.question.category.upper(),
                                         "Zawodnicy obstawiają…")
                self._stack.setCurrentWidget(self._splash)

            case Phase.FINAL_QUESTION:
                header = f"FINAŁ  ·  {state.final.question.category.upper()}"
                self._show_question(header, state.current_question(), media_path,
                                    state.final.revealed)

            case Phase.FINISHED:
                hint = "Dziękujemy za grę!"
                if state.final_skipped:
                    hint = "Finał pominięty – nikt nie miał dodatnich punktów. Dziękujemy za grę!"
                self._scores.show_scores(winner_title(state), _ranking_rows(state), hint,
                                         highlight_winners=True)
                self._stack.setCurrentWidget(self._scores)

    def _show_question(self, header: str, question: Question,
                       media_path: Callable[[str], Path], revealed: bool) -> None:
        path = media_path(question.media) if question.media else None
        self._question.show_question(header, question, path, revealed)
        self._stack.setCurrentWidget(self._question)
