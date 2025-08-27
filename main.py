#!/usr/bin/env python3
"""
Image Compression Application
Main application for compressing images with configurable parameters.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                             QSpinBox, QProgressBar, QTextEdit, QGroupBox,
                             QGridLayout, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

# Import our modules
from image_compression import ImageCompressor, create_image_pairs, save_compression_settings, load_compression_settings
from image_comparison import ImagePair, show_comparison_window


class CompressionWorker(QThread):
    """Worker thread for image compression to avoid blocking the UI."""
    
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    compression_finished = pyqtSignal(dict)  # stats
    error_occurred = pyqtSignal(str)
    
    def __init__(self, compressor: ImageCompressor, input_dir: Path, output_dir: Path, compression_settings: dict):
        super().__init__()
        self.compressor = compressor
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.compression_settings = compression_settings
    
    def run(self):
        """Run the compression process."""
        try:
            self.status_updated.emit("Starting compression...")
            
            # Process the directory
            total_files, compressed_files, compressed_paths = self.compressor.process_directory(
                self.input_dir, self.output_dir
            )
            
            # Get compression statistics
            stats = self.compressor.get_compression_stats(self.input_dir, self.output_dir)
            stats['total_files'] = total_files
            stats['compressed_files'] = compressed_files
            
            # Create image pairs for settings file
            image_pairs = create_image_pairs(self.output_dir, self.input_dir)
            
            # Save compression settings
            if image_pairs:
                save_compression_settings(self.output_dir, self.compression_settings, image_pairs)
            
            self.status_updated.emit(f"Compression completed! {compressed_files}/{total_files} files compressed.")
            self.compression_finished.emit(stats)
            
        except Exception as e:
            self.error_occurred.emit(f"Compression error: {str(e)}")


class MainWindow(QMainWindow):
    """Main application window for image compression."""
    
    def __init__(self):
        super().__init__()
        self.compression_worker = None
        self.output_directory = None
        
        self.setup_ui()
        self.setup_connections()
        
        # Set window properties
        self.setWindowTitle("Image Compression Tool")
        self.setGeometry(100, 100, 800, 600)
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
        """)
    
    def setup_ui(self):
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
        self.input_dir_label.setStyleSheet("padding: 8px; background-color: white; border: 1px solid #ccc; border-radius: 4px;")
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
        
        # Compression settings
        settings_group = QGroupBox("Compression Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Quality setting
        settings_layout.addWidget(QLabel("JPEG Quality:"), 0, 0)
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(1, 100)
        self.quality_spinbox.setValue(85)
        self.quality_spinbox.setSuffix("%")
        self.quality_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        settings_layout.addWidget(self.quality_spinbox, 0, 1)
        
        # Max largest side
        settings_layout.addWidget(QLabel("Max Largest Side:"), 1, 0)
        self.max_largest_spinbox = QSpinBox()
        self.max_largest_spinbox.setRange(100, 10000)
        self.max_largest_spinbox.setValue(1920)
        self.max_largest_spinbox.setSuffix(" px")
        self.max_largest_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        settings_layout.addWidget(self.max_largest_spinbox, 1, 1)
        
        # Max smallest side
        settings_layout.addWidget(QLabel("Max Smallest Side:"), 2, 0)
        self.max_smallest_spinbox = QSpinBox()
        self.max_smallest_spinbox.setRange(100, 10000)
        self.max_smallest_spinbox.setValue(1080)
        self.max_smallest_spinbox.setSuffix(" px")
        self.max_smallest_spinbox.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        settings_layout.addWidget(self.max_smallest_spinbox, 2, 1)
        
        # Output format
        settings_layout.addWidget(QLabel("Output Format:"), 3, 0)
        from PyQt6.QtWidgets import QComboBox
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "WebP", "AVIF"])
        self.format_combo.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        settings_layout.addWidget(self.format_combo, 3, 1)
        
        # Preserve original structure
        self.preserve_structure_checkbox = QCheckBox("Preserve folder structure")
        self.preserve_structure_checkbox.setChecked(True)
        settings_layout.addWidget(self.preserve_structure_checkbox, 4, 0, 1, 2)
        
        main_layout.addWidget(settings_group)
        
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
    
    def setup_connections(self):
        """Set up signal connections."""
        self.select_input_btn.clicked.connect(self.select_input_directory)
        self.compress_btn.clicked.connect(self.start_compression)
        self.compare_btn.clicked.connect(self.show_comparison)
    
    def select_input_directory(self):
        """Select input directory for compression."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory", "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.input_directory = Path(directory)
            self.input_dir_label.setText(str(self.input_directory))
            self.compress_btn.setEnabled(True)
            self.log_message(f"Selected input directory: {self.input_directory}")
    
    def start_compression(self):
        """Start the compression process."""
        if not hasattr(self, 'input_directory'):
            QMessageBox.warning(self, "Warning", "Please select an input directory first.")
            return
        
        # Create output directory
        output_name = f"{self.input_directory.name}_compressed_{datetime.now().strftime('%Y.%m.%d %H%M%S')}"
        self.output_directory = self.input_directory.parent / output_name
        
        # Get compression settings
        quality = self.quality_spinbox.value()
        max_largest = self.max_largest_spinbox.value()
        max_smallest = self.max_smallest_spinbox.value()
        preserve_structure = self.preserve_structure_checkbox.isChecked()
        output_format = self.format_combo.currentText()
        
        # Create compressor
        compressor = ImageCompressor(quality, max_largest, max_smallest, preserve_structure, output_format)
        
        # Create compression settings dictionary
        compression_settings = {
            'quality': quality,
            'max_largest_side': max_largest,
            'max_smallest_side': max_smallest,
            'preserve_structure': preserve_structure,
            'output_format': output_format,
            'input_directory': str(self.input_directory),
            'output_directory': str(self.output_directory)
        }
        
        # Create and start worker thread
        self.compression_worker = CompressionWorker(compressor, self.input_directory, self.output_directory, compression_settings)
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
    
    def update_progress(self, current: int, total: int):
        """Update progress bar."""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
    
    def update_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)
        self.log_message(message)
    
    def compression_finished(self, stats: dict):
        """Handle compression completion."""
        # Update UI
        self.compress_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Show completion message
        message = f"""
Compression completed successfully!

Statistics:
- Total files processed: {stats['total_files']}
- Files compressed: {stats['compressed_files']}
- Input size: {stats['input_size_mb']:.2f} MB
- Output size: {stats['output_size_mb']:.2f} MB
- Space saved: {stats['space_saved_mb']:.2f} MB
- Compression ratio: {stats['compression_ratio_percent']:.1f}%

Output directory: {self.output_directory}
        """
        
        self.log_message("Compression completed successfully!")
        QMessageBox.information(self, "Compression Complete", message)
        
        # Update status
        self.status_label.setText("Compression completed successfully!")
    
    def compression_error(self, error_message: str):
        """Handle compression error."""
        self.compress_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Compression failed")
        self.log_message(f"ERROR: {error_message}")
        QMessageBox.critical(self, "Compression Error", f"An error occurred during compression:\n\n{error_message}")
    
    def show_comparison(self):
        """Show the image comparison window."""
        if not self.output_directory or not self.output_directory.exists():
            QMessageBox.warning(self, "Warning", "Please complete compression first.")
            return
        
        try:
            # Create image pairs for comparison (original vs compressed)
            self.log_message(f"Creating pairs from: {self.output_directory}")
            self.log_message(f"Original directory: {self.input_directory}")
            image_pairs = create_image_pairs(self.output_directory, self.input_directory)
            
            if not image_pairs:
                QMessageBox.information(self, "No Images", "No image pairs found for comparison.")
                return
            
            self.log_message(f"Found {len(image_pairs)} image pairs")
            
            # Convert to ImagePair objects for the comparison module
            comparison_pairs = []
            for i, (img1_path, img2_path) in enumerate(image_pairs):
                if img1_path == img2_path:
                    # Same file (fallback case)
                    pair_name = f"Pair {i+1}: {img1_path.name}"
                    self.log_message(f"Pair {i+1}: Same file - {img1_path.name}")
                else:
                    # Original vs compressed
                    pair_name = f"Pair {i+1}: Original vs Compressed - {img1_path.name}"
                    self.log_message(f"Pair {i+1}: Original vs Compressed - {img1_path.name} vs {img2_path.name}")
                comparison_pairs.append(ImagePair(str(img1_path), str(img2_path), pair_name))
            
            # Show comparison window with settings file
            settings_file = self.output_directory / 'compression_settings.json'
            self.comparison_window = show_comparison_window(comparison_pairs, settings_file)
            self.log_message(f"Opened comparison window with {len(comparison_pairs)} image pairs")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open comparison window:\n\n{str(e)}")
            self.log_message(f"ERROR: Failed to open comparison window: {str(e)}")
    
    def log_message(self, message: str):
        """Add message to log."""
        self.log_text.append(f"[{QTimer().remainingTime()}] {message}")
        self.log_text.ensureCursorVisible()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Image Compression Tool")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()