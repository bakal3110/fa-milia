"""Plansza: 6 kolumn kategorii i 5 rzędów pól z wartościami."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from fa_milia.config import ROW_COUNT
from fa_milia.core.game_state import RoundState
from fa_milia.ui.game.widgets import draw_fitted_text, format_points
from fa_milia.ui.style import BOARD_BLUE, GOLD, NAVY

HEADER_BLUE = QColor("#132e86")
TILE_BLUE = QColor(BOARD_BLUE)
TILE_HOVER = QColor("#2f58db")
TILE_USED = QColor("#0f2263")
HEADER_WEIGHT = 1.35  # wiersz z nazwami kategorii jest nieco wyższy od pól


class BoardWidget(QWidget):
    """Plansza rysowana ręcznie (paintEvent) – dzięki temu skaluje się do każdego ekranu."""

    tile_clicked = Signal(int, int)  # (kolumna, rząd)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._round: RoundState | None = None
        self._hover: tuple[int, int] | None = None
        self._clickable = True
        self._scale = 1.0  # skalowanie tekstu z ustawień
        self.setMouseTracking(True)  # zdarzenia ruchu myszy także bez wciśniętego przycisku
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_round(self, round_state: RoundState, clickable: bool = True) -> None:
        self._round = round_state
        self._clickable = clickable
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.update()

    # --- Geometria ---------------------------------------------------------

    def _layout(self) -> tuple[list[QRectF], dict[tuple[int, int], QRectF]]:
        """Oblicza prostokąty nagłówków i pól dla bieżącego rozmiaru widżetu."""
        columns = len(self._round.categories) if self._round else 6
        gap = max(3.0, min(self.width(), self.height()) * 0.008)
        column_width = (self.width() - gap * (columns + 1)) / columns
        unit = (self.height() - gap * (ROW_COUNT + 2)) / (HEADER_WEIGHT + ROW_COUNT)
        header_height = unit * HEADER_WEIGHT

        headers = []
        tiles = {}
        for column in range(columns):
            x = gap + column * (column_width + gap)
            headers.append(QRectF(x, gap, column_width, header_height))
            for row in range(1, ROW_COUNT + 1):
                y = gap * 2 + header_height + (row - 1) * (unit + gap)
                tiles[(column, row)] = QRectF(x, y, column_width, unit)
        return headers, tiles

    def _tile_at(self, point: QPointF) -> tuple[int, int] | None:
        _headers, tiles = self._layout()
        for key, rect in tiles.items():  # .items() daje pary (klucz, wartość)
            if rect.contains(point):
                return key
        return None

    # --- Rysowanie ---------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(NAVY))
        if self._round is None:
            return

        headers, tiles = self._layout()
        painter.setPen(Qt.PenStyle.NoPen)
        radius = max(4.0, headers[0].height() * 0.06)

        for column, rect in enumerate(headers):
            painter.setBrush(HEADER_BLUE)
            painter.drawRoundedRect(rect, radius, radius)
            name = self._round.categories[column].name.upper()
            padding = rect.width() * 0.06
            draw_fitted_text(painter, rect.adjusted(padding, padding, -padding, -padding),
                             name, QColor("white"), int(rect.height() * 0.32 * self._scale))
            painter.setPen(Qt.PenStyle.NoPen)

        for (column, row), rect in tiles.items():
            if self._round.is_used(column, row):
                painter.setBrush(TILE_USED)
                painter.drawRoundedRect(rect, radius, radius)
                continue
            hovered = self._clickable and self._hover == (column, row)
            painter.setBrush(TILE_HOVER if hovered else TILE_BLUE)
            painter.drawRoundedRect(rect, radius, radius)
            padding = rect.height() * 0.12
            draw_fitted_text(painter, rect.adjusted(padding, padding, -padding, -padding),
                             format_points(self._round.value(row)), QColor(GOLD),
                             int(rect.height() * 0.62 * self._scale), shadow=True)
            painter.setPen(Qt.PenStyle.NoPen)

    # --- Mysz --------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:
        tile = self._tile_at(event.position()) if self._round else None
        if tile != self._hover:
            self._hover = tile
            usable = tile is not None and self._clickable and not self._round.is_used(*tile)
            # *tile „rozpakowuje” krotkę (kolumna, rząd) na dwa argumenty.
            self.setCursor(Qt.CursorShape.PointingHandCursor if usable
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._clickable or not self._round:
            return
        tile = self._tile_at(event.position())
        if tile is not None and not self._round.is_used(*tile):
            self.tile_clicked.emit(*tile)
