"""Przykładowe kategorie i pytania finałowe dodawane przy pierwszym uruchomieniu.

Pytanie tekstowe zapisujemy krótko jako parę (treść, odpowiedź).
Pytanie z obrazem lub dźwiękiem to słownik z dodatkowym kluczem "media" –
nazwą pliku z katalogu fa_milia/resources/sample_media/.
"""

from pathlib import Path

from fa_milia.core.library import Library
from fa_milia.core.models import Category, ContentKind, FinalQuestion, Question, kind_for_file

SAMPLE_CATEGORIES = [
    ("Zwierzęta", [
        ("Ile nóg ma pająk?", "Osiem"),
        ("Jak nazywa się młode konia?", "Źrebię (źrebak)"),
        ("Które zwierzę jest największym ssakiem na Ziemi?", "Płetwal błękitny"),
        ("Jak nazywa się samica jelenia?", "Łania"),
        ("Ile serc ma ośmiornica?", "Trzy"),
    ]),
    ("Polska", [
        ("Jak nazywa się stolica Polski?", "Warszawa"),
        ("Jaka rzeka przepływa przez Kraków i Warszawę?", "Wisła"),
        ("Jak nazywa się najwyższy szczyt Polski?", "Rysy"),
        ("Ile województw ma Polska?", "16"),
        ("W którym roku Polska wstąpiła do Unii Europejskiej?", "W 2004"),
    ]),
    ("Bajki i baśnie", [
        ("Kto zgubił szklany pantofelek na balu?", "Kopciuszek"),
        ("Ilu krasnoludków spotkała Królewna Śnieżka?", "Siedmiu"),
        ("Jak miał na imię drewniany chłopiec, któremu rósł nos, gdy kłamał?", "Pinokio"),
        ("Jak nazywał się smok z krakowskiej legendy?", "Smok Wawelski"),
        ("Kto napisał baśń „Brzydkie kaczątko”?", "Hans Christian Andersen"),
    ]),
    ("Kuchnia", [
        ("Z czego robi się frytki?", "Z ziemniaków"),
        ("Jak nazywa się czerwona zupa z buraków?", "Barszcz (czerwony)"),
        ("Z jakiego kraju pochodzi pizza?", "Z Włoch"),
        ("Jak nazywa się japońska potrawa z ryżu i surowej ryby?", "Sushi"),
        ("Jaka przyprawa, otrzymywana z kwiatów krokusa, jest najdroższa na świecie?", "Szafran"),
    ]),
    ("Kosmos", [
        ("Jak nazywa się gwiazda najbliższa Ziemi?", "Słońce"),
        ("Którą planetę nazywa się Czerwoną Planetą?", "Marsa"),
        ("Ile planet krąży wokół Słońca?", "Osiem"),
        ("Jak nazywał się pierwszy człowiek, który stanął na Księżycu?", "Neil Armstrong"),
        ("Jak nazywa się galaktyka, w której leży Układ Słoneczny?", "Droga Mleczna"),
    ]),
    ("Sport", [
        ("Ilu zawodników jednej drużyny gra na boisku w piłce nożnej?", "Jedenastu"),
        ("Ile kół jest na fladze olimpijskiej?", "Pięć"),
        ("Co ile lat odbywają się letnie igrzyska olimpijskie?", "Co cztery lata"),
        ("Jak nazywa się polski skoczek narciarski, trzykrotny mistrz olimpijski?", "Kamil Stoch"),
        ("Ile minut trwa mecz piłki ręcznej (bez przerwy)?", "60 minut (2 × 30)"),
    ]),
    ("Muzyka", [
        ("Ile linii ma pięciolinia?", "Pięć"),
        ("Ile strun ma zwykła gitara klasyczna?", "Sześć"),
        ("Jak nazywa się kompozytor polonezów i mazurków urodzony w Żelazowej Woli?", "Fryderyk Chopin"),
        ("Jak nazywał się zespół z Liverpoolu, w którym grali John Lennon i Paul McCartney?", "The Beatles"),
        ("Ile klawiszy ma typowy fortepian?", "88"),
    ]),
    ("Ciało człowieka", [
        ("Ile palców mają razem obie dłonie człowieka?", "Dziesięć"),
        ("Który narząd pompuje krew?", "Serce"),
        ("Ile zębów stałych ma dorosły człowiek (razem z zębami mądrości)?", "32"),
        ("Jak nazywa się najdłuższa kość w ciele człowieka?", "Kość udowa"),
        ("Ile kości ma dorosły człowiek?", "Około 206"),
    ]),
    ("Geografia świata", [
        ("Na jakim kontynencie leży Egipt?", "W Afryce"),
        ("Jak nazywa się największy ocean na Ziemi?", "Ocean Spokojny (Pacyfik)"),
        ("Jak nazywa się najwyższa góra świata?", "Mount Everest"),
        ("Jak nazywa się stolica Australii?", "Canberra"),
        ("Z iloma państwami graniczy Polska?", "Z siedmioma"),
    ]),
    ("Dokończ przysłowie", [
        ("„Kto rano wstaje, …”", "…temu Pan Bóg daje"),
        ("„Gdzie kucharek sześć, …”", "…tam nie ma co jeść"),
        ("„Lepszy wróbel w garści …”", "…niż gołąb na dachu"),
        ("„Nie chwal dnia …”", "…przed zachodem słońca"),
        ("„Darowanemu koniowi …”", "…nie zagląda się w zęby"),
    ]),
    ("Filmy animowane", [
        ("Jak ma na imię miś, który uwielbia miód i przyjaźni się z Prosiaczkiem?", "Kubuś Puchatek"),
        ("Jak ma na imię królowa z „Krainy lodu”, która potrafi wyczarować lód?", "Elsa"),
        ("Jak ma na imię lew, główny bohater „Króla Lwa”?", "Simba"),
        ("Jak nazywa się chłopiec, który nie chciał dorosnąć i mieszkał w Nibylandii?", "Piotruś Pan"),
        ("Jak nazywa się kowboj, główny bohater „Toy Story”?", "Chudy (ang. Woody)"),
    ]),
    ("Łamigłówki", [
        ("Ile boków ma sześciokąt?", "Sześć"),
        ("Ile to jest 7 × 8?", "56"),
        ("Ile minut ma doba?", "1440"),
        ("Ile to jest pierwiastek kwadratowy ze 144?", "12"),
        ("Tata Ani ma pięć córek: Lalę, Lelę, Lilę i Lolę. Jak ma na imię piąta córka?", "Ania"),
    ]),
    ("Flagi", [
        {"text": "Którego kraju to flaga?", "media": "flaga_polska.png", "answer": "Polski"},
        {"text": "Którego kraju to flaga?", "media": "flaga_japonia.png", "answer": "Japonii"},
        {"text": "Którego kraju to flaga?", "media": "flaga_francja.png", "answer": "Francji"},
        {"text": "Którego kraju to flaga?", "media": "flaga_szwecja.png", "answer": "Szwecji"},
        {"text": "Którego kraju to flaga?", "media": "flaga_czechy.png", "answer": "Czech"},
    ]),
    ("Zagadki dźwiękowe", [
        {"text": "Ile sygnałów usłyszeliście?", "media": "dzwiek_trzy_sygnaly.wav", "answer": "Trzy"},
        {"text": "Czy melodia idzie w górę, czy w dół?", "media": "dzwiek_gama.wav", "answer": "W górę"},
        {"text": "Jaka to piosenka?", "media": "dzwiek_wlazl_kotek.wav", "answer": "„Wlazł kotek na płotek”"},
        {"text": "Jaka to piosenka?", "media": "dzwiek_panie_janie.wav", "answer": "„Panie Janie”"},
        {"text": "Ile sygnałów usłyszeliście?", "media": "dzwiek_siedem_sygnalow.wav", "answer": "Siedem"},
    ]),
]

# (kategoria, pytanie, odpowiedź)
SAMPLE_FINALS = [
    ("Historia Polski", "W którym roku odbył się chrzest Polski?", "W 966 roku"),
    ("Wielcy Polacy", "Jak nazywała się polska noblistka, która odkryła polon i rad?",
     "Maria Skłodowska-Curie"),
    ("Przyroda", "Jak nazywa się proces, w którym rośliny wytwarzają tlen dzięki światłu słonecznemu?",
     "Fotosynteza"),
]


def _build_question(entry, library: Library, media_source: Path) -> Question:
    """Zamienia wpis z listy powyżej na obiekt Question."""
    # isinstance sprawdza typ: krotka (treść, odpowiedź) albo słownik z mediami.
    if isinstance(entry, tuple):
        text, answer = entry
        return Question(kind=ContentKind.TEXT, text=text, answer=answer)

    media_name = library.import_media(media_source / entry["media"])
    return Question(
        kind=kind_for_file(media_name),
        text=entry["text"],
        media=media_name,
        answer=entry["answer"],
    )


def install_sample_data(library: Library, media_source: Path) -> None:
    """Dodaje do biblioteki wszystkie przykładowe kategorie i finały."""
    for name, entries in SAMPLE_CATEGORIES:
        questions = [_build_question(e, library, media_source) for e in entries]
        library.save_category(Category(name=name, questions=questions))
    for category, text, answer in SAMPLE_FINALS:
        question = Question(kind=ContentKind.TEXT, text=text, answer=answer)
        library.save_final(FinalQuestion(category=category, question=question))


def install_if_first_run(library: Library, media_source: Path) -> bool:
    """Instaluje przykładowe dane tylko przy pierwszym uruchomieniu programu.

    Zwraca True, jeśli dane zostały właśnie dodane. Plik-znacznik sprawia, że
    po usunięciu przykładowych kategorii nie pojawią się one ponownie.
    """
    marker = library.data_dir.sample_marker
    if marker.exists():
        return False
    install_sample_data(library, media_source)
    marker.write_text("Przykładowe dane zostały dodane.\n", encoding="utf-8")
    return True
