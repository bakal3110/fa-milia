"""Generuje przykładowe obrazy (flagi) i dźwięki do fa_milia/resources/sample_media/.

Skrypt uruchamia się raz, przy tworzeniu projektu – wynik jest zapisany w repozytorium.
Uruchomienie (z katalogu projektu):

    QT_QPA_PLATFORM=offscreen .venv/bin/python tools/generate_sample_media.py
"""

import math
import struct
import sys
import wave
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPolygonF

OUTPUT = Path(__file__).resolve().parent.parent / "fa_milia" / "resources" / "sample_media"

# ---------------------------------------------------------------------------
# Flagi
# ---------------------------------------------------------------------------


def _new_image(width: int, height: int) -> tuple[QImage, QPainter]:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(0, 0, 0, 0))  # bez obrysu
    return image, painter


def flag_poland() -> QImage:
    image, p = _new_image(800, 500)
    p.fillRect(0, 250, 800, 250, QColor("#DC143C"))
    p.end()
    return image


def flag_japan() -> QImage:
    image, p = _new_image(900, 600)
    p.setBrush(QColor("#BC002D"))
    radius = 600 * 3 / 10  # średnica koła = 3/5 wysokości
    p.drawEllipse(QPointF(450, 300), radius, radius)
    p.end()
    return image


def flag_france() -> QImage:
    image, p = _new_image(900, 600)
    p.fillRect(0, 0, 300, 600, QColor("#0055A4"))
    p.fillRect(600, 0, 300, 600, QColor("#EF4135"))
    p.end()
    return image


def flag_sweden() -> QImage:
    # Proporcje 16:10, krzyż: pionowe ramię zaczyna się na 5/16 szerokości.
    image, p = _new_image(960, 600)
    p.fillRect(0, 0, 960, 600, QColor("#006AA7"))
    yellow = QColor("#FECC02")
    p.fillRect(300, 0, 120, 600, yellow)
    p.fillRect(0, 240, 960, 120, yellow)
    p.end()
    return image


def flag_czechia() -> QImage:
    image, p = _new_image(900, 600)
    p.fillRect(0, 300, 900, 300, QColor("#D7141A"))
    p.setBrush(QColor("#11457E"))
    p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(450, 300), QPointF(0, 600)]))
    p.end()
    return image


# ---------------------------------------------------------------------------
# Dźwięki (fale sinusoidalne zapisane jako WAV)
# ---------------------------------------------------------------------------

SAMPLE_RATE = 22050

# Częstotliwości nut (Hz) w czwartej oktawie.
NOTES = {
    "C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23,
    "G": 392.00, "A": 440.00, "H": 493.88, "C5": 523.25, "G3": 196.00,
}


def tone(frequency: float, seconds: float, volume: float = 0.5) -> list[float]:
    """Pojedynczy ton z łagodnym narastaniem i wygaszaniem (bez trzasków)."""
    count = int(SAMPLE_RATE * seconds)
    fade = min(int(SAMPLE_RATE * 0.02), count // 2)
    samples = []
    for i in range(count):
        envelope = min(1.0, i / fade, (count - i) / fade) if fade else 1.0
        # Dodajemy słabą wyższą harmoniczną, żeby dźwięk był mniej „sterylny”.
        value = math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)
        value += 0.25 * math.sin(4 * math.pi * frequency * i / SAMPLE_RATE)
        samples.append(volume * envelope * value / 1.25)
    return samples


def silence(seconds: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * seconds)


def beeps(count: int, length: float, gap: float) -> list[float]:
    samples = silence(0.3)
    for _ in range(count):
        samples += tone(880, length) + silence(gap)
    return samples


def melody(notes: list[tuple[str, float]], beat: float = 0.4) -> list[float]:
    """notes: lista (nuta, liczba uderzeń)."""
    samples = silence(0.3)
    for name, beats in notes:
        samples += tone(NOTES[name], beat * beats * 0.92) + silence(beat * beats * 0.08)
    return samples + silence(0.3)


def save_wav(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)  # 16 bitów
        file.setframerate(SAMPLE_RATE)
        data = b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples)
        file.writeframes(data)


SCALE_UP = [(n, 1) for n in ("C", "D", "E", "F", "G", "A", "H")] + [("C5", 2)]

WLAZL_KOTEK = [
    ("G", 1), ("E", 1), ("E", 1), ("F", 1), ("D", 1), ("D", 1), ("C", 0.5), ("E", 0.5), ("G", 2),
    ("G", 1), ("E", 1), ("E", 1), ("F", 1), ("D", 1), ("D", 1), ("C", 0.5), ("E", 0.5), ("C", 2),
]

PANIE_JANIE = [
    ("C", 1), ("D", 1), ("E", 1), ("C", 1),
    ("C", 1), ("D", 1), ("E", 1), ("C", 1),
    ("E", 1), ("F", 1), ("G", 2),
    ("E", 1), ("F", 1), ("G", 2),
    ("G", 0.5), ("A", 0.5), ("G", 0.5), ("F", 0.5), ("E", 1), ("C", 1),
    ("G", 0.5), ("A", 0.5), ("G", 0.5), ("F", 0.5), ("E", 1), ("C", 1),
    ("C", 1), ("G3", 1), ("C", 2),
]


def main() -> None:
    app = QGuiApplication(sys.argv)  # potrzebne do rysowania  # noqa: F841
    OUTPUT.mkdir(parents=True, exist_ok=True)

    flags = {
        "flaga_polska.png": flag_poland,
        "flaga_japonia.png": flag_japan,
        "flaga_francja.png": flag_france,
        "flaga_szwecja.png": flag_sweden,
        "flaga_czechy.png": flag_czechia,
    }
    for name, painter_function in flags.items():
        painter_function().save(str(OUTPUT / name))

    save_wav(OUTPUT / "dzwiek_trzy_sygnaly.wav", beeps(3, 0.3, 0.4))
    save_wav(OUTPUT / "dzwiek_gama.wav", melody(SCALE_UP, beat=0.35))
    save_wav(OUTPUT / "dzwiek_wlazl_kotek.wav", melody(WLAZL_KOTEK, beat=0.38))
    save_wav(OUTPUT / "dzwiek_panie_janie.wav", melody(PANIE_JANIE, beat=0.38))
    save_wav(OUTPUT / "dzwiek_siedem_sygnalow.wav", beeps(7, 0.12, 0.13))
    print(f"Zapisano pliki w {OUTPUT}")


if __name__ == "__main__":
    main()
