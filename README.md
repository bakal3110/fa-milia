# Fa milia

Domowa gra w stylu teleturnieju Va banque (Jeopardy) do grania z rodziną:
plansza na telewizorze lub rzutniku, prowadzący steruje grą z laptopa.
Program działa w pełni offline.

> Projekt powstaje etapami. Ten plik zostanie uzupełniony w etapie E6
> (pakowanie, dźwięki, format importu, skróty klawiszowe).

## Wymagania

- Fedora Linux (KDE Plasma), Python 3.12 lub nowszy

## Instalacja (tryb deweloperski)

```bash
cd "Fa milia"
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Uruchomienie

```bash
.venv/bin/python -m fa_milia
```

Przy pierwszym uruchomieniu program tworzy katalog danych
`~/.local/share/fa-milia/` i dodaje 14 przykładowych kategorii oraz 3 pytania finałowe.

## Testy

```bash
.venv/bin/pytest
```

## Skróty klawiszowe (stan na etap E2)

| Klawisz | Działanie |
|---|---|
| Spacja | w grze: odsłoń odpowiedź / wróć do planszy / następna runda |
| Esc | wstecz; w pytaniu: zamknij pytanie; na planszy: menu (z potwierdzeniem) |
| Ctrl+Z | w grze: cofnij ostatnią akcję |
| F11 | pełny ekran / okno |

## Struktura projektu

- `fa_milia/core/` – logika i dane (bez Qt)
- `fa_milia/ui/` – interfejs (PySide6)
- `fa_milia/resources/` – ikona i przykładowe media
- `tests/` – testy logiki (pytest)
- `tools/generate_sample_media.py` – generator przykładowych flag i dźwięków
