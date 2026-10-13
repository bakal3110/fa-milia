"""Edytor pytań finałowych."""

from PySide6.QtWidgets import QFormLayout, QLineEdit, QVBoxLayout, QWidget

from fa_milia.core.models import ContentKind, FinalQuestion
from fa_milia.ui.editors.editor_page import LibraryEditorPage
from fa_milia.ui.editors.question_editor import QuestionEditor


class FinalEditorPage(LibraryEditorPage):
    PAGE_TITLE = "Pytania finałowe"
    NEW_BUTTON_TEXT = "Nowe pytanie"
    EMPTY_TEXT = "Brak pytań finałowych. Kliknij „Nowe pytanie”, aby dodać."
    COMPLETE_TEXT = "✔ Pytanie kompletne – może zostać wylosowane do finału."
    INCOMPLETE_TEXT = "⚠ Pytanie niekompletne – nie zostanie użyte w finale. Brakuje:"
    DELETE_QUESTION = "Usunąć pytanie finałowe „{title}”?"
    USED_SUFFIX = "   · użyte"
    UNMARK_TEXT = "Oznacz jako nieużyte"

    def _build_form(self) -> QWidget:
        form = QWidget()
        layout = QVBoxLayout(form)

        self._category_edit = QLineEdit()
        self._category_edit.setPlaceholderText("np. Historia Polski")
        self._category_edit.textChanged.connect(self._on_form_changed)
        category_row = QFormLayout()
        category_row.addRow("Kategoria\n(pokazywana przed obstawianiem):", self._category_edit)
        layout.addLayout(category_row)

        self._question_editor = QuestionEditor(self._library, self._audio, "Pytanie finałowe")
        self._question_editor.changed.connect(self._on_form_changed)
        layout.addWidget(self._question_editor)
        layout.addStretch()
        return form

    def _all_items(self) -> list[FinalQuestion]:
        return self._library.sorted_finals()

    def _get_item(self, item_id: str) -> FinalQuestion | None:
        return self._library.finals.get(item_id)

    def _item_title(self, item: FinalQuestion) -> str:
        category = item.category or "(bez kategorii)"
        if item.question.kind == ContentKind.IMAGE:
            snippet = "[obraz]"
        elif item.question.kind == ContentKind.SOUND:
            snippet = "[dźwięk]"
        else:
            snippet = item.question.text.splitlines()[0] if item.question.text else ""
            if len(snippet) > 40:
                snippet = snippet[:40] + "…"
        return f"{category}: {snippet}" if snippet else category

    def _item_problems(self, item: FinalQuestion) -> list[str]:
        return self._library.final_problems(item)

    def _load_form(self, item: FinalQuestion) -> None:
        self._category_edit.setText(item.category)
        self._question_editor.set_question(item.question)

    def _read_form(self) -> FinalQuestion:
        return FinalQuestion(
            id=self._current_id,
            category=self._category_edit.text().strip(),
            question=self._question_editor.question(),
        )

    def _store(self, item: FinalQuestion) -> None:
        self._library.save_final(item)

    def _remove(self, item_id: str) -> None:
        self._library.delete_final(item_id)

    def _is_used(self, item_id: str) -> bool:
        return self._usage.is_final_used(item_id)

    def _unmark_used(self, item_id: str) -> None:
        self._usage.unmark_final(item_id)

    def _create_new_item(self) -> FinalQuestion:
        return FinalQuestion()
