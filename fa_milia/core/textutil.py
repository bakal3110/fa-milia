"""Drobne narzędzia do pracy z tekstem."""

# Kolejność liter w polskim alfabecie (z q, v, x dla wyrazów obcych).
_POLISH_ALPHABET = "aąbcćdeęfghijklłmnńoópqrsśtuvwxyzźż"


def polish_sort_key(text: str) -> list[int]:
    """Klucz sortowania zgodny z polskim alfabetem.

    Zwykłe sortowanie w Pythonie porównuje kody znaków, więc „Łódź”
    trafiłoby za „Zebra”. Zamieniamy każdą literę na jej pozycję w polskim
    alfabecie, a inne znaki (cyfry, spacje) ustawiamy przed literami.

    Użycie: sorted(names, key=polish_sort_key)
    """
    key = []
    for char in text.casefold():
        position = _POLISH_ALPHABET.find(char)
        if position >= 0:
            key.append(position)
        else:
            # Liczby ujemne trafiają przed litery, a kolejność między
            # samymi cyframi/znakami zostaje zachowana.
            key.append(ord(char) - 0x110000)
    return key
