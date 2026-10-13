"""Okno ustawień: monitor ekranu gry, pełny ekran, skalowanie, skróty klawiszowe."""

from dataclasses import replace

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fa_milia.config import SHORTCUTS
from fa_milia.core.game_state import RoundState
from fa_milia.core.models import Category
from fa_milia.core.settings import MAX_SCALE, MIN_SCALE, Settings
from fa_milia.core.sounds import SOUND_EVENTS, find_sound
from fa_milia.ui.game.board_widget import BoardWidget
from fa_milia.ui.game.host_panel import PlayerRow, host_style
from fa_milia.ui.screens import describe_screen
from fa_milia.ui.sound_effects import SoundEffects

PREVIEW_CATEGORIES = ["Zwierzęta", "Polska", "Bajki i baśnie", "Kuchnia", "Kosmos", "Sport"]


def _scale_slider() -> QSlider:
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(MIN_SCALE, MAX_SCALE)
    slider.setSingleStep(5)
    slider.setPageStep(25)
    slider.setTickInterval(25)
    slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    return slider


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, sounds_dir: Path,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sounds_dir = sounds_dir
        self._effects = SoundEffects(sounds_dir, self)
        self.setWindowTitle("Ustawienia")
        self.resize(900, 640)
        self._settings = settings
        self._identify_windows: list[QLabel] = []

        tabs = QTabWidget()
        tabs.addTab(self._build_screens_tab(), "Ekrany")
        tabs.addTab(self._build_scaling_tab(), "Skalowanie")
        tabs.addTab(self._build_timer_sound_tab(), "Timer i dźwięk")
        tabs.addTab(self._build_shortcuts_tab(), "Skróty klawiszowe")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    # --- Zakładka „Ekrany” -------------------------------------------------

    def _build_screens_tab(self) -> QWidget:
        self._screen_combo = QComboBox()
        self._screen_combo.addItem("Automatycznie – monitor inny niż ten z oknem prowadzącego", None)
        for screen in QGuiApplication.screens():
            self._screen_combo.addItem(describe_screen(screen), screen.name())
        saved = self._settings.game_screen
        if saved and self._screen_combo.findData(saved) < 0:
            # Zapisany monitor nie jest teraz podłączony – pokazujemy go mimo to.
            self._screen_combo.addItem(f"{saved} (niepodłączony)", saved)
        self._screen_combo.setCurrentIndex(max(0, self._screen_combo.findData(saved)))

        identify = QPushButton("Pokaż nazwy na monitorach")
        identify.clicked.connect(self._identify_screens)
        screen_row = QHBoxLayout()
        screen_row.addWidget(self._screen_combo, stretch=1)
        screen_row.addWidget(identify)

        count = len(QGuiApplication.screens())
        if count < 2:
            info_text = ("Wykryto 1 monitor – gra będzie działać w trybie jednoekranowym, "
                         "a panel prowadzącego otworzy się jako nakładka (klawisz F2).")
        else:
            info_text = (f"Wykryto monitory: {count}. Ekran gry otworzy się na wybranym "
                         "monitorze, a panel prowadzącego zostanie w głównym oknie.")
        info = QLabel(info_text)
        info.setWordWrap(True)

        self._fullscreen = QCheckBox("Pełny ekran (główne okno przy starcie i ekran gry)")
        self._fullscreen.setChecked(self._settings.fullscreen)

        tab = QWidget()
        layout = QFormLayout(tab)
        layout.addRow("Ekran gry:", screen_row)
        layout.addRow("", info)
        layout.addRow("", self._fullscreen)
        return tab

    def _identify_screens(self) -> None:
        """Na każdym monitorze na chwilę wyświetla jego nazwę."""
        for screen in QGuiApplication.screens():
            label = QLabel(screen.name())
            label.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            label.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background: #0b1a4a; color: #f2c94c; font-size: 96pt;"
                                "font-weight: bold;")
            label.setScreen(screen)
            geometry = screen.geometry()
            label.setGeometry(geometry.x() + geometry.width() // 4,
                              geometry.y() + geometry.height() // 3,
                              geometry.width() // 2, geometry.height() // 3)
            label.show()
            self._identify_windows.append(label)
        QTimer.singleShot(2500, self._close_identify_windows)

    def _close_identify_windows(self) -> None:
        for label in self._identify_windows:
            label.close()
            label.deleteLater()
        self._identify_windows = []

    # --- Zakładka „Skalowanie” ---------------------------------------------

    def _build_scaling_tab(self) -> QWidget:
        # Ekran gry: suwak + podgląd planszy.
        self._game_slider = _scale_slider()
        self._game_slider.setValue(self._settings.game_scale)
        self._game_value = QLabel()
        self._board_preview = BoardWidget()
        self._board_preview.set_round(
            RoundState(1, [Category(name=name) for name in PREVIEW_CATEGORIES]), clickable=False)
        self._board_preview.setFixedSize(480, 270)
        self._game_slider.valueChanged.connect(self._update_game_preview)

        game_group = QGroupBox("Ekran gry (telewizor / rzutnik) – wielkość napisów")
        game_layout = QVBoxLayout(game_group)
        game_row = QHBoxLayout()
        game_row.addWidget(self._game_slider, stretch=1)
        game_row.addWidget(self._game_value)
        game_layout.addLayout(game_row)
        game_layout.addWidget(self._board_preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        game_hint = QLabel("Tekst nigdy nie wychodzi poza pole – przy dużej skali "
                           "długie napisy i tak zostaną zmniejszone, żeby się zmieściły.")
        game_hint.setStyleSheet("color: gray;")
        game_hint.setWordWrap(True)
        game_layout.addWidget(game_hint)

        # Panel prowadzącego: suwak + podgląd wiersza zawodnika.
        self._host_slider = _scale_slider()
        self._host_slider.setValue(self._settings.host_scale)
        self._host_value = QLabel()
        self._host_preview = QWidget()
        self._host_preview.setObjectName("HostPanel")  # żeby działały style panelu
        self._host_preview.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        preview_row = PlayerRow(0)
        preview_row.update_row("Ania", 1200, True, None, 300, last_correct=True)
        QVBoxLayout(self._host_preview).addWidget(preview_row)
        self._host_slider.valueChanged.connect(self._update_host_preview)

        host_group = QGroupBox("Panel prowadzącego (laptop) – wielkość napisów i przycisków")
        host_layout = QVBoxLayout(host_group)
        host_row = QHBoxLayout()
        host_row.addWidget(self._host_slider, stretch=1)
        host_row.addWidget(self._host_value)
        host_layout.addLayout(host_row)
        host_layout.addWidget(self._host_preview)

        self._update_game_preview()
        self._update_host_preview()

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(game_group)
        layout.addWidget(host_group)
        layout.addStretch()
        return tab

    def _update_game_preview(self) -> None:
        value = self._game_slider.value()
        self._game_value.setText(f"{value}%")
        self._board_preview.set_scale(value / 100)

    def _update_host_preview(self) -> None:
        value = self._host_slider.value()
        self._host_value.setText(f"{value}%")
        self._host_preview.setStyleSheet(host_style(value / 100))

    # --- Zakładka „Timer i dźwięk” ------------------------------------------

    def _build_timer_sound_tab(self) -> QWidget:
        self._timer_enabled = QCheckBox("Włącz timer (odliczanie widoczne na ekranie gry)")
        self._timer_enabled.setChecked(self._settings.timer_enabled)
        self._question_seconds = QSpinBox()
        self._question_seconds.setRange(5, 600)
        self._question_seconds.setSuffix(" s")
        self._question_seconds.setValue(self._settings.question_seconds)
        self._final_seconds = QSpinBox()
        self._final_seconds.setRange(5, 600)
        self._final_seconds.setSuffix(" s")
        self._final_seconds.setValue(self._settings.final_seconds)
        self._timer_enabled.toggled.connect(self._question_seconds.setEnabled)
        self._timer_enabled.toggled.connect(self._final_seconds.setEnabled)
        self._question_seconds.setEnabled(self._settings.timer_enabled)
        self._final_seconds.setEnabled(self._settings.timer_enabled)

        timer_group = QGroupBox("Timer")
        timer_form = QFormLayout(timer_group)
        timer_form.addRow(self._timer_enabled)
        timer_form.addRow("Czas na zwykłe pytanie i bonus:", self._question_seconds)
        timer_form.addRow("Czas na pytanie finałowe:", self._final_seconds)

        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(self._settings.volume)
        self._volume_label = QLabel()
        self._volume.valueChanged.connect(self._on_volume_changed)
        test_button = QPushButton("▶ Próbka")
        test_button.setToolTip("Odtwarza dźwięk „bonus” z wybraną głośnością")
        test_button.clicked.connect(lambda: self._effects.play("bonus"))
        volume_row = QHBoxLayout()
        volume_row.addWidget(self._volume, stretch=1)
        volume_row.addWidget(self._volume_label)
        volume_row.addWidget(test_button)

        open_folder = QPushButton("Otwórz folder dźwięków")
        open_folder.clicked.connect(self._open_sounds_folder)
        self._sound_status = QLabel()
        self._sound_status.setWordWrap(True)
        self._sound_status.setTextFormat(Qt.TextFormat.RichText)
        refresh = QPushButton("Odśwież listę")
        refresh.clicked.connect(self._update_sound_status)

        sound_group = QGroupBox("Dźwięk")
        sound_layout = QVBoxLayout(sound_group)
        sound_form = QFormLayout()
        sound_form.addRow("Głośność:", volume_row)
        sound_layout.addLayout(sound_form)
        buttons = QHBoxLayout()
        buttons.addWidget(open_folder)
        buttons.addWidget(refresh)
        buttons.addStretch()
        sound_layout.addLayout(buttons)
        sound_layout.addWidget(self._sound_status)

        self._on_volume_changed()
        self._update_sound_status()

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(timer_group)
        layout.addWidget(sound_group)
        layout.addStretch()
        return tab

    def _on_volume_changed(self) -> None:
        self._volume_label.setText(f"{self._volume.value()}%")
        self._effects.set_volume(self._volume.value() / 100)

    def _open_sounds_folder(self) -> None:
        self._sounds_dir.mkdir(parents=True, exist_ok=True)
        # Otwiera folder w menedżerze plików (Dolphin w KDE).
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._sounds_dir)))

    def _update_sound_status(self) -> None:
        lines = [f"Folder: <code>{self._sounds_dir}</code><br>"]
        for name, description in SOUND_EVENTS.items():
            path = find_sound(self._sounds_dir, name)
            mark = f"✔ {path.name}" if path else "– brak pliku (cisza)"
            lines.append(f"<b>{name}</b> – {description}: {mark}")
        self._sound_status.setText("<br>".join(lines))

    # --- Zakładka „Skróty klawiszowe” --------------------------------------

    def _build_shortcuts_tab(self) -> QWidget:
        table = QTableWidget(len(SHORTCUTS), 2)
        table.setHorizontalHeaderLabels(["Klawisz", "Działanie"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row, (key, description) in enumerate(SHORTCUTS):
            table.setItem(row, 0, QTableWidgetItem(key))
            table.setItem(row, 1, QTableWidgetItem(description))
        table.resizeColumnToContents(0)
        return table

    # --- Wynik ---------------------------------------------------------------

    def result_settings(self) -> Settings:
        """Ustawienia z formularza (pozostałe pola bez zmian)."""
        # replace tworzy kopię dataclass ze zmienionymi wybranymi polami.
        settings = replace(
            self._settings,
            game_screen=self._screen_combo.currentData(),
            fullscreen=self._fullscreen.isChecked(),
            game_scale=self._game_slider.value(),
            host_scale=self._host_slider.value(),
            timer_enabled=self._timer_enabled.isChecked(),
            question_seconds=self._question_seconds.value(),
            final_seconds=self._final_seconds.value(),
            volume=self._volume.value(),
        )
        return settings.normalized()

    def done(self, result: int) -> None:
        self._close_identify_windows()
        self._effects.stop_all()
        super().done(result)
