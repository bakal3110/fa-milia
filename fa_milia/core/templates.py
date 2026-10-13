"""Teksty plików dla rodziny: wzór kategorii i instrukcja krok po kroku.

UWAGA: każda zmiana formatu plików .txt musi zostać opisana w INSTRUCTION_FILE_TEXT.
"""

TEMPLATE_FILE_TEXT = """\
# ================================================================
#  WZÓR KATEGORII DO GRY FA MILIA
# ================================================================
#  Linie zaczynające się od # to komentarze – program je pomija.
#  Możesz je zostawić albo skasować.
#
#  Co zrobić:
#  1. Zapisz ten plik pod nową nazwą, np. zwierzeta.txt
#     (Plik → Zapisz jako…). Najlepiej bez polskich liter i spacji.
#  2. Po „KATEGORIA:” wpisz nazwę kategorii.
#  3. Po każdym „P:” wpisz pytanie, a po „O:” odpowiedź.
#     Pytanie 1 jest najłatwiejsze, pytanie 5 najtrudniejsze.
#  4. Zapisz plik.
#
#  Zdjęcie albo dźwięk do pytania: wrzuć plik do tego samego
#  folderu i nazwij go tak jak plik .txt + podkreślnik + numer
#  pytania, np. zwierzeta_2.jpg albo zwierzeta_4.mp3.
#  Wtedy tekst po „P:” będzie podpisem pod zdjęciem (może być pusty).
# ================================================================

KATEGORIA:

1
P:
O:

2
P:
O:

3
P:
O:

4
P:
O:

5
P:
O:
"""

INSTRUCTION_FILE_TEXT = """\
JAK DODAĆ PYTANIA DO GRY FA MILIA
=================================

Do przygotowania pytań wystarczy zwykły Notatnik.


KROK 1. Skopiuj wzór
--------------------
W tym folderze jest plik WZOR.txt. Otwórz go Notatnikiem
i zapisz pod nową nazwą (Plik → Zapisz jako…), np.:

    zwierzeta.txt

Jeden plik = jedna kategoria (5 pytań).
W nazwie pliku najlepiej nie używać polskich liter ani spacji.


KROK 2. Wpisz nazwę kategorii
-----------------------------
Na górze pliku, po słowie KATEGORIA i dwukropku:

    KATEGORIA: Zwierzęta

Ta nazwa pojawi się na planszy (tu polskie litery są w porządku).


KROK 3. Wpisz 5 pytań i odpowiedzi
----------------------------------
Każde pytanie zaczyna się od numeru w osobnej linii (1, 2, 3, 4, 5).
Pytanie 1 jest najłatwiejsze, pytanie 5 – najtrudniejsze.
Po „P:” wpisz pytanie, po „O:” odpowiedź:

    1
    P: Ile nóg ma pająk?
    O: Osiem

    2
    P: Jak nazywa się młode konia?
    O: Źrebię

Zamiast „P:” możesz napisać „Pytanie:”, a zamiast „O:” – „Odpowiedź:”.
Wielkość liter nie ma znaczenia. Puste linie są pomijane.
Linie zaczynające się od # to notatki dla Ciebie – program ich nie czyta.
Długą odpowiedź możesz zapisać w kilku liniach.


KROK 4. (Nieobowiązkowo) Dodaj zdjęcie lub dźwięk
-------------------------------------------------
Wrzuć plik do TEGO SAMEGO folderu co plik .txt i nazwij go tak:

    <nazwa pliku txt>_<numer pytania>.<rozszerzenie>

Przykład dla pliku zwierzeta.txt:

    zwierzeta_2.jpg    – zdjęcie do pytania 2
    zwierzeta_4.mp3    – dźwięk do pytania 4

Zdjęcia: .jpg, .jpeg, .png      Dźwięki: .mp3, .wav, .ogg

Pytanie ze zdjęciem lub dźwiękiem nadal potrzebuje „O:” z odpowiedzią.
Tekst po „P:” będzie wtedy podpisem (np. „Jak nazywa się to zwierzę?”)
i może zostać pusty.

Jak zmienić nazwę pliku: kliknij plik prawym przyciskiem myszy
→ „Zmień nazwę”. Jeśli nie widzisz końcówki „.jpg”, nie dopisuj jej
drugi raz – wystarczy zmienić część przed kropką.


KROK 5. Pytania finałowe (nieobowiązkowo)
-----------------------------------------
Utwórz plik final.txt. Każde pytanie finałowe ma numer (1, 2, 3…),
kategorię, pytanie i odpowiedź:

    1
    KATEGORIA: Historia Polski
    P: W którym roku odbył się chrzest Polski?
    O: W 966 roku

    2
    KATEGORIA: Przyroda
    P: Jak nazywa się proces wytwarzania tlenu przez rośliny?
    O: Fotosynteza

Zdjęcie do pierwszego pytania finałowego: final_1.jpg


KROK 6. Oddaj folder
--------------------
Gotowy folder (albo spakowany do .zip) przekaż prowadzącemu.
Program pokaże, co zostanie dodane, i opisze ewentualne błędy,
np. „zwierzeta.txt, pytanie 4: brak odpowiedzi”.
Niedokończone kategorie też można dodać i uzupełnić później.
"""
