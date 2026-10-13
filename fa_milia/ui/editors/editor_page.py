"""Wspólna podstawa edytorów: lista elementów po lewej, formularz po prawej.

Edytor kategorii i edytor pytań finałowych działają tak samo (lista,
„Nowa”, „Usuń”, „Zapisz”, ostrzeżenie o niezapisanych zmianach). Ten kod
jest więc w klasie bazowej, a klasy pochodne uzupełniają tylko to, co różne:
budowę formularza i operacje na konkretnym typie danych.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.library import Library
from fa_milia.ui.audio import AudioPlayer

# Rola, pod którą każdy element listy przechowuje identyfikator obiektu.
ID_ROLE = Qt.ItemDataRole.UserRole


class LibraryEditorPage(QWidget):
    back_requested = Signal()

    # Teksty uzupełniane przez klasy pochodne.
    PAGE_TITLE = ""
    NEW_BUTTON_TEXT = "Nowy"
    EMPTY_TEXT = "Brak elementów. Kliknij „Nowy”, aby dodać."
    COMPLETE_TEXT = "✔ Kompletne."
    INCOMPLETE_TEXT = "⚠ Niekompletne:"
    DELETE_QUESTION = "Usunąć „{title}”?"

    def __init__(self, library: Library, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._audio = AudioPlayer(self)
        self._current_id: str | None = None
        self._dirty = False  # czy są niezapisane zmiany
        self._loading = False  # True podczas wypełniania formularza
        self._selection_guard = False  # True podczas programowej zmiany zaznaczenia
        self._build_ui()

    # === Metody do nadpisania w klasach pochodnych =========================

    def _build_form(self) -> QWidget:
        raise NotImplementedError

    def _all_items(self) -> list:
        raise NotImplementedError

    def _get_item(self, item_id: str):
        raise NotImplementedError

    def _item_title(self, item) -> str:
        raise NotImplementedError

    def _item_problems(self, item) -> list[str]:
        raise NotImplementedError

    def _load_form(self, item) -> None:
        raise NotImplementedError

    def _read_form(self):
        """Tworzy obiekt z bieżącej zawartości formularza (z id = self._current_id)."""
        raise NotImplementedError

    def _store(self, item) -> None:
        raise NotImplementedError

    def _remove(self, item_id: str) -> None:
        raise NotImplementedError

    def _create_new_item(self):
        raise NotImplementedError

    def _confirm_before_save(self, item) -> bool:
        """Dodatkowe pytania przed zapisem. Domyślnie nic nie sprawdza."""
        return True

    # === Budowa interfejsu =================================================

    def _build_ui(self) -> None:
        back_button = QPushButton("← Menu główne")
        back_button.clicked.connect(self.request_back)
        title = QLabel(self.PAGE_TITLE)
        title_font = QFont(title.font())
        title_font.setPointSizeF(title_font.pointSizeF() * 1.6)
        title_font.setBold(True)
        title.setFont(title_font)
        header = QHBoxLayout()
        header.addWidget(back_button)
        header.addSpacing(16)
        header.addWidget(title)
        header.addStretch()

        # Lewa kolumna: wyszukiwarka, lista, przyciski.
        self._search = QLineEdit()
        self._search.setPlaceholderText("Szukaj…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_current_item_changed)
        self._new_button = QPushButton(self.NEW_BUTTON_TEXT)
        self._new_button.clicked.connect(self._add_new)
        self._delete_button = QPushButton("Usuń")
        self._delete_button.clicked.connect(self._delete_current)
        list_buttons = QHBoxLayout()
        list_buttons.addWidget(self._new_button)
        list_buttons.addWidget(self._delete_button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._search)
        left_layout.addWidget(self._list, stretch=1)
        left_layout.addLayout(list_buttons)

        # Prawa kolumna: przewijany formularz, stan i przyciski zapisu.
        self._form = self._build_form()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._form)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._save_button = QPushButton("Zapisz")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self.save)
        self._revert_button = QPushButton("Cofnij zmiany")
        self._revert_button.clicked.connect(self._revert)
        save_buttons = QHBoxLayout()
        save_buttons.addWidget(self._status_label, stretch=1)
        save_buttons.addWidget(self._revert_button)
        save_buttons.addWidget(self._save_button)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(scroll, stretch=1)
        right_layout.addLayout(save_buttons)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(splitter, stretch=1)

    # === Publiczne operacje ================================================

    def reload(self) -> None:
        """Odświeża listę i otwiera poprzednio wybrany (lub pierwszy) element."""
        self._refresh_list(self._current_id)
        current = self._list.currentItem()
        self._open_item(current.data(ID_ROLE) if current else None)

    def request_back(self) -> None:
        """Powrót do menu – najpierw pyta o niezapisane zmiany."""
        if self.maybe_leave():
            self._audio.stop()
            self.back_requested.emit()

    def maybe_leave(self) -> bool:
        """Zwraca True, jeśli można opuścić bieżący element (zmiany obsłużone)."""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Niezapisane zmiany",
            "Wprowadzone zmiany nie zostały zapisane. Zapisać je?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        if answer == QMessageBox.StandardButton.Discard:
            self._dirty = False
            return True
        return False  # Anuluj

    def save(self) -> bool:
        """Zapisuje bieżący element. Zwraca True, jeśli się udało."""
        if self._current_id is None:
            return True
        item = self._read_form()
        if not self._confirm_before_save(item):
            return False
        try:
            self._store(item)
        except OSError as error:
            QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać:\n{error}")
            return False
        self._dirty = False
        self._refresh_list(self._current_id)
        self._update_status()
        return True

    # === Lista =============================================================

    def _refresh_list(self, select_id: str | None) -> None:
        self._selection_guard = True
        self._list.clear()
        select_row = 0
        for row, item in enumerate(self._all_items()):
            problems = self._item_problems(item)
            title = self._item_title(item)
            list_item = QListWidgetItem(f"⚠ {title}" if problems else title)
            list_item.setData(ID_ROLE, item.id)
            if problems:
                list_item.setToolTip("Niekompletne:\n• " + "\n• ".join(problems))
            self._list.addItem(list_item)
            if item.id == select_id:
                select_row = row
        if self._list.count():
            self._list.setCurrentRow(select_row)
        self._apply_filter()
        self._selection_guard = False

    def _apply_filter(self) -> None:
        wanted = self._search.text().strip().casefold()
        for row in range(self._list.count()):
            list_item = self._list.item(row)
            list_item.setHidden(wanted not in list_item.text().casefold())

    def _on_current_item_changed(self, current: QListWidgetItem | None,
                                 previous: QListWidgetItem | None) -> None:
        if self._selection_guard:
            return
        new_id = current.data(ID_ROLE) if current else None
        if new_id == self._current_id:
            return
        if not self.maybe_leave():
            # Użytkownik anulował – przywracamy poprzednie zaznaczenie.
            self._selection_guard = True
            self._list.setCurrentItem(previous)
            self._selection_guard = False
            return
        self._open_item(new_id)

    def _open_item(self, item_id: str | None) -> None:
        self._audio.stop()
        item = self._get_item(item_id) if item_id else None
        self._current_id = item.id if item else None
        self._dirty = False
        self._form.setEnabled(item is not None)
        self._delete_button.setEnabled(item is not None)
        if item is not None:
            self._loading = True
            self._load_form(item)
            self._loading = False
        self._update_status()

    # === Formularz =========================================================

    def _on_form_changed(self) -> None:
        """Klasy pochodne podłączają tu sygnały zmian ze wszystkich pól."""
        if self._loading:
            return
        self._dirty = True
        self._update_status()

    def _update_status(self) -> None:
        self._save_button.setEnabled(self._dirty)
        self._revert_button.setEnabled(self._dirty)
        if self._current_id is None:
            self._status_label.setText(self.EMPTY_TEXT)
            return
        problems = self._item_problems(self._read_form())
        if problems:
            # Pokazujemy najwyżej 3 braki, żeby napis nie zasłaniał formularza.
            shown = problems[:3]
            if len(problems) > 3:
                shown.append(f"…i {len(problems) - 3} więcej")
            text = self.INCOMPLETE_TEXT + " " + "; ".join(shown)
            self._status_label.setStyleSheet("color: #b8860b;")
        else:
            text = self.COMPLETE_TEXT
            self._status_label.setStyleSheet("color: #2e8b57;")
        if self._dirty:
            text += "  (niezapisane zmiany)"
        self._status_label.setText(text)

    def _revert(self) -> None:
        self._open_item(self._current_id)

    # === Dodawanie i usuwanie ==============================================

    def _add_new(self) -> None:
        if not self.maybe_leave():
            return
        self._search.clear()
        item = self._create_new_item()
        self._store(item)
        self._refresh_list(item.id)
        self._open_item(item.id)

    def _delete_current(self) -> None:
        item = self._get_item(self._current_id) if self._current_id else None
        if item is None:
            return
        answer = QMessageBox.question(
            self,
            "Usuwanie",
            self.DELETE_QUESTION.format(title=self._item_title(item))
            + "\n\nTej operacji nie można cofnąć.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._remove(item.id)
        self._library.remove_unused_media()
        self._dirty = False
        self._current_id = None
        self.reload()

    def hideEvent(self, event) -> None:
        # Wywoływane przez Qt, gdy strona znika z ekranu – zatrzymujemy dźwięk.
        self._audio.stop()
        super().hideEvent(event)
