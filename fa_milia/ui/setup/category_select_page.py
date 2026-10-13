"""Nowa gra, krok 2: wybór 6 kategorii do rundy 1 i 6 do rundy 2 oraz finału."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.library import Library
from fa_milia.core.sets import SetStore
from fa_milia.core.usage import UsageMemory
from fa_milia.ui.setup.category_picker import CategoryPicker
from fa_milia.ui.setup.players_page import page_title
from fa_milia.ui.setup.set_dialogs import choose_set, save_set


class CategorySelectPage(QWidget):
    back_requested = Signal()
    # kategorie rundy 1 i 2, czy z finałem, id pytania finałowego z zestawu ("" = losowe)
    start_requested = Signal(list, list, bool, str)

    def __init__(self, library: Library, usage: UsageMemory, sets: SetStore,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._usage = usage
        self._sets = sets
        self._set_final_id: str | None = None  # finał z wczytanego zestawu
        self._set_name = ""

        self._picker = CategoryPicker()
        self._picker.changed.connect(self._update_start_button)
        load_set_button = QPushButton("Wczytaj zestaw…")
        load_set_button.clicked.connect(self._load_set)
        save_set_button = QPushButton("Zapisz jako zestaw…")
        save_set_button.clicked.connect(self._save_set)
        self._picker.add_tool(save_set_button)
        self._picker.add_tool(load_set_button)

        self._final_check = QCheckBox("Finał")
        self._final_check.setChecked(True)
        self._final_check.toggled.connect(self._update_final_label)
        self._final_label = QLabel()
        final_row = QHBoxLayout()
        final_row.addWidget(self._final_check)
        final_row.addWidget(self._final_label, stretch=1)

        self._info = QLabel()
        self._info.setStyleSheet("color: gray;")
        self._info.setWordWrap(True)

        back_button = QPushButton("← Wstecz")
        back_button.clicked.connect(self.back_requested)
        self._start_button = QPushButton("Rozpocznij grę ▶")
        self._start_button.clicked.connect(self._start)
        buttons = QHBoxLayout()
        buttons.addWidget(back_button)
        buttons.addStretch()
        buttons.addWidget(self._start_button)

        layout = QVBoxLayout(self)
        layout.addWidget(page_title("Nowa gra – wybór kategorii"))
        layout.addWidget(self._picker, stretch=1)
        layout.addLayout(final_row)
        layout.addWidget(self._info)
        layout.addLayout(buttons)

    # --- Wejście na stronę -------------------------------------------------

    def prepare(self) -> None:
        """Wczytuje aktualną listę kompletnych kategorii (wybór z poprzedniej gry zostaje)."""
        categories = self._library.complete_categories()
        self._picker.set_categories(categories, self._usage.used_category_ids())

        if self._set_final_id and self._set_final_id not in self._library.finals:
            self._set_final_id = None
        has_finals = bool(self._library.complete_finals())
        self._final_check.setEnabled(has_finals)
        if not has_finals:
            self._final_check.setChecked(False)
        self._update_final_label()

        incomplete = len(self._library.categories) - len(categories)
        if incomplete:
            self._info.setText(f"Niekompletne kategorie ({incomplete}) nie są tu pokazane – "
                               "uzupełnij je w edytorze kategorii.")
        else:
            self._info.setText("")
        self._update_start_button()

    def request_back(self) -> None:
        self.back_requested.emit()

    # --- Finał i zestawy -----------------------------------------------------

    def _update_final_label(self) -> None:
        if not self._final_check.isEnabled():
            text = "brak kompletnych pytań finałowych – dodaj je w edytorze pytań finałowych"
        elif not self._final_check.isChecked():
            text = "gra bez finału"
        elif self._set_final_id:
            final = self._library.finals[self._set_final_id]
            text = f"pytanie z zestawu „{self._set_name}”: {final.category}"
        else:
            unused = [f for f in self._library.complete_finals()
                      if not self._usage.is_final_used(f.id)]
            text = (f"pytanie zostanie wylosowane spośród nieużytych ({len(unused)})" if unused
                    else "wszystkie pytania finałowe były już użyte – zostanie wylosowane "
                         "jedno z nich")
        self._final_label.setText(text)

    def _load_set(self) -> None:
        game_set = choose_set(self, self._sets, self._library)
        if game_set is None:
            return
        messages = self._picker.set_selection(game_set.round1, game_set.round2)
        self._set_name = game_set.name
        self._set_final_id = game_set.final if game_set.final in self._library.finals else None
        if game_set.final and self._set_final_id is None:
            messages.append("Pytanie finałowe z zestawu zostało usunięte – będzie losowane.")
        if self._set_final_id:
            self._final_check.setChecked(True)
        self._picker.show_message(" ".join(messages) or f"Wczytano zestaw „{game_set.name}”.")
        self._update_final_label()

    def _save_set(self) -> None:
        round1, round2 = self._picker.rounds()
        if not self._picker.is_complete():
            self._picker.show_message("Zestaw musi mieć komplet 6 + 6 kategorii.")
            return
        game_set = save_set(self, self._sets, self._library, round1, round2,
                            self._set_final_id, self._set_name)
        if game_set is not None:
            self._set_name = game_set.name
            self._set_final_id = game_set.final
            self._picker.show_message(f"Zapisano zestaw „{game_set.name}”.")
            self._update_final_label()

    # --- Start -----------------------------------------------------------------

    def _update_start_button(self) -> None:
        self._start_button.setEnabled(self._picker.is_complete())

    def _start(self) -> None:
        if not self._picker.is_complete():
            return
        by_id = {c.id: c for c in self._library.complete_categories()}
        round1_ids, round2_ids = self._picker.rounds()
        with_final = self._final_check.isEnabled() and self._final_check.isChecked()
        self.start_requested.emit([by_id[i] for i in round1_ids], [by_id[i] for i in round2_ids],
                                  with_final, self._set_final_id or "")
