"""Ekran gry – to, co widzą zawodnicy (później: telewizor/rzutnik).

Ten ekran NIGDY nie pokazuje odpowiedzi przed jej odsłonięciem.
Wszystkie informacje tylko dla prowadzącego trafiają do HostControls.
"""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.game_state import GameState, Phase
from fa_milia.core.models import ContentKind, Question
from fa_milia.ui.game.board_widget import BoardWidget
from fa_milia.ui.game.widgets import FitTextLabel, ScaledImage, format_points
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


class QuestionView(ClickableView):
    """Pytanie (tekst, obraz lub dźwięk), opcjonalny podpis i – po odsłonięciu – odpowiedź."""

    replay_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._header = FitTextLabel("#9fb4f0", max_ratio=0.6)

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
        layout.addWidget(self._header, stretch=1)
        layout.addWidget(self._content, stretch=8)
        layout.addWidget(self._caption, stretch=2)
        layout.addWidget(self._answer, stretch=3)

    def show_question(self, category: str, value: int, question: Question,
                      media_path: Path | None, revealed: bool) -> None:
        self._header.set_text(f"{category.upper()}  ·  {format_points(value)}")
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


class ScoresView(ClickableView):
    """Tabela wyników: tytuł, lista (miejsce, imię, punkty) i podpowiedź na dole."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
            self._rows.addWidget(place_label, line, 0)
            self._rows.addWidget(name_label, line, 1)
            self._rows.addWidget(score_label, line, 2)
        # Przy małej liczbie graczy wiersze nie powinny być gigantyczne:
        # dokładamy puste miejsce do co najmniej 6 wierszy.
        for line in range(len(ranking), 6):
            self._rows.setRowStretch(line, 1)
        for line in range(len(ranking)):
            self._rows.setRowStretch(line, 1)


def _ranking_rows(state: GameState) -> list[tuple[int, str, int]]:
    return [(place, player.name, player.score) for place, player in state.ranking()]


def winner_title(state: GameState) -> str:
    winners = [player.name for place, player in state.ranking() if place == 1]
    if len(winners) == 1:
        return f"Zwycięża {winners[0]}!"
    return "Remis: " + ", ".join(winners[:-1]) + " i " + winners[-1] + "!"


class GameScreen(QWidget):
    """Przełącza widoki (plansza / pytanie / wyniki) zależnie od stanu gry."""

    tile_clicked = Signal(int, int)
    advance_requested = Signal()  # kliknięcie w pytanie lub tabelę wyników
    replay_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GameScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(SCREEN_STYLE)

        self._board = BoardWidget()
        self._question = QuestionView()
        self._scores = ScoresView()
        self._stack = QStackedWidget()
        for view in (self._board, self._question, self._scores):
            self._stack.addWidget(view)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._board.tile_clicked.connect(self.tile_clicked)
        self._question.clicked.connect(self.advance_requested)
        self._question.replay_requested.connect(self.replay_requested)
        self._scores.clicked.connect(self.advance_requested)

    def show_state(self, state: GameState, media_path: Callable[[str], Path]) -> None:
        """Pokazuje widok odpowiadający fazie gry.

        media_path to funkcja zamieniająca nazwę pliku mediów na pełną ścieżkę.
        """
        match state.phase:
            case Phase.BOARD:
                self._board.set_round(state.round)
                self._stack.setCurrentWidget(self._board)
            case Phase.QUESTION:
                question = state.current_question()
                path = media_path(question.media) if question.media else None
                self._question.show_question(state.current_category().name, state.current.value,
                                             question, path, state.current.revealed)
                self._stack.setCurrentWidget(self._question)
            case Phase.ROUND_END:
                if state.is_last_round():
                    hint = "Kliknij lub naciśnij spację, aby zobaczyć wyniki końcowe"
                else:
                    hint = f"Kliknij lub naciśnij spację, aby rozpocząć rundę {state.round.number + 1}"
                self._scores.show_scores(f"Koniec rundy {state.round.number}",
                                         _ranking_rows(state), hint)
                self._stack.setCurrentWidget(self._scores)
            case Phase.FINISHED:
                self._scores.show_scores(winner_title(state), _ranking_rows(state),
                                         "Dziękujemy za grę!", highlight_winners=True)
                self._stack.setCurrentWidget(self._scores)
