"""Okna „Wczytaj zestaw” i „Zapisz jako zestaw”."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from fa_milia.core.library import Library
from fa_milia.core.sets import GameSet, SetStore, set_problems

RANDOM_FINAL_LABEL = "(losowe przy starcie gry)"


def final_combo(library: Library, selected: str | None) -> QComboBox:
    """Lista wyboru pytania finałowego: „losowe” + wszystkie kompletne finały."""
    combo = QComboBox()
    combo.addItem(RANDOM_FINAL_LABEL, None)
    for final in library.complete_finals():
        text = final.question.text.splitlines()[0] if final.question.text else "[obraz/dźwięk]"
        combo.addItem(f"{final.category}: {text[:50]}", final.id)
    index = combo.findData(selected)
    combo.setCurrentIndex(max(0, index))
    return combo


def choose_set(parent: QWidget, store: SetStore, library: Library) -> GameSet | None:
    """Pyta o zestaw do wczytania. None = anulowano albo brak zestawów."""
    sets = store.sorted_sets()
    if not sets:
        QMessageBox.information(parent, "Zestawy", "Nie ma jeszcze żadnych zestawów.\n"
                                "Wybierz kategorie i kliknij „Zapisz jako zestaw…”.")
        return None
    labels = [s.name + ("  ⚠" if set_problems(s, library) else "") for s in sets]
    # getItem zwraca (wybrany tekst, czy OK).
    label, accepted = QInputDialog.getItem(parent, "Wczytaj zestaw", "Zestaw:", labels, 0, False)
    if not accepted:
        return None
    return sets[labels.index(label)]


class SaveSetDialog(QDialog):
    def __init__(self, library: Library, default_name: str, final_id: str | None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Zapisz jako zestaw")
        self.resize(520, 140)
        self._name = QLineEdit(default_name)
        self._name.setPlaceholderText("np. Wieczór u babci")
        self._final = final_combo(library, final_id)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout(self)
        form.addRow("Nazwa zestawu:", self._name)
        form.addRow("Pytanie finałowe:", self._final)
        form.addRow(buttons)

    def name(self) -> str:
        return self._name.text().strip()

    def final_id(self) -> str | None:
        return self._final.currentData()


def save_set(parent: QWidget, store: SetStore, library: Library, round1: list[str],
             round2: list[str], final_id: str | None, default_name: str = "") -> GameSet | None:
    """Pyta o nazwę i zapisuje zestaw. Zwraca zapisany zestaw albo None."""
    dialog = SaveSetDialog(library, default_name, final_id, parent)
    while dialog.exec() == QDialog.DialogCode.Accepted:
        name = dialog.name()
        if not name:
            QMessageBox.warning(parent, "Zestaw", "Podaj nazwę zestawu.")
            continue
        if store.find(name) is not None and name.casefold() != default_name.casefold():
            answer = QMessageBox.question(parent, "Zestaw",
                                          f"Zestaw „{name}” już istnieje. Zastąpić go?")
            if answer != QMessageBox.StandardButton.Yes:
                continue
        game_set = GameSet(name, round1, round2, dialog.final_id())
        store.put(game_set)
        return game_set
    return None
