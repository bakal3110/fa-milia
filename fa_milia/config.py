"""Stałe konfiguracyjne gry.

Wszystkie „magiczne liczby” są zebrane tutaj, żeby łatwo było je zmienić
w jednym miejscu (np. wagi losowania bonusów).
"""

APP_NAME = "Fa milia"
APP_ID = "fa-milia"  # używane w nazwie katalogu danych i pliku .desktop

# --- Plansza ---------------------------------------------------------------

ROW_COUNT = 5  # liczba pytań w kategorii (rzędów na planszy)
CATEGORIES_PER_ROUND = 6  # liczba kategorii (kolumn) w rundzie

# Wartości pól w kolejnych rzędach (rząd 1 = najłatwiejsze pytanie).
ROUND_VALUES = {
    1: (100, 200, 300, 400, 500),
    2: (200, 400, 600, 800, 1000),
}

# --- Zawodnicy -------------------------------------------------------------

MIN_PLAYERS = 1
MAX_PLAYERS = 8

# --- Bonusy ----------------------------------------------------------------

BONUSES_PER_ROUND = 2

# Waga losowania bonusu dla każdego rzędu. Waga 0 oznacza „nigdy”.
BONUS_ROW_WEIGHTS = {
    1: 0.0,
    2: 1.0,
    3: 1.5,
    4: 1.5,
    5: 1.5,
}

# Mnożnik wagi dla drugiego bonusu w tej samej kategorii co pierwszy.
BONUS_SAME_CATEGORY_FACTOR = 0.3

# --- Pliki mediów ----------------------------------------------------------

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
SOUND_EXTENSIONS = (".mp3", ".wav", ".ogg")

# --- Skróty klawiszowe (wyświetlane w Ustawieniach i opisane w README) -----

SHORTCUTS = [
    ("Spacja", "Odsłoń odpowiedź / wróć do planszy / dalej"),
    ("Esc", "Wstecz; w pytaniu zamyka pytanie; na planszy – menu (z potwierdzeniem)"),
    ("Ctrl+Z", "Cofnij ostatnią akcję w grze"),
    ("F2", "Pokaż / ukryj panel prowadzącego (tryb jednoekranowy)"),
    ("F11", "Pełny ekran / okno"),
]
