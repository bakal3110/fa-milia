"""Nowa gra, krok 2: wybór 6 kategorii do rundy 1 i 6 do rundy 2."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fa_milia.config import CATEGORIES_PER_ROUND
from fa_milia.core.library import Library
from fa_milia.core.models import Category
from fa_milia.core.selection import ROUND_NUMBERS, CategorySelection, SelectionError
from fa_milia.ui.setup.players_page import page_title

NAME_COLUMN = 0
ID_ROLE = Qt.ItemDataRole.UserRole


class CategorySelectPage(QWidget):
    back_requested = Signal()
    start_requested = Signal(list, list)  # kategorie rundy 1, kategorie rundy 2

    def __init__(self, library: Library, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._selection = CategorySelection()
        self._categories: list[Category] = []

        self._counter = QLabel()
        self._counter.setStyleSheet("font-weight: bold;")
        random_button = QPushButton("Losuj")
        random_button.setToolTip("Uzupełnia brakujące miejsca losowymi kategoriami")
        random_button.clicked.connect(self._fill_randomly)
        clear_button = QPushButton("Wyczyść")
        clear_button.clicked.connect(self._clear)
        load_set_button = QPushButton("Wczytaj zestaw…")
        load_set_button.setEnabled(False)
        load_set_button.setToolTip("Dostępne od etapu E5")
        self._final_check = QCheckBox("Finał")
        self._final_check.setEnabled(False)
        self._final_check.setToolTip("Dostępne od etapu E4")
        tools = QHBoxLayout()
        tools.addWidget(self._counter)
        tools.addStretch()
        tools.addWidget(self._final_check)
        tools.addWidget(load_set_button)
        tools.addWidget(clear_button)
        tools.addWidget(random_button)

        # Tabela: nazwa kategorii + dwa pola wyboru (runda 1, runda 2).
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Kategoria", "Runda 1", "Runda 2"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        for column in ROUND_NUMBERS:
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.itemChanged.connect(self._on_item_changed)

        self._order = QLabel()
        self._order.setWordWrap(True)
        self._info = QLabel()
        self._info.setStyleSheet("color: gray;")
        self._info.setWordWrap(True)
        self._message = QLabel()
        self._message.setStyleSheet("color: #b03030;")
        self._message.setWordWrap(True)

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
        layout.addLayout(tools)
        layout.addWidget(self._table, stretch=1)
        layout.addWidget(self._order)
        layout.addWidget(self._info)
        layout.addWidget(self._message)
        layout.addLayout(buttons)

    # --- Wejście na stronę -------------------------------------------------

    def prepare(self) -> None:
        """Wczytuje aktualną listę kompletnych kategorii (wybór z poprzedniej gry zostaje)."""
        self._categories = self._library.complete_categories()
        self._selection.keep_only({c.id for c in self._categories})
        self._message.setText("")

        self._table.blockSignals(True)  # wypełnianie tabeli to nie zmiana wyboru
        self._table.setRowCount(len(self._categories))
        for row, category in enumerate(self._categories):
            name_item = QTableWidgetItem(category.name)
            name_item.setData(ID_ROLE, category.id)
            self._table.setItem(row, NAME_COLUMN, name_item)
            for column in ROUND_NUMBERS:
                check_item = QTableWidgetItem()
                check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, column, check_item)
        self._table.blockSignals(False)

        incomplete = len(self._library.categories) - len(self._categories)
        if incomplete:
            self._info.setText(f"Niekompletne kategorie ({incomplete}) nie są tu pokazane – "
                               "uzupełnij je w edytorze kategorii.")
        else:
            self._info.setText("")
        self._sync()

    def request_back(self) -> None:
        self.back_requested.emit()

    # --- Zmiany wyboru -----------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        round_number = item.column()
        if round_number not in ROUND_NUMBERS:
            return
        category_id = self._table.item(item.row(), NAME_COLUMN).data(ID_ROLE)
        checked = item.checkState() == Qt.CheckState.Checked
        current = self._selection.round_of(category_id)
        if checked:
            target = round_number
        else:
            target = None if current == round_number else current
        self._message.setText("")
        try:
            self._selection.set_round(category_id, target)
        except SelectionError as error:
            self._message.setText(str(error))
        self._sync()

    def _fill_randomly(self) -> None:
        self._selection.fill_randomly([c.id for c in self._categories], used_ids=set())
        if self._selection.is_complete():
            self._message.setText("")
        else:
            needed = CATEGORIES_PER_ROUND * len(ROUND_NUMBERS)
            self._message.setText(f"Za mało kompletnych kategorii: jest {len(self._categories)}, "
                                  f"potrzeba {needed}. Dodaj kategorie w edytorze.")
        self._sync()

    def _clear(self) -> None:
        self._selection.clear()
        self._message.setText("")
        self._sync()

    def _sync(self) -> None:
        """Ustawia pola wyboru, liczniki i przycisk startu zgodnie ze stanem wyboru."""
        names = {c.id: c.name for c in self._categories}
        self._table.blockSignals(True)
        for row in range(self._table.rowCount()):
            category_id = self._table.item(row, NAME_COLUMN).data(ID_ROLE)
            chosen = self._selection.round_of(category_id)
            for column in ROUND_NUMBERS:
                state = Qt.CheckState.Checked if chosen == column else Qt.CheckState.Unchecked
                self._table.item(row, column).setCheckState(state)
        self._table.blockSignals(False)

        self._counter.setText("   ".join(
            f"Runda {n}: {self._selection.count(n)} / {CATEGORIES_PER_ROUND}"
            for n in ROUND_NUMBERS
        ))
        order_lines = []
        for number in ROUND_NUMBERS:
            chosen_names = [names[i] for i in self._selection.rounds[number]]
            order_lines.append(f"<b>Plansza rundy {number}:</b> " + (", ".join(chosen_names) or "—"))
        self._order.setText("<br>".join(order_lines))
        self._start_button.setEnabled(self._selection.is_complete())

    def _start(self) -> None:
        if not self._selection.is_complete():
            return
        by_id = {c.id: c for c in self._categories}
        round1 = [by_id[i] for i in self._selection.rounds[1]]
        round2 = [by_id[i] for i in self._selection.rounds[2]]
        self.start_requested.emit(round1, round2)
