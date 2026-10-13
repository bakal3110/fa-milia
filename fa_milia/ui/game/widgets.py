"""Widżety ekranu gry, które same dopasowują się do wielkości ekranu.

Na telewizorze tekst ma być jak największy, ale musi się zmieścić.
Zamiast ustawiać stały rozmiar czcionki, szukamy największego rozmiaru,
przy którym tekst (z zawijaniem wierszy) mieści się w dostępnym prostokącie.
"""

from functools import lru_cache

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

WRAP_CENTER = Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter


def format_points(points: int, signed: bool = False) -> str:
    """1200 → „1 200”, −300 → „−300”; signed=True dodaje „+” przed dodatnimi."""
    #   to spacja nierozdzielająca (liczba nie zostanie przełamana),
    # − to typograficzny znak minus (dłuższy niż łącznik „-”).
    digits = f"{abs(points):,}".replace(",", " ")
    if points < 0:
        return "−" + digits
    if signed and points > 0:
        return "+" + digits
    return digits


@lru_cache(maxsize=2048)
def _best_pixel_size(family: str, bold: bool, text: str, width: int, height: int,
                     max_px: int, min_px: int) -> int:
    """Wyszukiwanie binarne największego rozmiaru czcionki, przy którym tekst się mieści.

    @lru_cache zapamiętuje wyniki dla tych samych argumentów, więc ponowne
    rysowanie tego samego napisu w tym samym miejscu nic nie kosztuje.
    """
    font = QFont(family)
    font.setBold(bold)
    low, high, best = min_px, max(min_px, max_px), min_px
    while low <= high:
        middle = (low + high) // 2
        font.setPixelSize(middle)
        bounds = QFontMetrics(font).boundingRect(QRect(0, 0, width, height), WRAP_CENTER, text)
        if bounds.width() <= width and bounds.height() <= height:
            best = middle
            low = middle + 1  # mieści się – spróbuj większej
        else:
            high = middle - 1  # nie mieści się – spróbuj mniejszej
    return best


def fitted_font(base: QFont, text: str, width: int, height: int,
                max_px: int, min_px: int = 8) -> QFont:
    font = QFont(base)
    size = _best_pixel_size(base.family(), base.bold(), text, max(1, width), max(1, height),
                            int(max_px), min_px)
    font.setPixelSize(size)
    return font


def draw_fitted_text(painter: QPainter, rect: QRectF, text: str, color: QColor,
                     max_px: int, bold: bool = True, shadow: bool = False) -> None:
    """Rysuje tekst wyśrodkowany w prostokącie, w największym mieszczącym się rozmiarze."""
    if not text:
        return
    base = QFont(painter.font())
    base.setBold(bold)
    inner = rect.toRect()
    painter.setFont(fitted_font(base, text, inner.width(), inner.height(), max_px))
    if shadow:
        offset = max(1, inner.height() // 40)
        painter.setPen(QColor(0, 0, 0, 160))
        painter.drawText(inner.translated(offset, offset), WRAP_CENTER, text)
    painter.setPen(color)
    painter.drawText(inner, WRAP_CENTER, text)


class FitTextLabel(QWidget):
    """Etykieta, której tekst automatycznie wypełnia dostępne miejsce.

    max_ratio: maksymalna wysokość liter jako ułamek wysokości widżetu
    (żeby krótkie słowo nie było absurdalnie wielkie).
    """

    def __init__(self, color: str = "#ffffff", max_ratio: float = 0.6, bold: bool = True,
                 shadow: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = ""
        self._color = QColor(color)
        self._max_ratio = max_ratio
        self._bold = bold
        self._shadow = shadow
        self._scale = 1.0  # skalowanie z ustawień (1.0 = 100%)
        # Ignored = układ może dowolnie zmniejszyć widżet (nie wymusza minimalnego rozmiaru).
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.update()  # poproś Qt o ponowne narysowanie

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.update()

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        margin = self.height() * 0.04
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        draw_fitted_text(painter, rect, self._text, self._color,
                         int(self.height() * self._max_ratio * self._scale),
                         self._bold, self._shadow)


class ScaledImage(QWidget):
    """Obraz skalowany do rozmiaru widżetu z zachowaniem proporcji."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = self._pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(QRect(x, y, scaled.width(), scaled.height()), self._pixmap)
