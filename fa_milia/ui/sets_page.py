"""Zestawy: przeglądanie, tworzenie, edycja i usuwanie zapisanych wyborów 6 + 6."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.library import Library
from fa_milia.core.sets import GameSet, SetStore, set_problems
from fa_milia.core.usage import UsageMemory
from fa_milia.ui.setup.category_picker import CategoryPicker
from fa_milia.ui.setup.players_page import page_title
from fa_milia.ui.setup.set_dialogs import final_combo

NAME_ROLE = Qt.ItemDataRole.UserRole


class SetsPage(QWidget):
    back_requested = Signal()

    def __init__(self, library: Library, usage: UsageMemory, sets: SetStore,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._usage = usage
        self._sets = sets
        self._current_name: str | None = None  # None = nowy, jeszcze niezapisany zestaw
        self._dirty = False
        self._loading = False

        back_button = QPushButton("← Menu główne")
        back_button.clicked.connect(self.request_back)
        header = QHBoxLayout()
        header.addWidget(back_button)
        header.addSpacing(16)
        header.addWidget(page_title("Zestawy"))
        header.addStretch()

        # Lewa kolumna: lista zestawów.
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_item_changed)
        new_button = QPushButton("Nowy zestaw")
        new_button.clicked.connect(self._new_set)
        self._delete_button = QPushButton("Usuń")
        self._delete_button.clicked.connect(self._delete_set)
        list_buttons = QHBoxLayout()
        list_buttons.addWidget(new_button)
        list_buttons.addWidget(self._delete_button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._list, stretch=1)
        left_layout.addLayout(list_buttons)

        # Prawa kolumna: edycja zestawu.
        self._name = QLineEdit()
        self._name.textChanged.connect(self._mark_dirty)
        self._final_holder = QHBoxLayout()  # lista finałów jest budowana od nowa przy wejściu
        self._final = None
        form = QFormLayout()
        form.addRow("Nazwa zestawu:", self._name)
        form.addRow("Pytanie finałowe:", self._final_holder)
        self._picker = CategoryPicker()
        self._picker.changed.connect(self._mark_dirty)
        self._problems = QLabel()
        self._problems.setStyleSheet("color: #b8860b;")
        self._problems.setWordWrap(True)
        self._save_button = QPushButton("Zapisz zestaw")
        self._save_button.clicked.connect(self.save)
        save_row = QHBoxLayout()
        save_row.addWidget(self._problems, stretch=1)
        save_row.addWidget(self._save_button)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addLayout(form)
        right_layout.addWidget(self._picker, stretch=1)
        right_layout.addLayout(save_row)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(splitter, stretch=1)

    # --- Wejście i wyjście --------------------------------------------------

    def reload(self) -> None:
        self._sets.load()
        # Lista pytań finałowych mogła się zmienić – budujemy ją od nowa.
        if self._final is not None:
            self._final.deleteLater()
        self._final = final_combo(self._library, None)
        self._final.currentIndexChanged.connect(self._mark_dirty)
        self._final_holder.addWidget(self._final, stretch=1)
        self._refresh_list(self._current_name)
        current = self._list.currentItem()
        self._open(current.data(NAME_ROLE) if current else None)

    def request_back(self) -> None:
        if self.maybe_leave():
            self.back_requested.emit()

    def maybe_leave(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, "Niezapisane zmiany", "Zestaw ma niezapisane zmiany. Zapisać je?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        if answer == QMessageBox.StandardButton.Discard:
            self._dirty = False
            return True
        return False

    # --- Lista ------------------------------------------------------------------

    def _refresh_list(self, select_name: str | None) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for game_set in self._sets.sorted_sets():
            problems = set_problems(game_set, self._library)
            item = QListWidgetItem(("⚠ " if problems else "") + game_set.name)
            item.setData(NAME_ROLE, game_set.name)
            if problems:
                item.setToolTip("\n".join(problems))
            self._list.addItem(item)
            if select_name and game_set.name.casefold() == select_name.casefold():
                self._list.setCurrentItem(item)
        if self._list.currentItem() is None and self._list.count():
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)

    def _on_item_changed(self, current: QListWidgetItem | None,
                         previous: QListWidgetItem | None) -> None:
        if not self.maybe_leave():
            self._list.blockSignals(True)
            self._list.setCurrentItem(previous)
            self._list.blockSignals(False)
            return
        self._open(current.data(NAME_ROLE) if current else None)

    def _open(self, name: str | None) -> None:
        game_set = self._sets.find(name) if name else None
        self._loading = True
        self._current_name = game_set.name if game_set else None
        self._picker.set_categories(self._library.complete_categories(),
                                    self._usage.used_category_ids())
        if game_set is None:
            self._name.setText("")
            self._picker.set_selection([], [])
            self._final.setCurrentIndex(0)
            self._problems.setText("Brak zestawów – kliknij „Nowy zestaw”." if not name else "")
        else:
            self._name.setText(game_set.name)
            self._picker.set_selection(game_set.round1, game_set.round2)
            self._final.setCurrentIndex(max(0, self._final.findData(game_set.final)))
            problems = set_problems(game_set, self._library)
            self._problems.setText(("⚠ " + "; ".join(problems)) if problems else "")
        self._delete_button.setEnabled(game_set is not None)
        self._loading = False
        self._dirty = False

    def _mark_dirty(self) -> None:
        if not self._loading:
            self._dirty = True

    # --- Akcje ----------------------------------------------------------------

    def _new_set(self) -> None:
        if not self.maybe_leave():
            return
        self._list.blockSignals(True)
        self._list.clearSelection()
        self._list.setCurrentItem(None)
        self._list.blockSignals(False)
        self._open(None)
        self._problems.setText("Nowy zestaw: wybierz 6 + 6 kategorii i kliknij „Zapisz zestaw”.")
        self._name.setFocus()

    def save(self) -> bool:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Zestaw", "Podaj nazwę zestawu.")
            return False
        if not self._picker.is_complete():
            QMessageBox.warning(self, "Zestaw", "Zestaw musi mieć komplet 6 + 6 kategorii.")
            return False
        existing = self._sets.find(name)
        renaming_onto_other = existing is not None and (
            self._current_name is None or existing.name.casefold() != self._current_name.casefold())
        if renaming_onto_other:
            answer = QMessageBox.question(self, "Zestaw",
                                          f"Zestaw „{name}” już istnieje. Zastąpić go?")
            if answer != QMessageBox.StandardButton.Yes:
                return False
        round1, round2 = self._picker.rounds()
        self._sets.put(GameSet(name, round1, round2, self._final.currentData()),
                       replace_name=self._current_name)
        self._dirty = False
        self._refresh_list(name)
        self._open(name)
        return True

    def _delete_set(self) -> None:
        if self._current_name is None:
            return
        answer = QMessageBox.question(self, "Usuwanie",
                                      f"Usunąć zestaw „{self._current_name}”?\n"
                                      "Kategorie i pytania pozostaną w programie.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._sets.delete(self._current_name)
        self._dirty = False
        self._current_name = None
        self._refresh_list(None)
        current = self._list.currentItem()
        self._open(current.data(NAME_ROLE) if current else None)
