"""Plansza: 6 kolumn kategorii i 5 rzędów pól z wartościami.

Na początku rundy:
- pola pojawiają się losowo, w małych grupach (play_fill_animation),
- nazwy kategorii są zasłonięte napisem „Fa milia” i prowadzący odsłania
  je kolejno od lewej – każda odsłania się z efektem „odwrócenia” tabliczki.
"""

import random

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from fa_milia.config import APP_NAME, ROW_COUNT
from fa_milia.core.game_state import RoundState
from fa_milia.ui.game.widgets import draw_fitted_text, format_points
from fa_milia.ui.style import BOARD_BLUE, GOLD, NAVY

HEADER_BLUE = QColor("#132e86")
TILE_BLUE = QColor(BOARD_BLUE)
TILE_HOVER = QColor("#2f58db")
TILE_USED = QColor("#0f2263")
HEADER_WEIGHT = 1.35  # wiersz z nazwami kategorii jest nieco wyższy od pól

TILE_FADE_MS = 180  # czas pojawiania się jednego pola
FLIP_MS = 450  # czas „odwrócenia” tabliczki z nazwą kategorii
FRAME_MS = 16  # ok. 60 klatek na sekundę


class BoardWidget(QWidget):
    """Plansza rysowana ręcznie (paintEvent) – dzięki temu skaluje się do każdego ekranu."""

    tile_clicked = Signal(int, int)  # (kolumna, rząd)
    advance_requested = Signal()  # kliknięcie w planszę podczas odsłaniania kategorii

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._round: RoundState | None = None
        self._round_number: int | None = None
        self._hover: tuple[int, int] | None = None
        self._clickable = True
        self._scale = 1.0  # skalowanie tekstu z ustawień
        # Tylko na planszy w panelu prowadzącego: obwiedzione pole (otwarte pytanie)
        # i pola oznaczone literą „P” (premia).
        self._highlight: tuple[int, int] | None = None
        self._marked: set[tuple[int, int]] = set()

        # Animacja pojawiania się pól: pole → moment pojawienia się (ms od startu).
        self._appear_at: dict[tuple[int, int], int] = {}
        self._fill_clock = QElapsedTimer()
        self._fill_timer = QTimer(self)
        self._fill_timer.setInterval(FRAME_MS)
        self._fill_timer.timeout.connect(self._on_fill_frame)
        self._fill_end_ms = 0

        # Animacja odwracania tabliczek: kolumna → postęp 0.0–1.0.
        self._shown_revealed = 0  # ile kategorii jest już narysowanych jako odsłonięte
        self._flips: dict[int, QVariantAnimation] = {}

        self.setMouseTracking(True)  # zdarzenia ruchu myszy także bez wciśniętego przycisku
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # --- Dane ----------------------------------------------------------------

    def set_round(self, round_state: RoundState, clickable: bool = True) -> None:
        new_round = round_state.number != self._round_number
        self._round = round_state
        self._round_number = round_state.number
        self._clickable = clickable

        revealed = round_state.revealed_categories
        if new_round or revealed < self._shown_revealed:
            # Nowa runda albo cofnięcie – bez animacji.
            self._stop_flips()
        else:
            # Każda nowo odsłonięta kategoria „odwraca się”.
            for column in range(self._shown_revealed, revealed):
                self._start_flip(column)
        self._shown_revealed = revealed
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.update()

    def set_highlight(self, tile: tuple[int, int] | None) -> None:
        """Obwódka wokół pola (np. aktualnie otwartego pytania)."""
        if tile != self._highlight:
            self._highlight = tile
            self.update()

    def set_marked(self, tiles: set[tuple[int, int]]) -> None:
        """Pola oznaczone literą „P” – położenie premii widoczne dla prowadzącego."""
        if tiles != self._marked:
            self._marked = set(tiles)
            self.update()

    def _intro_running(self) -> bool:
        """Czy trwa początek rundy (kategorie jeszcze zasłonięte albo pola się pojawiają)."""
        if self._round is None:
            return False
        return not self._round.all_categories_revealed() or self._fill_timer.isActive()

    # --- Animacja pojawiania się pól --------------------------------------------

    def play_fill_animation(self, duration_ms: int = 2500) -> None:
        """Pola pojawiają się losowo w małych grupach (2–4 pola) w podanym czasie."""
        if self._round is None:
            return
        tiles = [(c, r) for c in range(len(self._round.categories))
                 for r in range(1, ROW_COUNT + 1)]
        random.shuffle(tiles)
        groups = []
        while tiles:
            size = random.randint(2, 4)
            groups.append(tiles[:size])
            tiles = tiles[size:]
        last_start = max(0, duration_ms - TILE_FADE_MS)
        self._appear_at = {}
        for index, group in enumerate(groups):
            base = last_start * index / max(1, len(groups) - 1)
            for tile in group:
                jitter = random.randint(-40, 40)  # pola w grupie nie są idealnie równe
                self._appear_at[tile] = int(min(last_start, max(0, base + jitter)))
        self._fill_end_ms = duration_ms
        self._fill_clock.start()
        self._fill_timer.start()
        self.update()

    def _on_fill_frame(self) -> None:
        if self._fill_clock.elapsed() >= self._fill_end_ms:
            self._fill_timer.stop()
            self._appear_at = {}
        self.update()

    def _tile_opacity(self, tile: tuple[int, int]) -> float:
        if not self._fill_timer.isActive():
            return 1.0
        start = self._appear_at.get(tile, 0)
        progress = (self._fill_clock.elapsed() - start) / TILE_FADE_MS
        return max(0.0, min(1.0, progress))

    # --- Animacja odwracania tabliczek ------------------------------------------

    def _start_flip(self, column: int) -> None:
        animation = QVariantAnimation(self)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setDuration(FLIP_MS)
        animation.valueChanged.connect(self.update)
        animation.finished.connect(lambda: self._flips.pop(column, None))
        self._flips[column] = animation
        animation.start()

    def _stop_flips(self) -> None:
        for animation in self._flips.values():
            animation.stop()
        self._flips = {}

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
            self._paint_header(painter, column, rect, radius)

        for (column, row), rect in tiles.items():
            if self._round.is_used(column, row):
                painter.setBrush(TILE_USED)
                painter.drawRoundedRect(rect, radius, radius)
                continue
            if (column, row) == self._highlight:
                # Złota obwódka wokół otwartego pola (rysowana pod polem, więc wystaje).
                margin = max(2.0, rect.height() * 0.06)
                painter.setBrush(QColor(GOLD))
                painter.drawRoundedRect(rect.adjusted(-margin, -margin, margin, margin),
                                        radius + margin, radius + margin)
            painter.setOpacity(self._tile_opacity((column, row)))
            hovered = self._clickable and not self._intro_running() and self._hover == (column, row)
            painter.setBrush(TILE_HOVER if hovered else TILE_BLUE)
            painter.drawRoundedRect(rect, radius, radius)
            padding = rect.height() * 0.12
            draw_fitted_text(painter, rect.adjusted(padding, padding, -padding, -padding),
                             format_points(self._round.value(row)), QColor(GOLD),
                             int(rect.height() * 0.62 * self._scale), shadow=True)
            if (column, row) in self._marked:
                self._paint_marker(painter, rect)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setOpacity(1.0)

    @staticmethod
    def _paint_marker(painter: QPainter, rect: QRectF) -> None:
        """Mała złota litera „P” w rogu pola z premią."""
        size = rect.height() * 0.38
        corner = QRectF(rect.left() + size * 0.15, rect.top() + size * 0.15, size, size)
        painter.setBrush(QColor(GOLD))
        painter.setPen(QPen(QColor(NAVY), max(1.0, size * 0.06)))
        painter.drawEllipse(corner)
        draw_fitted_text(painter, corner, "P", QColor(NAVY), int(size * 0.8))
        painter.setPen(Qt.PenStyle.NoPen)

    def _paint_header(self, painter: QPainter, column: int, rect: QRectF, radius: float) -> None:
        """Tabliczka z nazwą kategorii – zasłonięta („Fa milia”) albo odsłonięta.

        Podczas odwracania tabliczka „składa się” w pionie do zera z napisem
        „Fa milia” (pierwsza połowa animacji) i rozkłada już z nazwą (druga połowa).
        """
        revealed = column < self._shown_revealed
        flip = self._flips.get(column)
        squeeze = 1.0
        if flip is not None:
            progress = float(flip.currentValue() or 0.0)
            if progress < 0.5:
                revealed = False
                squeeze = 1.0 - progress * 2
            else:
                squeeze = (progress - 0.5) * 2
        drawn = QRectF(rect)
        drawn.setHeight(rect.height() * max(0.02, squeeze))
        drawn.moveCenter(rect.center())

        painter.setBrush(HEADER_BLUE)
        painter.drawRoundedRect(drawn, radius, radius)
        if squeeze < 0.3:
            return  # tabliczka prawie płaska – napis byłby tylko nieczytelną kreską
        padding = rect.width() * 0.06
        inner = drawn.adjusted(padding, padding * squeeze, -padding, -padding * squeeze)
        if revealed:
            name = self._round.categories[column].display_name.upper()
            draw_fitted_text(painter, inner, name, QColor("white"),
                             int(rect.height() * 0.32 * self._scale * squeeze))
        else:
            draw_fitted_text(painter, inner, APP_NAME, QColor(GOLD),
                             int(rect.height() * 0.30 * self._scale * squeeze), shadow=True)
        painter.setPen(Qt.PenStyle.NoPen)

    # --- Mysz --------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:
        tile = self._tile_at(event.position()) if self._round else None
        if tile != self._hover:
            self._hover = tile
            usable = (tile is not None and self._clickable and not self._intro_running()
                      and not self._round.is_used(*tile))
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
        if not self._round.all_categories_revealed():
            self.advance_requested.emit()  # kliknięcie = odsłoń następną kategorię
            return
        if self._fill_timer.isActive():
            return  # pola jeszcze się pojawiają
        tile = self._tile_at(event.position())
        if tile is not None and not self._round.is_used(*tile):
            self.tile_clicked.emit(*tile)
