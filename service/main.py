#!/usr/bin/env python3
"""
Image Compression Application
Main application for compressing images with configurable parameters.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from service.image_comparison import ImagePair, show_comparison_window

# Import our modules
from service.image_compression import (
    ImageCompressor,
    create_image_pairs,
    save_compression_settings,
)


class CompressionWorker(QThread):
    """Worker thread for image compression to avoid blocking the UI."""

    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    compression_finished = pyqtSignal(dict)  # stats
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        compressor: ImageCompressor,
        input_dir: Path,
        output_dir: Path,
        compression_settings: dict,
    ) -> None:
        super().__init__()
        self.compressor = compressor
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.compression_settings = compression_settings

    def run(self) -> None:
        """Run the compression process."""
        try:
            self.status_updated.emit("Starting compression...")

            # Process the directory
            total_files, compressed_files, compressed_paths = self.compressor.process_directory(
                self.input_dir, self.output_dir
            )

            # Get compression statistics
            stats = self.compressor.get_compression_stats(self.input_dir, self.output_dir)
            stats["total_files"] = total_files
            stats["compressed_files"] = compressed_files

            # Create image pairs for settings file
            image_pairs = create_image_pairs(self.output_dir, self.input_dir)

            # Save compression settings
            if image_pairs:
                save_compression_settings(self.output_dir, self.compression_settings, image_pairs, stats)

            self.status_updated.emit(f"Compression completed! {compressed_files}/{total_files} files compressed.")
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

        # Store all parameter widgets for dynamic UI updates
        self.parameter_widgets: dict[str, dict[str, QWidget]] = {}

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

        main_layout.addWidget(input_group)

        # Create scrollable area for compression settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # Compression settings container
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)

        # Basic settings group
        self.basic_group = QGroupBox("Basic Settings")
        self.basic_layout = QGridLayout(self.basic_group)

        # Quality setting (common for all formats)
        self.basic_layout.addWidget(QLabel("Quality:"), 0, 0)
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(1, 100)
        self.quality_spinbox.setValue(75)
        self.quality_spinbox.setSuffix("%")
        self.quality_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.quality_spinbox.setToolTip("Quality level (1-100). Lower values = stronger compression, smaller files")
        self.basic_layout.addWidget(self.quality_spinbox, 0, 1)

        # Max largest side
        self.basic_layout.addWidget(QLabel("Max Largest Side:"), 1, 0)
        self.max_largest_spinbox = QSpinBox()
        self.max_largest_spinbox.setRange(100, 10000)
        self.max_largest_spinbox.setValue(1920)
        self.max_largest_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.max_largest_spinbox.setToolTip("Maximum size of the largest side in pixels")
        self.basic_layout.addWidget(self.max_largest_spinbox, 1, 1)

        # Max smallest side
        self.basic_layout.addWidget(QLabel("Max Smallest Side:"), 2, 0)
        self.max_smallest_spinbox = QSpinBox()
        self.max_smallest_spinbox.setRange(100, 10000)
        self.max_smallest_spinbox.setValue(1080)
        self.max_smallest_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.max_smallest_spinbox.setToolTip("Maximum size of the smallest side in pixels")
        self.basic_layout.addWidget(self.max_smallest_spinbox, 2, 1)

        # Output format
        self.basic_layout.addWidget(QLabel("Output Format:"), 3, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "WebP", "AVIF"])
        self.format_combo.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.format_combo.setToolTip("Output image format")
        self.basic_layout.addWidget(self.format_combo, 3, 1)

        # Preserve original structure
        self.preserve_structure_checkbox = QCheckBox("Preserve folder structure")
        self.preserve_structure_checkbox.setChecked(True)
        self.preserve_structure_checkbox.setToolTip(
            "Keep original folder structure or flatten all files to output directory"
        )
        self.basic_layout.addWidget(self.preserve_structure_checkbox, 4, 0, 1, 2)

        self.settings_layout.addWidget(self.basic_group)

        # Format-specific settings groups
        self.create_format_specific_settings()

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
                background-color: #17a2b8;
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
        self.compare_btn.setEnabled(False)

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

        # Initialize format-specific settings visibility
        self.update_format_specific_settings()

    def create_format_specific_settings(self) -> None:
        # Store all widgets for easy access
        self.parameter_widgets = {
            "jpeg": self._setup_advanced_for_jpeg(),
            "webp": self._setup_advanced_for_webp(),
            "avif": self._setup_advanced_for_avif(),
        }

    def _setup_advanced_for_jpeg(self) -> dict:
        # JPEG Settings
        self.jpeg_group = QGroupBox("JPEG Advanced Settings")
        self.jpeg_group.setVisible(False)
        jpeg_layout = QGridLayout(self.jpeg_group)

        # Progressive
        jpeg_layout.addWidget(QLabel("Progressive:"), 0, 0)
        self.jpeg_progressive = QCheckBox()
        self.jpeg_progressive.setChecked(False)
        self.jpeg_progressive.setToolTip("Progressive JPEG encoding. Sometimes reduces file size")
        jpeg_layout.addWidget(self.jpeg_progressive, 0, 1)

        # Subsampling
        jpeg_layout.addWidget(QLabel("Subsampling:"), 1, 0)
        self.jpeg_subsampling = QComboBox()
        self.jpeg_subsampling.addItems(["Auto (-1)", "4:4:4 (0)", "4:2:2 (1)", "4:2:0 (2)"])
        self.jpeg_subsampling.setCurrentText("Auto (-1)")
        self.jpeg_subsampling.setToolTip("Color subsampling. 4:4:4 = best quality, 4:2:0 = best compression")
        jpeg_layout.addWidget(self.jpeg_subsampling, 1, 1)

        # Optimize
        jpeg_layout.addWidget(QLabel("Optimize:"), 2, 0)
        self.jpeg_optimize = QCheckBox()
        self.jpeg_optimize.setChecked(False)
        self.jpeg_optimize.setToolTip("Huffman optimization for better compression")
        jpeg_layout.addWidget(self.jpeg_optimize, 2, 1)

        # Smooth
        jpeg_layout.addWidget(QLabel("Smooth:"), 3, 0)
        self.jpeg_smooth = QSpinBox()
        self.jpeg_smooth.setRange(0, 100)
        self.jpeg_smooth.setValue(0)
        self.jpeg_smooth.setToolTip("Light smoothing (0-100). Reduces noise for better compression")
        jpeg_layout.addWidget(self.jpeg_smooth, 3, 1)

        # Keep RGB
        jpeg_layout.addWidget(QLabel("Keep RGB:"), 4, 0)
        self.jpeg_keep_rgb = QCheckBox()
        self.jpeg_keep_rgb.setChecked(False)
        self.jpeg_keep_rgb.setToolTip("Save in RGB instead of YCbCr. May increase size but removes color transitions")
        jpeg_layout.addWidget(self.jpeg_keep_rgb, 4, 1)

        self.settings_layout.addWidget(self.jpeg_group)
        return {
            "progressive": self.jpeg_progressive,
            "subsampling": self.jpeg_subsampling,
            "optimize": self.jpeg_optimize,
            "smooth": self.jpeg_smooth,
            "keep_rgb": self.jpeg_keep_rgb,
        }

    def _setup_advanced_for_webp(self) -> dict:
        # WebP Settings
        self.webp_group = QGroupBox("WebP Advanced Settings")
        self.webp_group.setVisible(False)
        webp_layout = QGridLayout(self.webp_group)

        # Lossless
        webp_layout.addWidget(QLabel("Lossless:"), 0, 0)
        self.webp_lossless = QCheckBox()
        self.webp_lossless.setChecked(False)
        self.webp_lossless.setToolTip("Lossless compression. Radically changes compression method")
        webp_layout.addWidget(self.webp_lossless, 0, 1)

        # Method
        webp_layout.addWidget(QLabel("Method:"), 1, 0)
        self.webp_method = QSpinBox()
        self.webp_method.setRange(0, 6)
        self.webp_method.setValue(4)
        self.webp_method.setToolTip("Compression method (0-6). Slower = better compression at same quality")
        webp_layout.addWidget(self.webp_method, 1, 1)

        # Alpha Quality
        webp_layout.addWidget(QLabel("Alpha Quality:"), 2, 0)
        self.webp_alpha_quality = QSpinBox()
        self.webp_alpha_quality.setRange(0, 100)
        self.webp_alpha_quality.setValue(100)
        self.webp_alpha_quality.setToolTip("Quality of alpha channel in lossy mode")
        webp_layout.addWidget(self.webp_alpha_quality, 2, 1)

        # Exact
        webp_layout.addWidget(QLabel("Exact:"), 3, 0)
        self.webp_exact = QCheckBox()
        self.webp_exact.setChecked(False)
        self.webp_exact.setToolTip("Save RGB under transparency. Increases size but improves quality")
        webp_layout.addWidget(self.webp_exact, 3, 1)
        self.settings_layout.addWidget(self.webp_group)

        return {
            "lossless": self.webp_lossless,
            "method": self.webp_method,
            "alpha_quality": self.webp_alpha_quality,
            "exact": self.webp_exact,
        }

    def _setup_advanced_for_avif(self) -> dict:
        # AVIF Settings
        self.avif_group = QGroupBox("AVIF Advanced Settings")
        self.avif_group.setVisible(False)
        avif_layout = QGridLayout(self.avif_group)

        # Subsampling
        avif_layout.addWidget(QLabel("Subsampling:"), 0, 0)
        self.avif_subsampling = QComboBox()
        self.avif_subsampling.addItems(["4:2:0", "4:2:2", "4:4:4", "4:0:0"])
        self.avif_subsampling.setCurrentText("4:2:0")
        self.avif_subsampling.setToolTip("Color subsampling. 4:4:4 = best quality, 4:2:0 = best compression")
        avif_layout.addWidget(self.avif_subsampling, 0, 1)

        # Speed
        avif_layout.addWidget(QLabel("Speed:"), 1, 0)
        self.avif_speed = QSpinBox()
        self.avif_speed.setRange(0, 10)
        self.avif_speed.setValue(6)
        self.avif_speed.setToolTip("Encoding speed (0-10). 0 = slower/better, 10 = faster/worse")
        avif_layout.addWidget(self.avif_speed, 1, 1)

        # Codec
        avif_layout.addWidget(QLabel("Codec:"), 2, 0)
        self.avif_codec = QComboBox()
        self.avif_codec.addItems(["auto", "aom", "rav1e", "svt"])
        self.avif_codec.setCurrentText("auto")
        self.avif_codec.setToolTip("AV1 encoder to use (if available)")
        avif_layout.addWidget(self.avif_codec, 2, 1)

        # Range
        avif_layout.addWidget(QLabel("Range:"), 3, 0)
        self.avif_range = QComboBox()
        self.avif_range.addItems(["full", "limited"])
        self.avif_range.setCurrentText("full")
        self.avif_range.setToolTip("Tonal range")
        avif_layout.addWidget(self.avif_range, 3, 1)

        # QMin
        avif_layout.addWidget(QLabel("QMin:"), 4, 0)
        self.avif_qmin = QSpinBox()
        self.avif_qmin.setRange(-1, 63)
        self.avif_qmin.setValue(-1)
        self.avif_qmin.setToolTip("Minimum quantizer (-1 = auto, 0-63 = hard lower bound)")
        avif_layout.addWidget(self.avif_qmin, 4, 1)

        # QMax
        avif_layout.addWidget(QLabel("QMax:"), 5, 0)
        self.avif_qmax = QSpinBox()
        self.avif_qmax.setRange(-1, 63)
        self.avif_qmax.setValue(-1)
        self.avif_qmax.setToolTip("Maximum quantizer (-1 = auto, 0-63 = upper bound)")
        avif_layout.addWidget(self.avif_qmax, 5, 1)

        # Auto Tiling
        avif_layout.addWidget(QLabel("Auto Tiling:"), 6, 0)
        self.avif_autotiling = QCheckBox()
        self.avif_autotiling.setChecked(True)
        self.avif_autotiling.setToolTip("Automatic tiling for better decoding speed")
        avif_layout.addWidget(self.avif_autotiling, 6, 1)

        # Tile Rows
        avif_layout.addWidget(QLabel("Tile Rows (log2):"), 7, 0)
        self.avif_tile_rows = QSpinBox()
        self.avif_tile_rows.setRange(0, 6)
        self.avif_tile_rows.setValue(0)
        self.avif_tile_rows.setToolTip("Explicit tile rows (if auto tiling = false)")
        avif_layout.addWidget(self.avif_tile_rows, 7, 1)

        # Tile Cols
        avif_layout.addWidget(QLabel("Tile Cols (log2):"), 8, 0)
        self.avif_tile_cols = QSpinBox()
        self.avif_tile_cols.setRange(0, 6)
        self.avif_tile_cols.setValue(0)
        self.avif_tile_cols.setToolTip("Explicit tile columns (if auto tiling = false)")
        avif_layout.addWidget(self.avif_tile_cols, 8, 1)
        self.settings_layout.addWidget(self.avif_group)

        return {
            "subsampling": self.avif_subsampling,
            "speed": self.avif_speed,
            "codec": self.avif_codec,
            "range": self.avif_range,
            "qmin": self.avif_qmin,
            "qmax": self.avif_qmax,
            "autotiling": self.avif_autotiling,
            "tile_rows": self.avif_tile_rows,
            "tile_cols": self.avif_tile_cols,
        }

    def update_format_specific_settings(self) -> None:
        """Update visibility of format-specific settings based on selected format."""
        format_name = self.format_combo.currentText().lower()

        # Hide all groups first
        self.jpeg_group.setVisible(False)
        self.webp_group.setVisible(False)
        self.avif_group.setVisible(False)

        # Show only the relevant group
        if format_name == "jpeg":
            self.jpeg_group.setVisible(True)
        elif format_name == "webp":
            self.webp_group.setVisible(True)
        elif format_name == "avif":
            self.avif_group.setVisible(True)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        self.select_input_btn.clicked.connect(self.select_input_directory)
        self.compress_btn.clicked.connect(self.start_compression)
        self.compare_btn.clicked.connect(self.show_comparison)
        self.format_combo.currentTextChanged.connect(self.update_format_specific_settings)

    def select_input_directory(self) -> None:
        """Select input directory for compression."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", "", QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.input_directory = Path(directory)
            self.input_dir_label.setText(str(self.input_directory))
            self.compress_btn.setEnabled(True)
            self.log_message(f"Selected input directory: {self.input_directory}")
            self.compare_btn.setEnabled(True)

    def get_compression_parameters(self) -> dict[str, Any]:
        """Get all compression parameters from UI."""
        format_name = self.format_combo.currentText().lower()

        # Basic parameters
        params = {
            "quality": self.quality_spinbox.value(),
            "max_largest_side": self.max_largest_spinbox.value(),
            "max_smallest_side": self.max_smallest_spinbox.value(),
            "preserve_structure": self.preserve_structure_checkbox.isChecked(),
            "output_format": self.format_combo.currentText(),
            "input_directory": str(self.input_directory),
            "output_directory": str(self.output_directory),
        }

        # Format-specific parameters
        if format_name == "jpeg":
            params.update(
                {
                    "progressive": self.jpeg_progressive.isChecked(),
                    "subsampling": self._get_jpeg_subsampling_value(),
                    "optimize": self.jpeg_optimize.isChecked(),
                    "smooth": self.jpeg_smooth.value(),
                    "keep_rgb": self.jpeg_keep_rgb.isChecked(),
                }
            )
        elif format_name == "webp":
            params.update(
                {
                    "lossless": self.webp_lossless.isChecked(),
                    "method": self.webp_method.value(),
                    "alpha_quality": self.webp_alpha_quality.value(),
                    "exact": self.webp_exact.isChecked(),
                }
            )
        elif format_name == "avif":
            params.update(
                {
                    "subsampling": self.avif_subsampling.currentText(),
                    "speed": self.avif_speed.value(),
                    "codec": self.avif_codec.currentText(),
                    "range": self.avif_range.currentText(),
                    "qmin": self.avif_qmin.value(),
                    "qmax": self.avif_qmax.value(),
                    "autotiling": self.avif_autotiling.isChecked(),
                    "tile_rows": self.avif_tile_rows.value(),
                    "tile_cols": self.avif_tile_cols.value(),
                }
            )

        return params

    def _get_jpeg_subsampling_value(self) -> int | str:
        """Convert JPEG subsampling combo text to actual value."""
        text = self.jpeg_subsampling.currentText()
        if "4:4:4" in text:
            return 0
        if "4:2:2" in text:
            return 1
        if "4:2:0" in text:
            return 2
        return -1  # Auto

    def start_compression(self) -> None:
        """Start the compression process."""
        if self.input_directory is None:
            QMessageBox.warning(self, "Warning", "Please select an input directory first.")
            return

        # Create output directory
        output_name = f"{self.input_directory.name}_compressed_{datetime.now().strftime('%Y.%m.%d %H%M%S')}"
        self.output_directory = self.input_directory.parent / output_name

        # Get all compression parameters
        compression_params = self.get_compression_parameters()

        # Create compressor with basic parameters
        compressor = ImageCompressor(
            quality=compression_params["quality"],
            max_largest_side=compression_params["max_largest_side"],
            max_smallest_side=compression_params["max_smallest_side"],
            preserve_structure=compression_params["preserve_structure"],
            output_format=compression_params["output_format"],
        )

        # Set format-specific parameters
        format_name = compression_params["output_format"].lower()
        if format_name == "jpeg":
            compressor.set_jpeg_parameters(
                progressive=compression_params.get("progressive", False),
                subsampling=compression_params.get("subsampling", -1),
                optimize=compression_params.get("optimize", False),
                smooth=compression_params.get("smooth", 0),
                keep_rgb=compression_params.get("keep_rgb", False),
            )
        elif format_name == "webp":
            compressor.set_webp_parameters(
                lossless=compression_params.get("lossless", False),
                method=compression_params.get("method", 4),
                alpha_quality=compression_params.get("alpha_quality", 100),
                exact=compression_params.get("exact", False),
            )
        elif format_name == "avif":
            compressor.set_avif_parameters(
                subsampling=compression_params.get("subsampling", "4:2:0"),
                speed=compression_params.get("speed", 6),
                codec=compression_params.get("codec", "auto"),
                range=compression_params.get("range", "full"),
                qmin=compression_params.get("qmin", -1),
                qmax=compression_params.get("qmax", -1),
                autotiling=compression_params.get("autotiling", True),
                tile_rows=compression_params.get("tile_rows", 0),
                tile_cols=compression_params.get("tile_cols", 0),
            )

        # Store all parameters for the worker
        compression_settings = compression_params.copy()

        # Create and start worker thread
        assert self.output_directory is not None
        self.compression_worker = CompressionWorker(
            compressor,
            self.input_directory,
            self.output_directory,
            compression_settings,
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
        if not self.output_directory or not self.output_directory.exists():
            QMessageBox.warning(self, "Warning", "Please complete compression first.")
            return

        try:
            assert self.output_directory is not None
            # Create image pairs
            comparison_pairs = []
            image_pairs = create_image_pairs(self.output_directory, self.input_directory)

            for img1_path, img2_path in image_pairs:
                # Determine pair name based on whether it's a real comparison
                if img1_path.parent != img2_path.parent:
                    # This is a real comparison (original vs compressed)
                    pair_name = f"{img1_path.name} (Original vs Compressed)"
                else:
                    # Fallback: same file comparison
                    pair_name = f"{img1_path.name} (Same file)"

                comparison_pairs.append(ImagePair(str(img1_path), str(img2_path), pair_name))

            # Show comparison window with settings file
            settings_file = self.output_directory / "compression_settings.json"
            self.comparison_window = show_comparison_window(comparison_pairs, settings_file)
            self.log_message(f"Opened comparison window with {len(comparison_pairs)} image pairs")

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

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
