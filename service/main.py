#!/usr/bin/env python3
"""
Image Compression Application
Main application for compressing images with configurable parameters.
"""

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import Event

from PySide6.QtCore import QStandardPaths, Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from service.compression_profiles import (
    CompressionProfile,
    load_profiles,
    save_profiles,
)
from service.file_utils import format_timedelta

# Import our modules
from service.image_compression import (
    ImageCompressor,
    save_compression_settings,
)
from service.parameters_defaults import GLOBAL_DEFAULTS
from service.profile_panel import ProfilePanel
from service.translator import LANGUAGES, get_language, set_language, tr


class CompressionWorker(QThread):
    """Worker thread for image compression to avoid blocking the UI."""

    progress_updated = Signal(int, int)  # current, total
    status_updated = Signal(str)
    log_updated = Signal(str)
    compression_finished = Signal(dict)  # stats
    error_occurred = Signal(str)

    def __init__(
        self,
        compressor: ImageCompressor,
        input_dir: Path,
        output_dir: Path,
        compression_settings: dict,
        profiles: list[CompressionProfile],
    ) -> None:
        super().__init__()
        self.compressor = compressor
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.compression_settings = compression_settings
        self.profiles = profiles
        self._stop_event = Event()
        self.cancelled = False

    def run(self) -> None:
        """Run the compression process."""
        try:
            self.status_updated.emit(tr("Starting compression..."))
            start_time = datetime.now()

            # Process the directory
            (
                total_files,
                compressed_files,
                compressed_paths,
                failed_files,
                profile_results,
            ) = self.compressor.process_directory(
                self.input_dir,
                self.output_dir,
                self.profiles,
                progress_callback=lambda current, total: self.progress_updated.emit(current, total),
                status_callback=lambda msg: self.status_updated.emit(msg),
                log_callback=lambda msg: self.log_updated.emit(msg),
                num_workers=1,
                stop_event=self._stop_event,
            )

            # Get compression statistics
            failed_paths = [f for f, _ in failed_files]
            stats = self.compressor.get_compression_stats(
                self.input_dir,
                self.output_dir,
                compressed_paths,
                failed_paths,
            )
            stats["total_files"] = total_files
            stats["compressed_files"] = compressed_files
            stats["failed_files_count"] = len(failed_files)

            elapsed = datetime.now() - start_time
            stats["conversion_time"] = format_timedelta(elapsed)

            # Prepare data for settings file
            image_pairs = profile_results
            self.status_updated.emit(tr("Saving compression settings..."))

            # Save compression settings
            if image_pairs or failed_files:
                save_compression_settings(
                    self.output_dir,
                    self.compression_settings,
                    image_pairs,
                    stats,
                    failed_files,
                    stats["conversion_time"],
                )

            if self._stop_event.is_set():
                self.cancelled = True
                self.status_updated.emit(tr("Compression aborted by user"))
            else:
                self.status_updated.emit(
                    tr("Compression completed! {compressed}/{total} files compressed. {failed} failed.").format(
                        compressed=compressed_files,
                        total=total_files,
                        failed=len(failed_files),
                    )
                )
            self.compression_finished.emit(stats)

        except Exception as e:
            self.error_occurred.emit(tr("Compression error: {error}").format(error=e))

    def stop(self) -> None:
        """Request the worker to stop."""
        self._stop_event.set()


class MainWindow(QMainWindow):
    """Main application window for image compression."""

    def __init__(self) -> None:
        super().__init__()
        self.compression_worker: CompressionWorker | None = None
        self.output_directory: Path | None = None
        self.input_directory: Path | None = None
        self.progress_start_time: datetime | None = None

        self.setup_ui()
        self.setup_connections()
        self.update_translations()

        # Set window properties
        self.setWindowTitle(tr("Image Compression Tool"))
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel[class="tooltip"] {
                color: #666;
                font-style: italic;
                font-size: 11px;
            }
        """)

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_label = QLabel(tr("Language:"))
        self.language_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.language_combo.addItem(name, code)
        # Select system language by default
        current_code = get_language()
        index = self.language_combo.findData(current_code)
        if index != -1:
            self.language_combo.setCurrentIndex(index)
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.language_combo)
        main_layout.addLayout(lang_layout)

        # Title
        self.title_label = QLabel(tr("Image Compression Tool"))
        self.title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        main_layout.addWidget(self.title_label)

        # Input section
        self.input_group = QGroupBox(tr("Input Settings"))
        input_layout = QVBoxLayout(self.input_group)

        # Input directory selection
        input_dir_layout = QHBoxLayout()
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setPlaceholderText(tr("No input directory selected"))
        self.input_dir_edit.setStyleSheet(
            "padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.select_input_btn = QPushButton(tr("Select Input Directory"))
        self.select_input_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)

        input_dir_layout.addWidget(self.input_dir_edit, 1)
        input_dir_layout.addWidget(self.select_input_btn)
        input_layout.addLayout(input_dir_layout)

        # Output directory selection
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText(tr("No output directory selected"))
        self.output_dir_edit.setStyleSheet(
            "padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.regen_output_btn = QToolButton()
        self.regen_output_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.regen_output_btn.setToolTip(tr("Regenerate output directory name"))
        self.regen_output_btn.clicked.connect(self.regenerate_output_directory)
        self.select_output_btn = QPushButton(tr("Select Output Directory"))
        self.select_output_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)

        output_dir_layout.addWidget(self.output_dir_edit, 1)
        output_dir_layout.addWidget(self.regen_output_btn)
        output_dir_layout.addWidget(self.select_output_btn)
        input_layout.addLayout(output_dir_layout)

        unsupported_dir_layout = QHBoxLayout()
        self.unsupported_dir_edit = QLineEdit()
        self.unsupported_dir_edit.setPlaceholderText(tr("No unsupported directory selected"))
        self.unsupported_dir_edit.setStyleSheet(
            "padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.unsupported_dir_edit.setVisible(False)
        self.select_unsupported_btn = QPushButton(tr("Select Unsupported Folder"))
        self.select_unsupported_btn.setStyleSheet(self.select_output_btn.styleSheet())
        self.select_unsupported_btn.clicked.connect(self.select_unsupported_directory)
        self.select_unsupported_btn.setVisible(False)
        unsupported_dir_layout.addWidget(self.unsupported_dir_edit, 1)
        unsupported_dir_layout.addWidget(self.select_unsupported_btn)
        input_layout.addLayout(unsupported_dir_layout)

        self.preserve_structure_cb = QCheckBox(tr("Preserve folder structure"))
        self.preserve_structure_cb.setChecked(GLOBAL_DEFAULTS["preserve_structure"])
        input_layout.addWidget(self.preserve_structure_cb)

        self.copy_unsupported_cb = QCheckBox(tr("Copy unsupported files"))
        self.copy_unsupported_cb.setChecked(GLOBAL_DEFAULTS["copy_unsupported"])
        self.copy_unsupported_cb.stateChanged.connect(self.update_copy_unsupported_state)
        input_layout.addWidget(self.copy_unsupported_cb)

        self.copy_unsupported_separate_cb = QCheckBox(tr("Copy unsupported files to separate folder"))
        self.copy_unsupported_separate_cb.setChecked(GLOBAL_DEFAULTS["copy_unsupported_to_dir"])
        self.copy_unsupported_separate_cb.stateChanged.connect(self.update_copy_unsupported_state)
        input_layout.addWidget(self.copy_unsupported_separate_cb)

        self.update_copy_unsupported_state()

        main_layout.addWidget(self.input_group)

        # Create scrollable area for compression settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        scroll_area.setContentsMargins(0, 0, 0, 0)

        # Compression settings container
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)

        # Reset settings button at top of settings panel
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 10, 0)
        header_layout.addStretch()

        self.save_profiles_btn = QPushButton(tr("Save Profiles"))
        self.save_profiles_btn.clicked.connect(self.save_profiles)
        header_layout.addWidget(self.save_profiles_btn)

        self.load_profiles_btn = QPushButton(tr("Load Profiles"))
        self.load_profiles_btn.clicked.connect(self.load_profiles)
        header_layout.addWidget(self.load_profiles_btn)

        self.add_profile_btn = QPushButton(tr("Add Profile"))
        self.add_profile_btn.clicked.connect(self.add_profile_panel)
        header_layout.addWidget(self.add_profile_btn)

        self.reset_btn = QPushButton(tr("Reset Settings"))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: 1px solid #b3b3b3;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #d5d5d5;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
        header_layout.addWidget(self.reset_btn)
        self.settings_layout.addLayout(header_layout)

        self.profiles_layout = QVBoxLayout()
        self.settings_layout.addLayout(self.profiles_layout)

        self.profile_panels: list[ProfilePanel] = []
        self.add_profile_panel()

        scroll_area.setWidget(self.settings_container)
        main_layout.addWidget(scroll_area)

        # Progress section
        self.progress_group = QGroupBox(tr("Progress"))
        progress_layout = QVBoxLayout(self.progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel(tr("Ready to compress images"))
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        progress_layout.addWidget(self.status_label)

        # Action buttons
        button_layout = QHBoxLayout()

        self.compress_btn = QPushButton(tr("Start Compression"))
        self.compress_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.compress_btn_default_style = self.compress_btn.styleSheet()
        self.abort_btn_style = """
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """
        self.compress_btn.setEnabled(False)

        self.compare_btn = QPushButton(tr("Compare Images"))
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        self.compare_menu_btn = QToolButton()
        self.compare_menu_btn.setText("▼")
        self.compare_menu_btn.setStyleSheet(self.compare_btn.styleSheet())
        self.compare_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.compare_menu = QMenu(self)
        self.compare_stats_only_action = QAction(tr("Compare Stats Only"), self)
        self.compare_stats_only_action.triggered.connect(self.show_stats_only_comparison)
        self.compare_menu.addAction(self.compare_stats_only_action)
        self.compare_menu_btn.setMenu(self.compare_menu)
        self.compare_menu_btn.setFixedHeight(self.compare_btn.sizeHint().height())

        compare_buttons_layout = QHBoxLayout()
        compare_buttons_layout.setContentsMargins(0, 0, 0, 0)
        compare_buttons_layout.setSpacing(5)
        compare_buttons_layout.addWidget(self.compare_btn)
        compare_buttons_layout.addWidget(self.compare_menu_btn)

        button_layout.addWidget(self.compress_btn)
        button_layout.addLayout(compare_buttons_layout)

        # Log section
        self.log_group = QGroupBox(tr("Log"))
        self.log_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.log_group.setMaximumHeight(200)
        log_layout = QVBoxLayout(self.log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)

        # Group progress, buttons, and log together at the bottom
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.progress_group)
        bottom_layout.addLayout(button_layout)
        bottom_layout.addWidget(self.log_group)

        main_layout.addStretch(1)
        main_layout.addLayout(bottom_layout)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        self.select_input_btn.clicked.connect(self.select_input_directory)
        self.select_output_btn.clicked.connect(self.select_output_directory)
        self.input_dir_edit.textChanged.connect(self.update_input_directory_from_text)
        self.output_dir_edit.textChanged.connect(self.update_output_directory_from_text)
        self.compress_btn.clicked.connect(self.start_compression)
        self.compare_btn.clicked.connect(self.show_comparison)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.language_combo.currentIndexChanged.connect(self.change_language)

    def change_language(self) -> None:
        """Handle language selection changes."""
        code = self.language_combo.currentData()
        set_language(code)
        self.update_translations()
        for panel in self.profile_panels:
            if hasattr(panel, "update_translations"):
                panel.update_translations()

    def update_button_widths(self) -> None:
        """Ensure directory selection buttons share the same width."""
        button_width = max(
            self.select_input_btn.sizeHint().width(),
            self.select_output_btn.sizeHint().width(),
            self.select_unsupported_btn.sizeHint().width(),
        )
        self.select_input_btn.setFixedWidth(button_width)
        self.select_output_btn.setFixedWidth(button_width)
        self.select_unsupported_btn.setFixedWidth(button_width)

    def update_translations(self) -> None:
        """Update UI text for the selected language."""
        self.setWindowTitle(tr("Image Compression Tool"))
        self.title_label.setText(tr("Image Compression Tool"))
        self.input_group.setTitle(tr("Input Settings"))
        if self.input_directory is None:
            self.input_dir_edit.setPlaceholderText(tr("No input directory selected"))
        self.select_input_btn.setText(tr("Select Input Directory"))
        if self.output_directory is None:
            self.output_dir_edit.setPlaceholderText(tr("No output directory selected"))
        if not self.unsupported_dir_edit.text():
            self.unsupported_dir_edit.setPlaceholderText(tr("No unsupported directory selected"))
        self.regen_output_btn.setToolTip(tr("Regenerate output directory name"))
        self.select_output_btn.setText(tr("Select Output Directory"))
        self.preserve_structure_cb.setText(tr("Preserve folder structure"))
        self.copy_unsupported_cb.setText(tr("Copy unsupported files"))
        self.copy_unsupported_separate_cb.setText(tr("Copy unsupported files to separate folder"))
        self.select_unsupported_btn.setText(tr("Select Unsupported Folder"))
        self.save_profiles_btn.setText(tr("Save Profiles"))
        self.load_profiles_btn.setText(tr("Load Profiles"))
        self.add_profile_btn.setText(tr("Add Profile"))
        self.reset_btn.setText(tr("Reset Settings"))
        self.progress_group.setTitle(tr("Progress"))
        self.status_label.setText(tr("Ready to compress images"))
        if self.compression_worker and self.compression_worker.isRunning():
            self.compress_btn.setText(tr("Abort Compression"))
            self.compress_btn.setStyleSheet(self.abort_btn_style)
        else:
            self.compress_btn.setText(tr("Start Compression"))
            self.compress_btn.setStyleSheet(self.compress_btn_default_style)
        self.compare_btn.setText(tr("Compare Images"))
        self.compare_menu_btn.setFixedHeight(self.compare_btn.sizeHint().height())
        self.compare_stats_only_action.setText(tr("Compare Stats Only"))
        self.log_group.setTitle(tr("Log"))
        self.lang_label.setText(tr("Language:"))
        self.update_button_widths()

    def select_input_directory(self) -> None:
        """Select input directory for compression."""
        directory = QFileDialog.getExistingDirectory(
            self, tr("Select Input Directory"), "", QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.input_directory = Path(directory)
            self.input_dir_edit.setText(str(self.input_directory))
            self.output_directory = self.generate_output_directory()
            self.output_dir_edit.setText(str(self.output_directory))
            self.compress_btn.setEnabled(True)
            self.log_message(tr("Selected input directory: {path}").format(path=self.input_directory))
            self.compare_btn.setEnabled(True)
            self.compare_menu_btn.setEnabled(True)

    def reset_settings(self) -> None:
        """Reset all compression settings to their default values."""
        for panel in self.profile_panels:
            panel.setParent(None)
        self.profile_panels.clear()
        self.add_profile_panel()
        self.preserve_structure_cb.setChecked(GLOBAL_DEFAULTS["preserve_structure"])
        self.copy_unsupported_cb.setChecked(GLOBAL_DEFAULTS["copy_unsupported"])
        self.copy_unsupported_separate_cb.setChecked(GLOBAL_DEFAULTS["copy_unsupported_to_dir"])
        self.unsupported_dir_edit.clear()
        self.update_copy_unsupported_state()
        self.log_message(tr("Compression settings reset to defaults"))

    def select_output_directory(self) -> None:
        """Select output directory for compression results."""
        initial_dir = str(self.output_directory.parent) if self.output_directory else ""
        directory = QFileDialog.getExistingDirectory(
            self, tr("Select Output Directory"), initial_dir, QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.output_directory = Path(directory)
            self.output_dir_edit.setText(str(self.output_directory))
            self.log_message(tr("Selected output directory: {path}").format(path=self.output_directory))
            self.update_copy_unsupported_state()
            self.update_unsupported_directory()

    def select_unsupported_directory(self) -> None:
        initial_dir = str(self.output_directory.parent) if self.output_directory else ""
        directory = QFileDialog.getExistingDirectory(
            self, tr("Select Unsupported Folder"), initial_dir, QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.unsupported_dir_edit.setText(directory)
            self.log_message(tr("Selected unsupported folder: {path}").format(path=directory))

    def update_copy_unsupported_state(self) -> None:
        enabled = self.copy_unsupported_cb.isChecked()
        self.copy_unsupported_separate_cb.setEnabled(enabled)
        separate = enabled and self.copy_unsupported_separate_cb.isChecked()
        self.unsupported_dir_edit.setVisible(separate)
        self.select_unsupported_btn.setVisible(separate)
        if separate and not self.unsupported_dir_edit.text() and self.output_directory is not None:
            self.unsupported_dir_edit.setText(str(self.generate_unsupported_directory()))

    def update_input_directory_from_text(self, text: str) -> None:
        """Update stored input directory when text changes."""
        path = Path(text)
        if text and path.exists():
            self.input_directory = path
            self.compress_btn.setEnabled(True)
            self.compare_btn.setEnabled(True)
            self.compare_menu_btn.setEnabled(True)
            self.output_directory = self.generate_output_directory()
            self.output_dir_edit.setText(str(self.output_directory))
        else:
            self.input_directory = None
            self.compress_btn.setEnabled(False)
            self.compare_btn.setEnabled(False)
            self.compare_menu_btn.setEnabled(False)

    def update_output_directory_from_text(self, text: str) -> None:
        """Update stored output directory when text changes."""
        self.output_directory = Path(text) if text else None
        if self.output_directory is not None:
            self.update_unsupported_directory()

    def update_unsupported_directory(self) -> None:
        if (
            self.output_directory is not None
            and self.copy_unsupported_cb.isChecked()
            and self.copy_unsupported_separate_cb.isChecked()
        ):
            self.unsupported_dir_edit.setText(str(self.generate_unsupported_directory()))

    def generate_unsupported_directory(self) -> Path:
        assert self.output_directory is not None
        suffix = tr("not_proceed")
        candidate = self.output_directory.parent / f"{self.output_directory.name}_{suffix}"
        counter = 1
        while candidate.exists():
            candidate = candidate.parent / f"{self.output_directory.name}_{suffix}_{counter}"
            counter += 1
        return candidate

    def generate_output_directory(self) -> Path:
        assert self.input_directory is not None
        base = f"{self.input_directory.name}_compressed_{datetime.now().strftime('%Y.%m.%d %H%M%S')}"
        candidate = self.input_directory.parent / base
        counter = 1
        while candidate.exists():
            candidate = self.input_directory.parent / f"{base}_{counter}"
            counter += 1
        return candidate

    def regenerate_output_directory(self) -> None:
        if self.input_directory is None:
            QMessageBox.warning(self, tr("Warning"), tr("Please select an input directory first."))
            return
        self.output_directory = self.generate_output_directory()
        self.output_dir_edit.setText(str(self.output_directory))
        self.log_message(tr("Regenerated output directory: {path}").format(path=self.output_directory))
        self.update_copy_unsupported_state()
        self.update_unsupported_directory()

    def add_profile_panel(self, profile: CompressionProfile | None = None) -> None:
        allow_conditions = len(self.profile_panels) > 0
        title = (
            tr("Default") if not self.profile_panels else tr("Profile {num}").format(num=len(self.profile_panels) + 1)
        )
        panel = ProfilePanel(title, allow_conditions=allow_conditions, removable=allow_conditions)
        panel.remove_requested.connect(lambda p=panel: self.remove_profile_panel(p))
        self.profile_panels.append(panel)
        self.profiles_layout.addWidget(panel)
        if profile:
            panel.apply_profile(profile)

    def save_profiles(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(self, tr("Save Profiles"), "profiles.json", "JSON Files (*.json)")
        if not file_name:
            return
        profiles = [panel.to_profile() for panel in self.profile_panels]
        save_profiles(profiles, Path(file_name))
        self.log_message(tr("Saved {count} profiles to {file}").format(count=len(profiles), file=file_name))

    def load_profiles(self) -> None:
        documents_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        file_name, _ = QFileDialog.getOpenFileName(self, tr("Load Profiles"), documents_dir, "JSON Files (*.json)")
        if not file_name:
            return
        profiles = load_profiles(Path(file_name))
        if not profiles:
            QMessageBox.warning(self, tr("Warning"), tr("No profiles found in file."))
            return
        for panel in self.profile_panels:
            panel.setParent(None)
        self.profile_panels.clear()
        for profile in profiles:
            self.add_profile_panel(profile)
        self.log_message(tr("Loaded {count} profiles from {file}").format(count=len(profiles), file=file_name))

    def remove_profile_panel(self, panel: ProfilePanel) -> None:
        if panel in self.profile_panels:
            self.profile_panels.remove(panel)
            panel.setParent(None)

    def start_compression(self) -> None:
        """Start the compression process."""
        if self.compression_worker and self.compression_worker.isRunning():
            self.log_message(tr("Stopping compression..."))
            self.status_label.setText(tr("Stopping compression..."))
            self.compression_worker.stop()
            self.compress_btn.setEnabled(False)
            self.log_message(tr("Waiting for compression to stop; start button disabled"))
            return

        if self.input_directory is None:
            QMessageBox.warning(self, tr("Warning"), tr("Please select an input directory first."))
            return

        # Ensure output directory is set
        # Update output directory from text field
        if self.output_dir_edit.text():
            self.output_directory = Path(self.output_dir_edit.text())

        if self.output_directory is None:
            self.output_directory = self.generate_output_directory()
            self.output_dir_edit.setText(str(self.output_directory))

        if self.output_directory.exists():
            QMessageBox.warning(
                self,
                tr("Warning"),
                tr("Output directory already exists. Please regenerate or choose another path."),
            )
            return

        profiles = [panel.to_profile() for panel in self.profile_panels]
        default_profile = profiles[0]

        preserve_structure = self.preserve_structure_cb.isChecked()
        copy_unsupported = self.copy_unsupported_cb.isChecked()
        copy_unsupported_to_dir = self.copy_unsupported_separate_cb.isChecked()
        unsupported_dir = (
            Path(self.unsupported_dir_edit.text())
            if copy_unsupported and copy_unsupported_to_dir and self.unsupported_dir_edit.text()
            else None
        )
        compressor = ImageCompressor(
            quality=default_profile.quality,
            max_largest_side=default_profile.max_largest_side,
            max_smallest_side=default_profile.max_smallest_side,
            preserve_structure=preserve_structure,
            copy_unsupported=copy_unsupported,
            unsupported_dir=unsupported_dir,
            output_format=default_profile.output_format,
        )
        compressor.apply_profile(default_profile)

        compression_settings = {
            "input_directory": str(self.input_directory),
            "output_directory": str(self.output_directory),
            "profiles": [asdict(p) for p in profiles],
            "preserve_structure": preserve_structure,
            "copy_unsupported": copy_unsupported,
            "copy_unsupported_to_dir": copy_unsupported_to_dir,
            "unsupported_dir": str(unsupported_dir) if unsupported_dir else "",
        }

        # Create and start worker thread
        assert self.output_directory is not None
        self.compression_worker = CompressionWorker(
            compressor,
            self.input_directory,
            self.output_directory,
            compression_settings,
            profiles,
        )
        self.compression_worker.progress_updated.connect(self.update_progress)
        self.compression_worker.status_updated.connect(self.update_status)
        self.compression_worker.log_updated.connect(self.log_message)
        self.compression_worker.compression_finished.connect(self.compression_finished)
        self.compression_worker.error_occurred.connect(self.compression_error)

        self.progress_start_time = datetime.now()

        # Update UI
        self.compress_btn.setText(tr("Abort Compression"))
        self.compress_btn.setStyleSheet(self.abort_btn_style)
        self.compare_btn.setEnabled(False)
        self.compare_menu_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start compression
        self.compression_worker.start()
        self.log_message(tr("Starting compression process..."))

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        if current > 0 and self.progress_start_time:
            elapsed = datetime.now() - self.progress_start_time
            remaining = elapsed * (total - current) / current
            remaining_text = format_timedelta(remaining)
            status = tr("Processed {current}/{total} files (≈ {remaining} left)").format(
                current=current, total=total, remaining=remaining_text
            )
        else:
            status = tr("Processed {current}/{total} files").format(current=current, total=total)
        self.status_label.setText(status)

    def update_status(self, message: str) -> None:
        """Update status message."""
        self.status_label.setText(message)
        self.log_message(message)

    def compression_finished(self, stats: dict) -> None:
        """Handle compression completion."""
        cancelled = self.compression_worker.cancelled if self.compression_worker else False
        self.progress_start_time = None

        # Update UI
        self.compress_btn.setText(tr("Start Compression"))
        self.compress_btn.setStyleSheet(self.compress_btn_default_style)
        self.compress_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.compare_menu_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if cancelled:
            pass
        else:
            message = f"""
Compression completed successfully!

Statistics:
- Total files processed: {stats["total_files"]}
- Files compressed: {stats["compressed_files"]}
- Input size: {stats["input_size_mb"]:.2f} MB
- Output size: {stats["output_size_mb"]:.2f} MB
- Space saved: {stats["space_saved_mb"]:.2f} MB
- Compression ratio: {stats["compression_ratio_percent"]:.1f}%

Output directory: {self.output_directory}
            """

            self.log_message(tr("Compression completed successfully!"))
            QMessageBox.information(self, tr("Compression Complete"), message)
            self.status_label.setText(tr("Compression completed successfully!"))

        self.compression_worker = None

    def compression_error(self, error_message: str) -> None:
        """Handle compression error."""
        self.compress_btn.setText(tr("Start Compression"))
        self.compress_btn.setStyleSheet(self.compress_btn_default_style)
        self.compress_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.compare_menu_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(tr("Compression failed"))
        self.log_message(tr("Error: {error}").format(error=error_message))
        QMessageBox.critical(
            self,
            tr("Compression Error"),
            tr("An error occurred during compression:\n\n{error}").format(error=error_message),
        )
        self.compression_worker = None

    def show_stats_only_comparison(self) -> None:
        """Show comparison dialog for statistics files only."""
        file1, _ = QFileDialog.getOpenFileName(
            self, tr("Select Stats File"), str(self.output_directory or Path.home()), "JSON Files (*.json)"
        )
        if not file1:
            return
        file2, _ = QFileDialog.getOpenFileName(
            self, tr("Select Stats File"), str(self.output_directory or Path.home()), "JSON Files (*.json)"
        )
        if not file2:
            return
        try:
            data1 = json.loads(Path(file1).read_text())
            data2 = json.loads(Path(file2).read_text())
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to load statistics:\n\n{error}").format(error=e),
            )
            return
        stats1 = data1.get("stats", {})
        stats2 = data2.get("stats", {})
        settings1 = data1.get("compression_settings", {})
        settings2 = data2.get("compression_settings", {})
        from service.image_comparison_viewer import CompressionStatsDialog

        dialog = CompressionStatsDialog(stats1, stats2, settings1, settings2, self)
        dialog.exec()

    def show_comparison(self) -> None:
        """Show the image comparison window."""
        try:
            from service.image_comparison_viewer import MainWindow as ComparisonViewer

            self.comparison_window = ComparisonViewer()
            self.comparison_window.show()

            if self.output_directory and self.input_directory:
                settings_file = self.output_directory / "compression_settings.json"
                if settings_file.exists():
                    self.comparison_window.load_config_from_path(settings_file)
                else:
                    self.comparison_window.load_directories_from_paths(self.output_directory, self.input_directory)

            self.log_message(tr("Opened comparison window"))

        except Exception as e:
            self.log_message(tr("Error opening comparison: {error}").format(error=e))
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to open comparison window:\n\n{error}").format(error=e),
            )

    def log_message(self, message: str) -> None:
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def _resource_root() -> Path:
    """Return base directory for bundled resource files."""
    if getattr(sys, "frozen", False):
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent.parent


def main() -> None:
    """Main application entry point."""
    app = QApplication(sys.argv)

    icon_path = _resource_root() / "resources" / "bp.ico"
    app.setWindowIcon(QIcon(str(icon_path)))  # общий значок для всех окон

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
