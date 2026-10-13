"""Import / Eksport: pytania w formacie tekstowym oraz kopia zapasowa."""

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fa_milia.core.backup import BackupError, create_backup, restore_backup
from fa_milia.core.exporter import create_template, export_to_folder
from fa_milia.core.importer import (
    ConflictAction,
    ImportFailed,
    ImportItem,
    ImportPreview,
    Status,
    apply_import,
    extract_zip,
    scan_folder,
)
from fa_milia.core.library import Library
from fa_milia.ui.setup.players_page import page_title

STATUS_TEXT = {
    Status.OK: "✔ gotowe",
    Status.INCOMPLETE: "⚠ niekompletne – uzupełnisz w edytorze",
    Status.ERROR: "✖ błąd – nie zostanie dodane",
}
CONFLICT_CHOICES = [
    ("Zapisz jako kopię", ConflictAction.COPY),
    ("Zastąp istniejące", ConflictAction.REPLACE),
    ("Pomiń", ConflictAction.SKIP),
]


def _open_folder(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ---------------------------------------------------------------------------
# Podgląd importu
# ---------------------------------------------------------------------------


class ImportPreviewDialog(QDialog):
    """Pokazuje, co zostanie dodane, co jest niekompletne lub błędne, i pyta o konflikty."""

    def __init__(self, preview: ImportPreview, source: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Podgląd importu")
        self.resize(1000, 700)
        self._items = preview.items
        self._combos: dict[int, QComboBox] = {}

        intro = QLabel(f"Źródło: <b>{source}</b><br>Zaznacz, co chcesz dodać. "
                       "Niekompletne kategorie możesz dokończyć później w edytorze.")
        intro.setWordWrap(True)

        self._table = QTableWidget(len(self._items), 4)
        self._table.setHorizontalHeaderLabels(["Dodać?", "Nazwa", "Stan",
                                               "Ta nazwa już istnieje – co zrobić?"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # bez ramki „aktywnej komórki”
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (0, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        for row, item in enumerate(self._items):
            check = QTableWidgetItem()
            if item.status == Status.ERROR:
                check.setFlags(Qt.ItemFlag.NoItemFlags)
                check.setCheckState(Qt.CheckState.Unchecked)
            else:
                check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                check.setCheckState(Qt.CheckState.Checked)
            kind = "Pytanie finałowe" if item.is_final else "Kategoria"
            name = QTableWidgetItem(f"{kind}: {item.title}   ({item.source})")
            if item.problems:
                name.setToolTip("\n".join(item.problems))
            self._table.setItem(row, 0, check)
            self._table.setItem(row, 1, name)
            self._table.setItem(row, 2, QTableWidgetItem(STATUS_TEXT[item.status]))
            if item.conflict_id and item.status != Status.ERROR:
                combo = QComboBox()
                for label, action in CONFLICT_CHOICES:
                    combo.addItem(label, action)
                self._table.setCellWidget(row, 3, combo)
                self._combos[row] = combo
            else:
                self._table.setItem(row, 3, QTableWidgetItem("—"))

        all_problems = list(preview.problems)
        for item in self._items:
            all_problems += item.problems
        problems_label = QLabel(f"Uwagi i błędy ({len(all_problems)}):" if all_problems
                                else "Nie znaleziono żadnych błędów.")
        self._problems = QPlainTextEdit("\n".join(all_problems))
        self._problems.setReadOnly(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importuj zaznaczone")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            any(i.status != Status.ERROR for i in self._items))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self._table, stretch=3)
        layout.addWidget(problems_label)
        layout.addWidget(self._problems, stretch=2)
        layout.addWidget(buttons)

    def chosen(self) -> tuple[list[ImportItem], dict[int, ConflictAction]]:
        """Zaznaczone elementy i decyzje o konfliktach (indeksy w zwróconej liście)."""
        items = []
        actions = {}
        for row, item in enumerate(self._items):
            if self._table.item(row, 0).checkState() != Qt.CheckState.Checked:
                continue
            if row in self._combos:
                actions[len(items)] = self._combos[row].currentData()
            items.append(item)
        return items, actions


# ---------------------------------------------------------------------------
# Wybór elementów do eksportu
# ---------------------------------------------------------------------------


class ExportDialog(QDialog):
    def __init__(self, library: Library, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Eksport pytań")
        self.resize(800, 600)
        self._categories = self._checklist(
            [(c.id, c.name) for c in library.sorted_categories()])
        self._finals = self._checklist(
            [(f.id, f"{f.category}: {f.question.text[:50]}") for f in library.sorted_finals()])

        columns = QHBoxLayout()
        for title, widget in (("Kategorie", self._categories),
                              ("Pytania finałowe", self._finals)):
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            group_layout.addWidget(widget)
            select_row = QHBoxLayout()
            all_button = QPushButton("Zaznacz wszystkie")
            none_button = QPushButton("Odznacz wszystkie")
            # Domyślne argumenty lambdy „zamrażają” bieżącą listę (patrz menu_screen.py).
            all_button.clicked.connect(lambda _=False, w=widget: self._set_all(w, True))
            none_button.clicked.connect(lambda _=False, w=widget: self._set_all(w, False))
            select_row.addWidget(all_button)
            select_row.addWidget(none_button)
            group_layout.addLayout(select_row)
            columns.addWidget(group)

        info = QLabel("W wybranym miejscu powstanie nowy folder z plikami .txt, zdjęciami, "
                      "dźwiękami i instrukcją – w tym samym formacie, co przy imporcie.")
        info.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Wybierz miejsce i eksportuj…")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(columns, stretch=1)
        layout.addWidget(info)
        layout.addWidget(buttons)

    @staticmethod
    def _checklist(entries: list[tuple[str, str]]) -> QListWidget:
        widget = QListWidget()
        for item_id, label in entries:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, item_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            widget.addItem(item)
        return widget

    @staticmethod
    def _set_all(widget: QListWidget, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(widget.count()):
            widget.item(row).setCheckState(state)

    @staticmethod
    def _checked_ids(widget: QListWidget) -> list[str]:
        return [widget.item(row).data(Qt.ItemDataRole.UserRole) for row in range(widget.count())
                if widget.item(row).checkState() == Qt.CheckState.Checked]

    def chosen(self) -> tuple[list[str], list[str]]:
        return self._checked_ids(self._categories), self._checked_ids(self._finals)


# ---------------------------------------------------------------------------
# Strona
# ---------------------------------------------------------------------------


class TransferPage(QWidget):
    back_requested = Signal()
    library_changed = Signal()  # po imporcie
    backup_restored = Signal()  # po przywróceniu kopii – trzeba wczytać wszystko od nowa

    def __init__(self, library: Library, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library

        back_button = QPushButton("← Menu główne")
        back_button.clicked.connect(self.back_requested)
        header = QHBoxLayout()
        header.addWidget(back_button)
        header.addSpacing(16)
        header.addWidget(page_title("Import / Eksport"))
        header.addStretch()

        import_group = self._group(
            "Import pytań (pliki .txt z Notatnika)",
            "Wybierz folder z plikami .txt oraz zdjęciami i dźwiękami nazwanymi np. "
            "zwierzeta_2.jpg – albo plik .zip z takim folderem. Przed dodaniem zobaczysz "
            "podgląd i opis ewentualnych błędów.",
            [("Importuj z folderu…", self._import_folder),
             ("Importuj z pliku .zip…", self._import_zip)])
        export_group = self._group(
            "Eksport i szablon dla rodziny",
            "Eksport zapisuje wybrane kategorie i pytania finałowe w tym samym formacie. "
            "Pusty szablon to folder z plikiem WZOR.txt i prostą instrukcją "
            "JAK_DODAC_PYTANIA.txt – do przekazania osobom, które przygotują pytania.",
            [("Eksportuj…", self._export),
             ("Utwórz pusty szablon…", self._template)])
        backup_group = self._group(
            "Kopia zapasowa (dla prowadzącego)",
            "Jeden plik .zip ze wszystkimi danymi programu: kategoriami, finałami, zestawami, "
            "zdjęciami, dźwiękami, pamięcią wykorzystania, ustawieniami i zapisaną grą.",
            [("Utwórz kopię zapasową…", self._backup),
             ("Przywróć z kopii…", self._restore)])

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        column = QVBoxLayout()
        for group in (import_group, export_group, backup_group):
            column.addWidget(group)
        column.addWidget(self._status)
        column.addStretch()
        container = QWidget()
        container.setLayout(column)
        container.setMaximumWidth(900)
        center = QHBoxLayout()
        center.addStretch()
        center.addWidget(container, stretch=1)
        center.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(center, stretch=1)

    @staticmethod
    def _group(title: str, description: str, buttons: list) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        label = QLabel(description)
        label.setWordWrap(True)
        layout.addWidget(label)
        row = QHBoxLayout()
        for text, slot in buttons:
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        return group

    def request_back(self) -> None:
        self.back_requested.emit()

    def prepare(self) -> None:
        self._status.setText("")

    # --- Import ---------------------------------------------------------------

    def _import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder z pytaniami",
                                                  str(Path.home()))
        if folder:
            self._run_import(Path(folder), Path(folder).name)

    def _import_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik .zip z pytaniami",
                                              str(Path.home()), "Archiwum ZIP (*.zip *.ZIP)")
        if not path:
            return
        try:
            folder, temp = extract_zip(Path(path))
        except (ImportFailed, OSError) as error:
            QMessageBox.warning(self, "Import", str(error))
            return
        try:
            self._run_import(folder, Path(path).name)
        finally:
            temp.cleanup()  # kasujemy katalog tymczasowy z rozpakowanymi plikami

    def _run_import(self, folder: Path, source: str) -> None:
        try:
            preview = scan_folder(folder, self._library)
        except OSError as error:
            QMessageBox.warning(self, "Import", f"Nie udało się odczytać folderu:\n{error}")
            return
        dialog = ImportPreviewDialog(preview, source, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        items, actions = dialog.chosen()
        try:
            result = apply_import(self._library, items, actions)
        except OSError as error:
            QMessageBox.critical(self, "Import", f"Błąd podczas zapisu:\n{error}")
            return
        self._status.setText(f"Import zakończony: dodano {result.added}, zastąpiono "
                             f"{result.replaced}, pominięto {result.skipped}.")
        self.library_changed.emit()

    # --- Eksport ------------------------------------------------------------------

    def _export(self) -> None:
        dialog = ExportDialog(self._library, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        category_ids, final_ids = dialog.chosen()
        if not category_ids and not final_ids:
            QMessageBox.information(self, "Eksport", "Nic nie zaznaczono.")
            return
        parent = QFileDialog.getExistingDirectory(self, "Gdzie zapisać folder z pytaniami?",
                                                  str(Path.home()))
        if not parent:
            return
        try:
            folder = export_to_folder(self._library, category_ids, final_ids, Path(parent))
        except OSError as error:
            QMessageBox.critical(self, "Eksport", f"Nie udało się zapisać:\n{error}")
            return
        self._status.setText(f"Zapisano: {folder}")
        _open_folder(folder)

    def _template(self) -> None:
        parent = QFileDialog.getExistingDirectory(self, "Gdzie utworzyć szablon?", str(Path.home()))
        if not parent:
            return
        try:
            folder = create_template(Path(parent))
        except OSError as error:
            QMessageBox.critical(self, "Szablon", f"Nie udało się zapisać:\n{error}")
            return
        self._status.setText(f"Utworzono szablon: {folder}")
        _open_folder(folder)

    # --- Kopia zapasowa ----------------------------------------------------------

    def _backup(self) -> None:
        default = Path.home() / f"fa-milia-kopia-{date.today().isoformat()}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz kopię zapasową", str(default),
                                              "Archiwum ZIP (*.zip)")
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        try:
            count = create_backup(self._library.data_dir, target)
        except OSError as error:
            QMessageBox.critical(self, "Kopia zapasowa", f"Nie udało się zapisać:\n{error}")
            return
        self._status.setText(f"Zapisano kopię zapasową ({count} plików): {target}")

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz kopię zapasową", str(Path.home()),
                                              "Archiwum ZIP (*.zip *.ZIP)")
        if not path:
            return
        answer = QMessageBox.warning(
            self, "Przywracanie kopii",
            "Wszystkie obecne dane programu (kategorie, finały, zestawy, media, ustawienia, "
            "zapisana gra) zostaną zastąpione zawartością kopii.\n\n"
            "Obecne dane nie znikną od razu – zostaną odłożone do folderu "
            "„fa-milia-przed-przywroceniem” obok katalogu danych.\n\nKontynuować?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            previous = restore_backup(self._library.data_dir, Path(path))
        except (BackupError, OSError) as error:
            QMessageBox.critical(self, "Przywracanie kopii", str(error))
            return
        self.backup_restored.emit()
        self._status.setText(f"Przywrócono kopię. Poprzednie dane: {previous}")
