#!/usr/bin/env python3
"""
Image Compression Application
Main application for compressing images with configurable parameters.
"""

import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
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
    create_image_pairs,
    save_compression_settings,
)
from service.profile_panel import ProfilePanel


class CompressionWorker(QThread):
    """Worker thread for image compression to avoid blocking the UI."""

    progress_updated = Signal(int, int)  # current, total
    status_updated = Signal(str)
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

    def run(self) -> None:
        """Run the compression process."""
        try:
            self.status_updated.emit("Starting compression...")
            start_time = datetime.now()

            # Process the directory
            total_files, compressed_files, compressed_paths, failed_files = self.compressor.process_directory(
                self.input_dir, self.output_dir, self.profiles
            )

            # Get compression statistics
            stats = self.compressor.get_compression_stats(
                self.input_dir,
                self.output_dir,
                compressed_paths,
                failed_files,
            )
            stats["total_files"] = total_files
            stats["compressed_files"] = compressed_files
            stats["failed_files_count"] = len(failed_files)

            elapsed = datetime.now() - start_time
            stats["conversion_time"] = format_timedelta(elapsed)

            # Create image pairs for settings file
            image_pairs = create_image_pairs(self.output_dir, self.input_dir)

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

            self.status_updated.emit(
                f"Compression completed! {compressed_files}/{total_files} files compressed. {len(failed_files)} failed."
            )
            self.compression_finished.emit(stats)

        except Exception as e:
            self.error_occurred.emit(f"Compression error: {e!s}")


class MainWindow(QMainWindow):
    """Main application window for image compression."""

    def __init__(self) -> None:
        super().__init__()
        self.compression_worker: CompressionWorker | None = None
        self.output_directory: Path | None = None
        self.input_directory: Path | None = None

        self.setup_ui()
        self.setup_connections()

        # Set window properties
        self.setWindowTitle("Image Compression Tool")
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

        # Title
        title_label = QLabel("Image Compression Tool")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Input section
        input_group = QGroupBox("Input Settings")
        input_layout = QVBoxLayout(input_group)

        # Input directory selection
        input_dir_layout = QHBoxLayout()
        self.input_dir_label = QLabel("No input directory selected")
        self.input_dir_label.setStyleSheet(
            "padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.select_input_btn = QPushButton("Select Input Directory")
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

        input_dir_layout.addWidget(self.input_dir_label, 1)
        input_dir_layout.addWidget(self.select_input_btn)
        input_layout.addLayout(input_dir_layout)

        # Output directory selection
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("No output directory selected")
        self.output_dir_edit.setStyleSheet(
            "padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.regen_output_btn = QToolButton()
        self.regen_output_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.regen_output_btn.setToolTip("Regenerate output directory name")
        self.regen_output_btn.clicked.connect(self.regenerate_output_directory)
        self.select_output_btn = QPushButton("Select Output Directory")
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

        # Ensure directory selection buttons have the same width
        button_width = max(
            self.select_input_btn.sizeHint().width(),
            self.select_output_btn.sizeHint().width(),
        )
        self.select_input_btn.setFixedWidth(button_width)
        self.select_output_btn.setFixedWidth(button_width)

        output_dir_layout.addWidget(self.output_dir_edit, 1)
        output_dir_layout.addWidget(self.regen_output_btn)
        output_dir_layout.addWidget(self.select_output_btn)
        input_layout.addLayout(output_dir_layout)

        main_layout.addWidget(input_group)

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

        self.save_profiles_btn = QPushButton("Save Profiles")
        self.save_profiles_btn.clicked.connect(self.save_profiles)
        header_layout.addWidget(self.save_profiles_btn)

        self.load_profiles_btn = QPushButton("Load Profiles")
        self.load_profiles_btn.clicked.connect(self.load_profiles)
        header_layout.addWidget(self.load_profiles_btn)

        self.add_profile_btn = QPushButton("Add Profile")
        self.add_profile_btn.clicked.connect(self.add_profile_panel)
        header_layout.addWidget(self.add_profile_btn)

        self.reset_btn = QPushButton("Reset Settings")
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
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to compress images")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        progress_layout.addWidget(self.status_label)

        main_layout.addWidget(progress_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.compress_btn = QPushButton("Start Compression")
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
        self.compress_btn.setEnabled(False)

        self.compare_btn = QPushButton("Compare Images")
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

        button_layout.addWidget(self.compress_btn)
        button_layout.addWidget(self.compare_btn)
        main_layout.addLayout(button_layout)

        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

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

        main_layout.addWidget(log_group)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        self.select_input_btn.clicked.connect(self.select_input_directory)
        self.select_output_btn.clicked.connect(self.select_output_directory)
        self.output_dir_edit.textChanged.connect(self.update_output_directory_from_text)
        self.compress_btn.clicked.connect(self.start_compression)
        self.compare_btn.clicked.connect(self.show_comparison)
        self.reset_btn.clicked.connect(self.reset_settings)

    def select_input_directory(self) -> None:
        """Select input directory for compression."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", "", QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.input_directory = Path(directory)
            self.input_dir_label.setText(str(self.input_directory))
            self.output_directory = self.generate_output_directory()
            self.output_dir_edit.setText(str(self.output_directory))
            self.compress_btn.setEnabled(True)
            self.log_message(f"Selected input directory: {self.input_directory}")
            self.compare_btn.setEnabled(True)

    def reset_settings(self) -> None:
        """Reset all compression settings to their default values."""
        for panel in self.profile_panels:
            panel.setParent(None)
        self.profile_panels.clear()
        self.add_profile_panel()
        self.log_message("Compression settings reset to defaults")

    def select_output_directory(self) -> None:
        """Select output directory for compression results."""
        initial_dir = str(self.output_directory.parent) if self.output_directory else ""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", initial_dir, QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.output_directory = Path(directory)
            self.output_dir_edit.setText(str(self.output_directory))
            self.log_message(f"Selected output directory: {self.output_directory}")

    def update_output_directory_from_text(self, text: str) -> None:
        """Update stored output directory when text changes."""
        self.output_directory = Path(text) if text else None

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
            QMessageBox.warning(self, "Warning", "Please select an input directory first.")
            return
        self.output_directory = self.generate_output_directory()
        self.output_dir_edit.setText(str(self.output_directory))
        self.log_message(f"Regenerated output directory: {self.output_directory}")

    def add_profile_panel(self, profile: CompressionProfile | None = None) -> None:
        allow_conditions = len(self.profile_panels) > 0
        title = "Default" if not self.profile_panels else f"Profile {len(self.profile_panels) + 1}"
        panel = ProfilePanel(title, allow_conditions=allow_conditions, removable=allow_conditions)
        panel.remove_requested.connect(lambda p=panel: self.remove_profile_panel(p))
        self.profile_panels.append(panel)
        self.profiles_layout.addWidget(panel)
        if profile:
            panel.apply_profile(profile)

    def save_profiles(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Profiles", "profiles.json", "JSON Files (*.json)")
        if not file_name:
            return
        profiles = [panel.to_profile() for panel in self.profile_panels]
        save_profiles(profiles, Path(file_name))
        self.log_message(f"Saved {len(profiles)} profiles to {file_name}")

    def load_profiles(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Profiles", "", "JSON Files (*.json)")
        if not file_name:
            return
        profiles = load_profiles(Path(file_name))
        if not profiles:
            QMessageBox.warning(self, "Warning", "No profiles found in file.")
            return
        for panel in self.profile_panels:
            panel.setParent(None)
        self.profile_panels.clear()
        for profile in profiles:
            self.add_profile_panel(profile)
        self.log_message(f"Loaded {len(profiles)} profiles from {file_name}")

    def remove_profile_panel(self, panel: ProfilePanel) -> None:
        if panel in self.profile_panels:
            self.profile_panels.remove(panel)
            panel.setParent(None)

    def start_compression(self) -> None:
        """Start the compression process."""
        if self.input_directory is None:
            QMessageBox.warning(self, "Warning", "Please select an input directory first.")
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
                "Warning",
                "Output directory already exists. Please regenerate or choose another path.",
            )
            return

        profiles = [panel.to_profile() for panel in self.profile_panels]
        default_profile = profiles[0]

        compressor = ImageCompressor(
            quality=default_profile.quality,
            max_largest_side=default_profile.max_largest_side,
            max_smallest_side=default_profile.max_smallest_side,
            preserve_structure=default_profile.preserve_structure,
            output_format=default_profile.output_format,
        )
        compressor.set_jpeg_parameters(**default_profile.jpeg_params)
        compressor.set_webp_parameters(**default_profile.webp_params)
        compressor.set_avif_parameters(**default_profile.avif_params)

        compression_settings = {
            "input_directory": str(self.input_directory),
            "output_directory": str(self.output_directory),
            "profiles": [asdict(p) for p in profiles],
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
        self.compression_worker.compression_finished.connect(self.compression_finished)
        self.compression_worker.error_occurred.connect(self.compression_error)

        # Update UI
        self.compress_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start compression
        self.compression_worker.start()
        self.log_message("Starting compression process...")

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def update_status(self, message: str) -> None:
        """Update status message."""
        self.status_label.setText(message)
        self.log_message(message)

    def compression_finished(self, stats: dict) -> None:
        """Handle compression completion."""
        # Update UI
        self.compress_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Show completion message
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

        self.log_message("Compression completed successfully!")
        QMessageBox.information(self, "Compression Complete", message)

        # Update status
        self.status_label.setText("Compression completed successfully!")

    def compression_error(self, error_message: str) -> None:
        """Handle compression error."""
        self.compress_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Compression failed")
        self.log_message(f"ERROR: {error_message}")
        QMessageBox.critical(
            self,
            "Compression Error",
            f"An error occurred during compression:\n\n{error_message}",
        )

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

            self.log_message("Opened comparison window")

        except Exception as e:
            self.log_message(f"Error opening comparison: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open comparison window:\n\n{e!s}")

    def log_message(self, message: str) -> None:
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main() -> None:
    """Main application entry point."""
    app = QApplication(sys.argv)

    icon_path = Path(__file__).resolve().parent.parent / "resources" / "bp.ico"
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
