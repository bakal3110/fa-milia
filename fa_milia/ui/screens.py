"""Wybór monitora dla ekranu gry."""

from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication, QScreen

from fa_milia.core.settings import Settings


def describe_screen(screen: QScreen) -> str:
    """Np. „HDMI-A-1 – Samsung U28E590 (3840×2160)”."""
    size = screen.size()
    model = " ".join(part for part in (screen.manufacturer(), screen.model()) if part).strip()
    label = f"{screen.name()} – {model}" if model else screen.name()
    return f"{label} ({size.width()}×{size.height()})"


@dataclass
class ScreenChoice:
    screen: QScreen | None  # None = tryb jednoekranowy
    message: str = ""  # wyjaśnienie dla prowadzącego (np. brak monitora)


def choose_game_screen(settings: Settings, host_screen: QScreen | None) -> ScreenChoice:
    """Wybiera monitor dla ekranu gry.

    host_screen to monitor, na którym jest okno prowadzącego. Ekran gry
    musi być na innym monitorze – inaczej używamy trybu jednoekranowego.
    """
    screens = QGuiApplication.screens()
    if len(screens) < 2:
        return ScreenChoice(None)

    if settings.game_screen:
        # next(…, None) zwraca pierwszy pasujący element albo None, gdy brak.
        chosen = next((s for s in screens if s.name() == settings.game_screen), None)
        if chosen is None:
            return ScreenChoice(None, f"Wybrany ekran gry ({settings.game_screen}) nie jest "
                                      "podłączony – gra działa w trybie jednoekranowym.")
        if chosen == host_screen:
            return ScreenChoice(None, "Okno prowadzącego jest na monitorze wybranym jako ekran "
                                      "gry – gra działa w trybie jednoekranowym. Przenieś okno "
                                      "programu na laptop albo zmień monitor w Ustawieniach.")
        return ScreenChoice(chosen)

    # Automatycznie: pierwszy monitor inny niż ten z oknem prowadzącego.
    for screen in screens:
        if screen != host_screen:
            return ScreenChoice(screen)
    return ScreenChoice(None)
