# Fa milia

Domowa gra w stylu teleturnieju Va banque (Jeopardy) do grania z rodziną:
plansza na telewizorze lub rzutniku, prowadzący steruje grą z laptopa.
Program działa w pełni offline.

## Szybki start (Fedora KDE)

```bash
cd "Fa milia"
./install.sh
```

Skrypt zbuduje program (za pierwszym razem kilka minut, potrzebny internet tylko do
pobrania bibliotek) i doda **Fa milię** do menu KDE (kategoria *Gry*). Program startuje
w pełnym ekranie i działa całkowicie offline.

Odinstalowanie z menu: `./install.sh --odinstaluj` (dane użytkownika zostają).

## Wymagania i zależności systemowe

- Python 3.12 lub nowszy (Fedora ma go domyślnie).
- Odtwarzanie dźwięku **nie wymaga** dodatkowych kodeków z RPM Fusion: biblioteka PySide6
  z pip zawiera własne FFmpeg dla Qt Multimedia (obsługuje .wav, .ogg i .mp3).
- Do budowania pliku wykonywalnego PyInstaller potrzebuje programu `objdump` z pakietu
  `binutils` (na Fedorze zwykle już zainstalowany: `sudo dnf install binutils`).

## Uruchomienie z kodu źródłowego (dla programisty)

```bash
cd "Fa milia"
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m fa_milia
```

Testy: `.venv/bin/pytest`

## Gdzie są dane

| System | Katalog danych |
|---|---|
| Linux | `~/.local/share/fa-milia/` |
| Windows (plik .exe) | folder `Fa milia - dane` obok pliku .exe; gdy tam nie da się zapisywać (np. `Program Files`) – `%APPDATA%\fa-milia` |

Przy pierwszym uruchomieniu program dodaje 14 przykładowych kategorii, 3 pytania finałowe
i proste dźwięki. Zmienna środowiskowa `FA_MILIA_DATA_DIR` pozwala wskazać inny katalog.

## Budowanie pliku wykonywalnego

### Linux

```bash
packaging/build_linux.sh          # jeden plik: dist/fa-milia
packaging/build_linux.sh folder   # folder: dist/fa-milia/fa-milia
```

`./install.sh` kopiuje `dist/fa-milia` do `~/.local/bin`, a ikonę i plik `.desktop` do
katalogów menu KDE.

### Windows

PyInstaller nie potrafi zbudować pliku .exe na Linuksie – trzeba to zrobić na komputerze
z Windows:

1. Zainstaluj Python 3.12+ ze strony python.org (zaznacz *Add python.exe to PATH*).
2. Skopiuj folder projektu na komputer z Windows (bez folderów `.venv`, `build`, `dist`).
3. Uruchom `packaging\build_windows.bat` (dwuklik). Powstanie `dist\Fa milia.exe`.
   Wariant „folder” (rzadziej oznaczany przez antywirusy): `packaging\build_windows.bat folder`.

Plik .exe można skopiować w dowolne miejsce (także na pendrive) – dane programu trafią
do folderu `Fa milia - dane` obok niego. Program nie jest podpisany cyfrowo, więc przy
pierwszym uruchomieniu Windows może pokazać okno „System Windows ochronił ten komputer” –
kliknij „Więcej informacji” → „Uruchom mimo to”.

## Skróty klawiszowe

| Klawisz | Działanie |
|---|---|
| Spacja | odsłoń odpowiedź / wróć do planszy / dalej |
| Esc | wstecz; w pytaniu zamyka pytanie; na planszy – menu (z potwierdzeniem) |
| Ctrl+Z | cofnij ostatnią akcję w grze |
| P | pauza / wznowienie timera |
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
- **Timer** (Ustawienia → Timer i dźwięk): rusza po pokazaniu pytania (z wyjątkiem pytań
  bonusowych, które są bez timera), znika po odsłonięciu odpowiedzi. Prowadzący może go wstrzymać i wznowić (klawisz P) lub uruchomić od nowa.

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

## Zapis gry, pamięć wykorzystania, zestawy

- **Zapis gry:** gra zapisuje się automatycznie po każdej akcji. Po zamknięciu programu
  (także przypadkowym) dokończysz ją przez „Kontynuuj grę” – razem z możliwością cofania.
- **Pamięć wykorzystania:** kategoria jest „użyta” od rozpoczęcia gry, w której wystąpiła,
  a pytanie finałowe – od chwili wyświetlenia. Użyte kategorie są wyszarzone przy wyborze,
  a „Losuj” i losowanie finału biorą najpierw nieużyte. Reset: Ustawienia → Pamięć gier;
  pojedynczy element odznaczysz w edytorze.
- **Zestawy:** zapisany wybór 6 + 6 kategorii i pytania finałowego („Zapisz jako zestaw…”
  przy wyborze kategorii albo menu → Zestawy).

## Format plików do importu (dla rodziny)

Pytania można przygotować w zwykłym Notatniku. Najprościej: Import / Eksport →
„Utwórz pusty szablon…” – powstanie folder z plikiem `WZOR.txt` i instrukcją
`JAK_DODAC_PYTANIA.txt`. Przykład gotowego folderu: `examples/przyklad_importu/`.

Jeden plik `.txt` = jedna kategoria:

```
KATEGORIA: Zwierzęta

1
P: Ile nóg ma pająk?
O: Osiem

2
P: Jak nazywa się to zwierzę?
O: Kapibara
```

- Numery 1–5 to rzędy (1 = najłatwiejsze); zamiast nich można pisać 100–500.
- Zamiast `P:` można pisać `Pytanie:`, zamiast `O:` – `Odpowiedź:`/`Odpowiedz:`.
  Wielkość liter i polskie znaki w tych słowach nie mają znaczenia.
- Puste linie i linie zaczynające się od `#` są pomijane. Odpowiedź może mieć kilka linii.
- Kodowanie UTF-8 albo Windows-1250 (stary Notatnik) – rozpoznawane automatycznie.
- Zdjęcia i dźwięki w tym samym folderze: `<nazwa pliku txt>_<numer>.<rozszerzenie>`,
  np. `zwierzeta_2.jpg`, `zwierzeta_3.mp3` (obrazy .jpg/.jpeg/.png, dźwięki .mp3/.wav/.ogg).
  Tekst po `P:` staje się wtedy podpisem (może być pusty).
- Pytania finałowe: plik `final.txt` (albo `finał.txt`) z blokami `1`, `KATEGORIA:`, `P:`, `O:`;
  media `final_1.jpg` itd.

Import (folder albo `.zip`) pokazuje podgląd: co zostanie dodane, co jest niekompletne
i jakie są błędy (np. „zwierzeta.txt, pytanie 4: brak odpowiedzi”). Przy powtórzonej nazwie
można pominąć, zastąpić albo zapisać kopię. Eksport tworzy folder w tym samym formacie.

## Kopia zapasowa

Import / Eksport → „Utwórz kopię zapasową…” zapisuje wszystkie dane programu w jednym
pliku `.zip`. „Przywróć z kopii…” zastępuje obecne dane zawartością kopii; dotychczasowe
dane są odkładane do katalogu `~/.local/share/fa-milia-przed-przywroceniem/`.

## Rozwiązywanie problemów

- **Brak dźwięku:** Ustawienia → Timer i dźwięk → „▶ Próbka”. Lista pod spodem pokazuje,
  które pliki dźwięków zostały znalezione. Sprawdź też głośność systemu.
- **Plansza nie otwiera się na telewizorze:** telewizor musi być ekranem *rozszerzonym*.
  W Ustawieniach → Ekrany wybierz właściwy monitor („Pokaż nazwy na monitorach”).
- **Skróty klawiszowe nie działają po starcie gry:** kliknij raz okno panelu prowadzącego
  (na Waylandzie system nie zawsze przenosi fokus automatycznie).

## Struktura projektu

- `fa_milia/core/` – logika i dane (bez Qt)
- `fa_milia/ui/` – interfejs (PySide6)
- `fa_milia/resources/` – ikona i przykładowe media
- `tests/` – testy logiki (pytest)
- `examples/przyklad_importu/` – przykładowy folder do przetestowania importu
- `packaging/` – PyInstaller (`fa-milia.spec`), skrypty budowania, plik `.desktop`
- `install.sh` – instalacja w menu KDE
- `tools/generate_sample_media.py` – generator przykładowych flag, obrazków, dźwięków i ikon
