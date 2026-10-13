"""Tabela wyboru 6 + 6 kategorii – używana przy nowej grze i w edytorze zestawów."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from fa_milia.core.models import Category
from fa_milia.core.selection import ROUND_NUMBERS, CategorySelection, SelectionError

NAME_COLUMN = 0
STATUS_COLUMN = 3
ID_ROLE = Qt.ItemDataRole.UserRole
USED_COLOR = QBrush(QColor("#8a8f99"))


class CategoryPicker(QWidget):
    changed = Signal()  # zmienił się wybór kategorii

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selection = CategorySelection()
        self._categories: list[Category] = []
        self._used: set[str] = set()

        self._counter = QLabel()
        self._counter.setStyleSheet("font-weight: bold;")
        random_button = QPushButton("Losuj")
        random_button.setToolTip("Uzupełnia brakujące miejsca losowymi kategoriami "
                                 "(najpierw nieużytymi)")
        random_button.clicked.connect(self._fill_randomly)
        clear_button = QPushButton("Wyczyść")
        clear_button.clicked.connect(self._clear)
        self._tools = QHBoxLayout()
        self._tools.addWidget(self._counter)
        self._tools.addStretch()
        self._tools.addWidget(clear_button)
        self._tools.addWidget(random_button)

        # Tabela: nazwa, dwa pola wyboru (runda 1, runda 2) i status „użyta”.
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Kategoria", "Runda 1", "Runda 2", ""])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        for column in (*ROUND_NUMBERS, STATUS_COLUMN):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.itemChanged.connect(self._on_item_changed)

        self._order = QLabel()
        self._order.setWordWrap(True)
        self._message = QLabel()
        self._message.setStyleSheet("color: #b03030;")
        self._message.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._tools)
        layout.addWidget(self._table, stretch=1)
        layout.addWidget(self._order)
        layout.addWidget(self._message)

    def add_tool(self, widget: QWidget) -> None:
        """Dodaje przycisk (np. „Wczytaj zestaw…”) do paska nad tabelą."""
        self._tools.insertWidget(2, widget)

    # --- Dane ---------------------------------------------------------------

    def set_categories(self, categories: list[Category], used_ids: set[str]) -> None:
        """Ustawia listę kategorii do wyboru (wybór, który nadal pasuje, zostaje)."""
        self._categories = categories
        self._used = used_ids
        self._selection.keep_only({c.id for c in categories})
        self._message.setText("")

        self._table.blockSignals(True)  # wypełnianie tabeli to nie zmiana wyboru
        self._table.setRowCount(len(categories))
        for row, category in enumerate(categories):
            used = category.id in used_ids
            name_item = QTableWidgetItem(category.name)
            name_item.setData(ID_ROLE, category.id)
            status_item = QTableWidgetItem("użyta" if used else "")
            if used:
                # Użyte są wyszarzone, ale nadal można je zaznaczyć ręcznie.
                name_item.setForeground(USED_COLOR)
                status_item.setForeground(USED_COLOR)
                name_item.setToolTip("Ta kategoria była już w grze")
            self._table.setItem(row, NAME_COLUMN, name_item)
            self._table.setItem(row, STATUS_COLUMN, status_item)
            for column in ROUND_NUMBERS:
                check_item = QTableWidgetItem()
                check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, column, check_item)
        self._table.blockSignals(False)
        self._sync()

    def set_selection(self, round1: list[str], round2: list[str]) -> list[str]:
        """Ustawia wybór (np. z zestawu). Zwraca opisy pominiętych kategorii."""
        available = {c.id for c in self._categories}
        self._selection.clear()
        skipped = 0
        for number, ids in ((1, round1), (2, round2)):
            for category_id in ids:
                if category_id in available and self._selection.round_of(category_id) is None \
                        and not self._selection.is_full(number):
                    self._selection.set_round(category_id, number)
                else:
                    skipped += 1
        self._sync()
        if skipped:
            return [f"Pominięto {skipped} kategorii (usunięte, niekompletne lub powtórzone)."]
        return []

    def rounds(self) -> tuple[list[str], list[str]]:
        return list(self._selection.rounds[1]), list(self._selection.rounds[2])

    def is_complete(self) -> bool:
        return self._selection.is_complete()

    def show_message(self, text: str) -> None:
        self._message.setText(text)

    # --- Zmiany wyboru -------------------------------------------------------

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
        taken_used = self._selection.fill_randomly([c.id for c in self._categories], self._used)
        messages = []
        if taken_used:
            messages.append(f"Zabrakło nieużytych kategorii – dobrano {taken_used} już użytych.")
        if not self._selection.is_complete():
            needed = CATEGORIES_PER_ROUND * len(ROUND_NUMBERS)
            messages.append(f"Za mało kompletnych kategorii: jest {len(self._categories)}, "
                            f"potrzeba {needed}. Dodaj kategorie w edytorze.")
        self._message.setText(" ".join(messages))
        self._sync()

    def _clear(self) -> None:
        self._selection.clear()
        self._message.setText("")
        self._sync()

    def _sync(self) -> None:
        """Ustawia pola wyboru, liczniki i opis plansz zgodnie ze stanem wyboru."""
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
        self.changed.emit()
