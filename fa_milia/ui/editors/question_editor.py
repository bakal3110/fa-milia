"""Widżet do edycji jednego pytania (rodzaj, treść, plik, odpowiedź)."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)

from fa_milia.core.library import Library
from fa_milia.core.models import KIND_EXTENSIONS, KIND_LABELS, ContentKind, Question
from fa_milia.ui.audio import AudioPlayer

PREVIEW_WIDTH = 260
PREVIEW_HEIGHT = 160


def _file_filter(kind: ContentKind) -> str:
    """Filtr dla okna wyboru pliku, np. "Obrazy (*.jpg *.JPG …)"."""
    patterns = []
    for extension in KIND_EXTENSIONS[kind]:
        patterns += [f"*{extension}", f"*{extension.upper()}"]
    label = "Obrazy" if kind == ContentKind.IMAGE else "Dźwięki"
    return f"{label} ({' '.join(patterns)})"


class QuestionEditor(QGroupBox):
    """Pola jednego pytania. Wysyła `changed`, gdy użytkownik coś zmieni."""

    changed = Signal()

    def __init__(self, library: Library, audio: AudioPlayer, title: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._library = library
        self._audio = audio
        # Nazwa pliku w katalogu media/. Pamiętamy ją także po zmianie rodzaju
        # na „Tekst”, żeby powrót do „Obraz” nie gubił wybranego pliku.
        self._media: str | None = None

        self._kind_combo = QComboBox()
        for kind in ContentKind:
            # Drugi argument addItem to „dane” elementu – zapisujemy wartość tekstową.
            self._kind_combo.addItem(KIND_LABELS[kind], kind.value)

        self._text_label = QLabel()
        # Etykieta zmienia treść zależnie od rodzaju pytania, więc od razu
        # rezerwujemy miejsce na dłuższy wariant – inaczej tekst bywa ucięty.
        metrics = self._text_label.fontMetrics()
        self._text_label.setMinimumWidth(metrics.horizontalAdvance("Treść pytania:  "))
        self._text_edit = QPlainTextEdit()
        self._text_edit.setFixedHeight(64)
        self._text_edit.setTabChangesFocus(True)  # Tab przechodzi do następnego pola

        self._choose_button = QPushButton("Wybierz plik…")
        self._media_label = QLabel()
        self._play_button = QPushButton("▶ Odtwórz")
        self._stop_button = QPushButton("■ Zatrzymaj")
        self._media_row = QWidget()
        media_layout = QHBoxLayout(self._media_row)
        media_layout.setContentsMargins(0, 0, 0, 0)
        media_layout.addWidget(self._choose_button)
        media_layout.addWidget(self._media_label, stretch=1)
        media_layout.addWidget(self._play_button)
        media_layout.addWidget(self._stop_button)

        self._preview = QLabel()
        self._preview.setFixedSize(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet("background: #20242c; color: #ddd; border-radius: 4px;")

        self._answer_edit = QPlainTextEdit()
        self._answer_edit.setFixedHeight(46)
        self._answer_edit.setTabChangesFocus(True)

        self._form = QFormLayout(self)
        self._form.addRow("Rodzaj:", self._kind_combo)
        self._form.addRow(self._text_label, self._text_edit)
        self._form.addRow("Plik:", self._media_row)
        self._form.addRow("", self._preview)
        self._form.addRow("Odpowiedź:", self._answer_edit)

        self._kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        self._text_edit.textChanged.connect(self.changed)
        self._answer_edit.textChanged.connect(self.changed)
        self._choose_button.clicked.connect(self._choose_file)
        self._play_button.clicked.connect(self._play)
        self._stop_button.clicked.connect(self._audio.stop)

        self._update_kind_widgets()

    # --- Wymiana danych z resztą programu ----------------------------------

    def set_question(self, question: Question) -> None:
        """Wypełnia pola danymi pytania."""
        self._media = question.media
        # blockSignals: podczas wypełniania nie chcemy sygnałów „changed”.
        for widget in (self._kind_combo, self._text_edit, self._answer_edit):
            widget.blockSignals(True)
        self._kind_combo.setCurrentIndex(self._kind_combo.findData(question.kind.value))
        self._text_edit.setPlainText(question.text)
        self._answer_edit.setPlainText(question.answer)
        for widget in (self._kind_combo, self._text_edit, self._answer_edit):
            widget.blockSignals(False)
        self._update_kind_widgets()

    def question(self) -> Question:
        """Tworzy obiekt Question z bieżącej zawartości pól."""
        kind = self._current_kind()
        media = self._media
        # Plik zapisujemy tylko wtedy, gdy pasuje do wybranego rodzaju.
        if media is None or not media.lower().endswith(KIND_EXTENSIONS[kind]):
            media = None
        return Question(
            kind=kind,
            text=self._text_edit.toPlainText().strip(),
            media=media,
            answer=self._answer_edit.toPlainText().strip(),
        )

    # --- Obsługa zdarzeń ---------------------------------------------------

    def _current_kind(self) -> ContentKind:
        return ContentKind(self._kind_combo.currentData())

    def _on_kind_changed(self) -> None:
        self._audio.stop()
        self._update_kind_widgets()
        self.changed.emit()

    def _choose_file(self) -> None:
        kind = self._current_kind()
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, "Wybierz plik", str(Path.home()), _file_filter(kind)
        )
        if not path:  # użytkownik zamknął okno bez wyboru
            return
        try:
            self._media = self._library.import_media(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Nie udało się dodać pliku", str(error))
            return
        self._update_kind_widgets()
        self.changed.emit()

    def _play(self) -> None:
        media = self.question().media
        if media:
            self._audio.play(self._library.media_path(media))

    # --- Wygląd zależny od rodzaju pytania --------------------------------

    def _update_kind_widgets(self) -> None:
        kind = self._current_kind()
        has_media = kind != ContentKind.TEXT

        if has_media:
            self._text_label.setText("Podpis\n(opcjonalny):")
            self._text_edit.setPlaceholderText("Tekst wyświetlany pod obrazem / przy dźwięku")
        else:
            self._text_label.setText("Treść pytania:")
            self._text_edit.setPlaceholderText("")

        # setRowVisible ukrywa cały wiersz formularza (etykietę i pole).
        self._form.setRowVisible(self._media_row, has_media)
        self._form.setRowVisible(self._preview, kind == ContentKind.IMAGE)
        self._play_button.setVisible(kind == ContentKind.SOUND)
        self._stop_button.setVisible(kind == ContentKind.SOUND)

        media = self.question().media  # None, jeśli plik nie pasuje do rodzaju
        if media is None:
            self._media_label.setText("(nie wybrano pliku)")
            self._play_button.setEnabled(False)
            self._preview.setPixmap(QPixmap())
            self._preview.setText("brak obrazu")
            return

        path = self._library.media_path(media)
        display_name = Library.display_media_name(media)
        if not path.is_file():
            self._media_label.setText(f"⚠ {display_name} – plik nie istnieje")
            self._play_button.setEnabled(False)
            self._preview.setText("brak pliku")
            return

        self._media_label.setText(display_name)
        self._play_button.setEnabled(True)
        if kind == ContentKind.IMAGE:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._preview.setText("nie można wyświetlić obrazu")
            else:
                self._preview.setPixmap(pixmap.scaled(
                    PREVIEW_WIDTH, PREVIEW_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
