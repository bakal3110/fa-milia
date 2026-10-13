# Fa milia – zasady projektu

## O projekcie
Domowa gra w stylu Va banque (Jeopardy) w Pythonie i PySide6. Fedora KDE, dwa ekrany (TV + laptop prowadzącego). Wyłącznie offline, użytek rodzinny.

## Zasady
- Interfejs i komunikaty po polsku. Kod, nazwy zmiennych i funkcji po angielsku, komentarze po polsku.
- Właściciel projektu uczy się Pythona: pisz czytelnie, komentuj nieoczywiste fragmenty, unikaj „sprytnych” skrótów.
- Logika gry (`core/`) nie importuje niczego z Qt. Interfejs (`ui/`) korzysta z logiki, nie odwrotnie.
- Żadnego kodu sieciowego.
- Dane użytkownika tylko w `~/.local/share/fa-milia/`.
- Brakujące pliki dźwięków lub mediów nigdy nie powodują błędu programu.
- Format tekstowy importu jest przeznaczony dla osób nietechnicznych: każda zmiana w nim musi pozostać prosta i być opisana w `JAK_DODAC_PYTANIA.txt`.

## Przed zakończeniem zadania
- Uruchom testy: `pytest`
- Sprawdź, że program się uruchamia: `python -m fa_milia`
- Zrób commit z opisowym komunikatem po polsku.

## Współpraca
- Przy zmianach w zasadach gry lub w formacie danych najpierw zapytaj.
- Po każdym etapie podaj, co ręcznie przetestować.
