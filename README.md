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

## Zasady: bonusy, finał, timer

- **Bonusy:** w każdej rundzie 2 ukryte pola bonusowe (nigdy w pierwszym rzędzie).
  Po trafieniu prowadzący wybiera zawodnika i stawkę: od 0 do większej z wartości
  (wynik zawodnika, najwyższe pole rundy). Prowadzący może podejrzeć położenie bonusów
  w panelu („Pokaż mi położenie bonusów”, domyślnie wyłączone).
- **Finał** (przełącznik „Finał” przy wyborze kategorii): grają zawodnicy z wynikiem
  większym niż 0. Najpierw kategoria, potem stawki (od 0 do wyniku), pytanie i ocena.
  Gdy nikt nie ma punktów, finał jest pomijany.
- **Timer** (Ustawienia → Timer i dźwięk): rusza po pokazaniu pytania, znika po odsłonięciu
  odpowiedzi. Prowadzący może go wstrzymać, wznowić lub uruchomić od nowa.

## Dźwięki

Dźwięki są w folderze `~/.local/share/fa-milia/sounds/` (Ustawienia → Timer i dźwięk →
„Otwórz folder dźwięków”). Przy pierwszym uruchomieniu program dodaje tam proste dźwięki
domyślne – możesz je podmienić własnymi plikami .wav, .ogg lub .mp3 o nazwach:

| Plik | Kiedy gra |
|---|---|
| `bonus` | trafienie na pole bonusowe |
| `koniec_czasu` | upływ czasu timera |
| `dobra_odpowiedz` | oznaczenie dobrej odpowiedzi |
| `zla_odpowiedz` | oznaczenie złej odpowiedzi |
| `start_rundy` | początek rundy |
| `final` | początek finału |
| `zwyciezca` | ekran zwycięzcy |

Brak pliku nie jest błędem – program po prostu nie zagra dźwięku. Szczegóły są w pliku
`INSTRUKCJA.txt` w tym folderze.

## Struktura projektu

- `fa_milia/core/` – logika i dane (bez Qt)
- `fa_milia/ui/` – interfejs (PySide6)
- `fa_milia/resources/` – ikona i przykładowe media
- `tests/` – testy logiki (pytest)
- `tools/generate_sample_media.py` – generator przykładowych flag i dźwięków
