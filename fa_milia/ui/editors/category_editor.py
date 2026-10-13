"""Edytor kategorii."""

from PySide6.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from fa_milia.config import ROUND_VALUES, ROW_COUNT
from fa_milia.core.models import Category
from fa_milia.ui.editors.editor_page import LibraryEditorPage
from fa_milia.ui.editors.question_editor import QuestionEditor


def _row_title(row: int) -> str:
    """Np. „Pytanie 1 – najłatwiejsze (runda 1: 100 pkt, runda 2: 200 pkt)”."""
    hint = ""
    if row == 1:
        hint = " – najłatwiejsze"
    elif row == ROW_COUNT:
        hint = " – najtrudniejsze"
    value_1 = ROUND_VALUES[1][row - 1]
    value_2 = ROUND_VALUES[2][row - 1]
    return f"Pytanie {row}{hint}   (runda 1: {value_1} pkt, runda 2: {value_2} pkt)"


class CategoryEditorPage(LibraryEditorPage):
    PAGE_TITLE = "Kategorie"
    NEW_BUTTON_TEXT = "Nowa kategoria"
    EMPTY_TEXT = "Brak kategorii. Kliknij „Nowa kategoria”, aby dodać."
    COMPLETE_TEXT = "✔ Kategoria kompletna – można ją wybrać do gry."
    INCOMPLETE_TEXT = "⚠ Kategoria niekompletna – nie da się jej wybrać do gry. Brakuje:"
    DELETE_QUESTION = "Usunąć kategorię „{title}” razem z jej pytaniami i plikami?"

    def _build_form(self) -> QWidget:
        form = QWidget()
        layout = QVBoxLayout(form)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("np. Zwierzęta")
        self._name_edit.textChanged.connect(self._on_form_changed)
        name_row = QFormLayout()
        name_row.addRow("Nazwa kategorii:", self._name_edit)
        layout.addLayout(name_row)

        self._question_editors: list[QuestionEditor] = []
        for row in range(1, ROW_COUNT + 1):
            editor = QuestionEditor(self._library, self._audio, _row_title(row))
            editor.changed.connect(self._on_form_changed)
            layout.addWidget(editor)
            self._question_editors.append(editor)
        layout.addStretch()
        return form

    def _all_items(self) -> list[Category]:
        return self._library.sorted_categories()

    def _get_item(self, item_id: str) -> Category | None:
        return self._library.categories.get(item_id)

    def _item_title(self, item: Category) -> str:
        return item.name or "(bez nazwy)"

    def _item_problems(self, item: Category) -> list[str]:
        return self._library.category_problems(item)

    def _load_form(self, item: Category) -> None:
        self._name_edit.setText(item.name)
        # zip łączy dwie listy w pary: (edytor 1, pytanie 1), (edytor 2, pytanie 2)…
        for editor, question in zip(self._question_editors, item.questions):
            editor.set_question(question)

    def _read_form(self) -> Category:
        return Category(
            id=self._current_id,
            name=self._name_edit.text().strip(),
            questions=[editor.question() for editor in self._question_editors],
        )

    def _store(self, item: Category) -> None:
        self._library.save_category(item)

    def _remove(self, item_id: str) -> None:
        self._library.delete_category(item_id)

    def _create_new_item(self) -> Category:
        return Category(name=self._library.unique_category_name("Nowa kategoria"))

    def _confirm_before_save(self, item: Category) -> bool:
        if item.name and self._library.category_name_taken(item.name, except_id=item.id):
            answer = QMessageBox.question(
                self,
                "Powtórzona nazwa",
                f"Istnieje już kategoria o nazwie „{item.name}”.\nZapisać mimo to?",
            )
            return answer == QMessageBox.StandardButton.Yes
        return True
