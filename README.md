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

## Skróty klawiszowe

| Klawisz | Działanie |
|---|---|
| Spacja | odsłoń odpowiedź / wróć do planszy / dalej |
| Esc | wstecz; w pytaniu zamyka pytanie; na planszy – menu (z potwierdzeniem) |
| Ctrl+Z | cofnij ostatnią akcję w grze |
| F2 | pokaż / ukryj panel prowadzącego (tryb jednoekranowy) |
| F11 | pełny ekran / okno |

Lista skrótów jest też w programie: Ustawienia → Skróty klawiszowe.

## Dwa ekrany

Podłącz telewizor lub rzutnik jako **ekran rozszerzony** (nie lustrzany).
Po rozpoczęciu gry plansza otworzy się na drugim monitorze, a panel prowadzącego
(z poprawnymi odpowiedziami) zostanie na laptopie. Monitor ekranu gry można wybrać
w Ustawieniach → Ekrany („Pokaż nazwy na monitorach” pomaga je rozpoznać).

Przy jednym monitorze program działa w trybie jednoekranowym: panel prowadzącego jest
nakładką na dole ekranu (F2 ukrywa/pokazuje), a odpowiedź widać dopiero po
przytrzymaniu przycisku „Pokaż mi”.

## Struktura projektu

- `fa_milia/core/` – logika i dane (bez Qt)
- `fa_milia/ui/` – interfejs (PySide6)
- `fa_milia/resources/` – ikona i przykładowe media
- `tests/` – testy logiki (pytest)
- `tools/generate_sample_media.py` – generator przykładowych flag i dźwięków
