#!/usr/bin/env python3
"""
Image Comparison Viewer
A PyQt6 application for comparing pairs of images with interactive features.
"""

import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from service.constants import SUPPORTED_EXTENSIONS
from service.file_utils import format_timedelta
from service.image_pair import ImagePair


class ComparisonViewer(QWidget):
    """Main widget for displaying and comparing images."""

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Image data
        self.image_pair: ImagePair | None = None
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.slider_position = 0.5  # 0.0 = left, 1.0 = right

        # Mouse interaction state
        self.is_panning = False
        self.is_dragging_slider = False
        self.last_mouse_pos = QPoint()

        # Minimum zoom and pan limits
        self.min_zoom = 0.1
        self.max_zoom = 10.0

        # Set up the widget
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
        """)

    def set_image_pair(self, image_pair: ImagePair) -> None:
        """Set the image pair to display."""
        self.image_pair = image_pair
        self.reset_view()
        self.update()

    def reset_view(self) -> None:
        """Reset zoom and pan to fit images."""
        if not self.image_pair:
            return

        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.slider_position = 0.5
        self.update()

    def get_display_rect(self) -> QRect:
        """Get the rectangle where images should be displayed."""
        return self.rect().adjusted(10, 10, -10, -10)

    def get_scaled_pixmaps(self) -> tuple[QPixmap, QPixmap]:
        """Get the scaled pixmaps for both images."""
        if not self.image_pair:
            return QPixmap(), QPixmap()

        pixmap1 = self.image_pair.get_pixmap1()
        pixmap2 = self.image_pair.get_pixmap2()

        # Check if pixmaps are valid
        if pixmap1.isNull() or pixmap2.isNull():
            return QPixmap(), QPixmap()

        # Scale both images to the same size for comparison
        display_rect = self.get_display_rect()
        target_size = display_rect.size()

        # Ensure target size is valid
        if target_size.width() <= 0 or target_size.height() <= 0:
            return QPixmap(), QPixmap()

        scaled1 = pixmap1.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled2 = pixmap2.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Apply zoom with safety checks
        if self.zoom_factor != 1.0 and self.zoom_factor > 0:
            try:
                zoomed_size = scaled1.size() * self.zoom_factor
                # Ensure zoomed size is reasonable
                if (
                    zoomed_size.width() > 0
                    and zoomed_size.height() > 0
                    and zoomed_size.width() < 10000
                    and zoomed_size.height() < 10000
                ):
                    scaled1 = scaled1.scaled(
                        zoomed_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    scaled2 = scaled2.scaled(
                        zoomed_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
            except (ValueError, OverflowError):
                # If zoom calculation fails, return unscaled images
                pass

        return scaled1, scaled2

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: ARG002
        """Custom paint event for drawing the comparison view."""
        if not self.image_pair:
            # Draw placeholder
            painter = QPainter(self)
            painter.setPen(QPen(QColor(100, 100, 100)))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Load images to start comparison",
            )
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Get scaled pixmaps
        pixmap1, pixmap2 = self.get_scaled_pixmaps()
        if pixmap1.isNull() or pixmap2.isNull():
            return

        # Additional safety checks
        if pixmap1.width() <= 0 or pixmap1.height() <= 0 or pixmap2.width() <= 0 or pixmap2.height() <= 0:
            return

        # Calculate display positions
        display_rect = self.get_display_rect()
        center_x = display_rect.center().x() + self.pan_offset.x()
        center_y = display_rect.center().y() + self.pan_offset.y()

        # Calculate image positions (centered)
        img1_x = center_x - pixmap1.width() // 2
        img1_y = center_y - pixmap1.height() // 2
        img2_x = center_x - pixmap2.width() // 2
        img2_y = center_y - pixmap2.height() // 2

        # Calculate split position
        split_x = img1_x + int(pixmap1.width() * self.slider_position)

        # Draw first image (left part)
        if split_x > img1_x:
            left_rect = QRect(img1_x, img1_y, split_x - img1_x, pixmap1.height())
            painter.drawPixmap(left_rect, pixmap1, QRect(0, 0, split_x - img1_x, pixmap1.height()))

        # Draw second image (right part)
        if split_x < img2_x + pixmap2.width():
            right_rect = QRect(split_x, img2_y, img2_x + pixmap2.width() - split_x, pixmap2.height())
            right_source_x = int(split_x - img2_x)
            if right_source_x >= 0 and right_source_x < pixmap2.width():
                source_width = pixmap2.width() - right_source_x
                if source_width > 0:
                    painter.drawPixmap(
                        right_rect,
                        pixmap2,
                        QRect(right_source_x, 0, source_width, pixmap2.height()),
                    )

        # Draw thin slider handle (no line)
        handle_size = 8  # Much thinner handle
        handle_rect = QRect(
            split_x - handle_size // 2,
            center_y - handle_size // 2,
            handle_size,
            handle_size,
        )
        painter.fillRect(handle_rect, QColor(255, 255, 0))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawRect(handle_rect)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse press events."""
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on slider
            if self.is_near_slider(event.pos()):
                self.is_dragging_slider = True
            else:
                self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse release events."""
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.is_dragging_slider = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse move events."""
        if not self.image_pair or event is None:
            return

        if self.is_dragging_slider:
            # Update slider position
            display_rect = self.get_display_rect()
            pixmap1, _ = self.get_scaled_pixmaps()

            if pixmap1.width() > 0:
                center_x = display_rect.center().x() + self.pan_offset.x()
                img1_x = center_x - pixmap1.width() // 2
                relative_x = event.pos().x() - img1_x
                self.slider_position = max(0.0, min(1.0, relative_x / pixmap1.width()))
                self.update()

        elif self.is_panning:
            # Update pan offset
            delta = event.pos() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.pos()
            self.update()

        # Update cursor
        if self.is_near_slider(event.pos()):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.is_panning:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Handle mouse wheel events for zooming and scrolling."""
        if not self.image_pair or event is None:
            return

        modifiers = event.modifiers()
        delta = event.angleDelta().y()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Zoom in/out - simplified zoom calculation
            zoom_delta = 0.1 if delta > 0 else -0.1
            new_zoom = self.zoom_factor + zoom_delta

            if self.min_zoom <= new_zoom <= self.max_zoom:
                self.zoom_factor = new_zoom
                self.update()

        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Horizontal scroll
            scroll_delta = delta // 8
            self.pan_offset.setX(self.pan_offset.x() - scroll_delta)
            self.update()

        else:
            # Vertical scroll
            scroll_delta = delta // 8
            self.pan_offset.setY(self.pan_offset.y() - scroll_delta)
            self.update()

    def is_near_slider(self, pos: QPoint) -> bool:
        """Check if a position is near the slider."""
        if not self.image_pair:
            return False

        display_rect = self.get_display_rect()
        pixmap1, _ = self.get_scaled_pixmaps()

        if pixmap1.width() <= 0:
            return False

        center_x = display_rect.center().x() + self.pan_offset.x()
        img1_x = center_x - pixmap1.width() // 2
        split_x = img1_x + int(pixmap1.width() * self.slider_position)

        return abs(pos.x() - split_x) <= 15


class ThumbnailWidget(QWidget):
    """Widget for displaying a thumbnail in the carousel."""

    clicked = pyqtSignal(ImagePair)

    def __init__(self, image_pair: ImagePair, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_pair = image_pair
        self.setFixedSize(120, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create thumbnail
        self.thumbnail = image_pair.create_thumbnail(QSize(100, 100))

        self.setStyleSheet("""
            QWidget {
                border: 2px solid #444;
                border-radius: 8px;
                background-color: #333;
                margin: 5px;
            }
            QWidget:hover {
                border-color: #666;
                background-color: #444;
            }
        """)

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: ARG002
        """Draw the thumbnail."""
        painter = QPainter(self)

        # Draw thumbnail centered
        x = (self.width() - self.thumbnail.width()) // 2
        y = (self.height() - self.thumbnail.height()) // 2
        painter.drawPixmap(x, y, self.thumbnail)

        # Draw name at bottom
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        text_rect = QRect(0, self.height() - 20, self.width(), 20)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.image_pair.name[:15] + "..." if len(self.image_pair.name) > 15 else self.image_pair.name,
        )

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle click events."""
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_pair)


class ThumbnailCarousel(QScrollArea):
    """Horizontal scroll area for displaying image pair thumbnails."""

    thumbnail_clicked = pyqtSignal(ImagePair)

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(140)

        # Create container widget
        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(10)

        self.setWidget(self.container)

        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #333;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #666;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #888;
            }
        """)

    def add_image_pair(self, image_pair: ImagePair) -> None:
        """Add an image pair thumbnail to the carousel."""
        thumbnail = ThumbnailWidget(image_pair)
        thumbnail.clicked.connect(self.thumbnail_clicked.emit)
        self.container_layout.addWidget(thumbnail)

    def clear(self) -> None:
        """Clear all thumbnails."""
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()


class CompressionStatsDialog(QDialog):
    """Dialog window to display compression statistics side by side."""

    def __init__(
        self,
        stats1: dict[str, Any],
        stats2: dict[str, Any],
        settings1: dict[str, Any],
        settings2: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compression Statistics")
        layout = QGridLayout(self)

        layout.addWidget(QLabel("Metric"), 0, 0)
        layout.addWidget(QLabel("Directory 1"), 0, 1)
        layout.addWidget(QLabel("Directory 2"), 0, 2)
        layout.addWidget(QLabel("Difference"), 0, 3)

        param_label_map = {
            "output_format": "Output Format",
            "quality": "Quality",
            "progressive": "Progressive",
            "subsampling": "Subsampling",
            "optimize": "Optimize",
            "smooth": "Smooth",
            "keep_rgb": "Keep RGB",
            "lossless": "Lossless",
            "method": "Method",
            "alpha_quality": "Alpha Quality",
            "exact": "Exact",
            "speed": "Speed",
            "codec": "Codec",
            "range": "Range",
            "qmin": "Qmin",
            "qmax": "Qmax",
            "autotiling": "Autotiling",
            "tile_rows": "Tile Rows",
            "tile_cols": "Tile Cols",
        }

        def format_param_value(key: str, value: Any) -> str:
            if key == "quality" and isinstance(value, int | float):
                return f"{int(value)}%"
            if isinstance(value, bool):
                return "True" if value else "False"
            return str(value)

        def diff_param_value(key: str, val1: Any, val2: Any) -> str:
            if isinstance(val1, int | float) and isinstance(val2, int | float):
                diff = float(val1) - float(val2)
                if key == "quality":
                    return f"{diff:.2f}%" if not diff.is_integer() else f"{int(diff)}%"
                return f"{diff:.2f}" if not diff.is_integer() else str(int(diff))
            if val1 != val2:
                return "Different"
            return ""

        fmt1 = str(settings1.get("output_format", "")).lower()
        fmt2 = str(settings2.get("output_format", "")).lower()

        row = 1

        def add_param_row(key: str) -> None:
            nonlocal row
            val1 = settings1.get(key, "")
            val2 = settings2.get(key, "")
            metric_label = QLabel(param_label_map.get(key, key))
            val1_label = QLabel(format_param_value(key, val1))
            val2_label = QLabel(format_param_value(key, val2))
            diff_label = QLabel(diff_param_value(key, val1, val2))
            if val1 != val2 and (key == "output_format" or fmt1 == fmt2):
                for lbl in (metric_label, val1_label, val2_label, diff_label):
                    lbl.setStyleSheet("color: #ff5555")
            layout.addWidget(metric_label, row, 0)
            layout.addWidget(val1_label, row, 1)
            layout.addWidget(val2_label, row, 2)
            layout.addWidget(diff_label, row, 3)
            row += 1

        add_param_row("output_format")
        add_param_row("quality")

        if fmt1 == fmt2:
            format_specific = {
                "jpeg": ["progressive", "subsampling", "optimize", "smooth", "keep_rgb"],
                "webp": ["lossless", "method", "alpha_quality", "exact"],
                "avif": [
                    "subsampling",
                    "speed",
                    "codec",
                    "range",
                    "qmin",
                    "qmax",
                    "autotiling",
                    "tile_rows",
                    "tile_cols",
                ],
            }
            for key in format_specific.get(fmt1, []):
                add_param_row(key)

        label_map = {
            "input_size_mb": "Input Size",
            "output_size_mb": "Output Size",
            "space_saved_mb": "Space Saved",
            "compression_ratio_percent": "Compression Ratio",
            "total_files": "Total Files",
            "compressed_files": "Files Compressed",
            "failed_files_count": "Failed Files",
            "conversion_time": "Conversion Time",
        }

        higher_better = {
            "space_saved_mb",
            "compression_ratio_percent",
            "total_files",
            "compressed_files",
        }

        def parse_time(value: str) -> float | None:
            total = 0
            for part in value.split():
                try:
                    num = int(part[:-1])
                except ValueError:
                    return None
                unit = part[-1]
                if unit == "d":
                    total += num * 86400
                elif unit == "h":
                    total += num * 3600
                elif unit == "m":
                    total += num * 60
                elif unit == "s":
                    total += num
                else:
                    return None
            return float(total)

        def format_value(key: str, value: Any) -> str:
            if isinstance(value, int | float):
                if key.endswith("_mb"):
                    return f"{float(value):.2f} MB"
                if key == "compression_ratio_percent":
                    return f"{float(value):.2f} %"
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)
            return str(value)

        keys = sorted(set(stats1.keys()) | set(stats2.keys()))
        for key in keys:
            layout.addWidget(QLabel(label_map.get(key, key)), row, 0)
            val1 = stats1.get(key, "")
            val2 = stats2.get(key, "")
            label1 = QLabel(format_value(key, val1))
            label2 = QLabel(format_value(key, val2))

            diff_text = ""
            v1: float | None = None
            v2: float | None = None

            if isinstance(val1, int | float) and isinstance(val2, int | float):
                v1 = float(val1)
                v2 = float(val2)
                diff = v1 - v2
                if key.endswith("_mb"):
                    diff_text = f"{diff:.2f} MB"
                elif key == "compression_ratio_percent":
                    diff_text = f"{diff:.2f} %"
                elif diff.is_integer():
                    diff_text = str(int(diff))
                else:
                    diff_text = str(diff)
            elif key == "conversion_time" and isinstance(val1, str) and isinstance(val2, str):
                v1 = parse_time(val1)
                v2 = parse_time(val2)
                if v1 is not None and v2 is not None:
                    diff_seconds = v1 - v2
                    sign = "-" if diff_seconds < 0 else ""
                    diff_text = f"{sign}{format_timedelta(timedelta(seconds=abs(diff_seconds)))}"

            label_diff = QLabel(diff_text)

            layout.addWidget(label1, row, 1)
            layout.addWidget(label2, row, 2)
            layout.addWidget(label_diff, row, 3)
            row += 1

            if v1 is not None and v2 is not None:
                if key in higher_better:
                    if v1 > v2:
                        label1.setStyleSheet("background-color: #228B22; color: white;")
                    elif v2 > v1:
                        label2.setStyleSheet("background-color: #228B22; color: white;")
                elif v1 < v2:
                    label1.setStyleSheet("background-color: #228B22; color: white;")
                elif v2 < v1:
                    label2.setStyleSheet("background-color: #228B22; color: white;")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.image_pairs: list[ImagePair] = []
        self.current_pair_index = -1
        self.stats_data: (
            tuple[
                dict[str, Any],
                dict[str, Any],
                dict[str, Any],
                dict[str, Any],
            ]
            | None
        ) = None

        self.setup_ui()
        self.setup_connections()

        # Set window properties
        self.setWindowTitle("Image Comparison Viewer")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
        """)

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top controls
        controls_layout = QHBoxLayout()

        self.load_config_button = QPushButton("Load Config")
        self.load_config_button.setStyleSheet("""
            QPushButton {
                background-color: #005a9e;
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
                background-color: #004578;
            }
        """)

        self.load_button = QPushButton("Load Image Pair")
        self.load_button.setStyleSheet("""
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

        self.load_dirs_button = QPushButton("Load Directories")
        self.load_dirs_button.setStyleSheet("""
            QPushButton {
                background-color: #008272;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #108775;
            }
            QPushButton:pressed {
                background-color: #006f5f;
            }
        """)

        self.reset_button = QPushButton("Reset View")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QPushButton:pressed {
                background-color: #555;
            }
        """)

        self.stats_button = QPushButton("Compare Stats")
        self.stats_button.setEnabled(False)
        self.stats_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)

        controls_layout.addWidget(self.load_config_button)
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.load_dirs_button)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addWidget(self.stats_button)
        controls_layout.addStretch()

        # Status label
        self.status_label = QLabel("No images loaded")
        self.status_label.setStyleSheet("color: #ccc; font-size: 12px;")
        controls_layout.addWidget(self.status_label)

        main_layout.addLayout(controls_layout)

        # Comparison viewer
        self.viewer = ComparisonViewer()
        main_layout.addWidget(self.viewer, 1)

        # Thumbnail carousel
        self.carousel = ThumbnailCarousel()
        main_layout.addWidget(self.carousel)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        self.load_config_button.clicked.connect(self.load_config)
        self.load_button.clicked.connect(self.load_image_pair)
        self.load_dirs_button.clicked.connect(self.load_directories)
        self.reset_button.clicked.connect(self.reset_view)
        self.stats_button.clicked.connect(self.show_stats)
        self.carousel.thumbnail_clicked.connect(self.load_image_pair_from_thumbnail)

    def load_image_pair(self) -> None:
        """Load a pair of images."""
        # Load first image
        file1, _ = QFileDialog.getOpenFileName(
            self,
            "Select First Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)",
        )

        if not file1:
            return

        # Load second image
        file2, _ = QFileDialog.getOpenFileName(
            self,
            "Select Second Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)",
        )

        if not file2:
            return

        # Create image pair
        image_pair = ImagePair(file1, file2)
        self.image_pairs.append(image_pair)

        # Add to carousel
        self.carousel.add_image_pair(image_pair)

        # Load into viewer
        self.load_image_pair_from_thumbnail(image_pair)

        self.update_status()

    def clear_pairs(self) -> None:
        """Clear loaded image pairs and thumbnails."""
        self.image_pairs.clear()
        self.carousel.clear()
        self.current_pair_index = -1
        self.viewer.image_pair = None
        self.viewer.update()
        self.stats_data = None
        self.stats_button.setEnabled(False)
        self.update_status()

    def load_config(self) -> None:
        """Load image pairs from a compression settings file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Config", "", "JSON Files (*.json)")
        if not file_path:
            return
        self.load_config_from_path(Path(file_path))

    def load_config_from_path(self, path: Path) -> None:
        try:
            with path.open() as f:
                data = json.load(f)
        except Exception:
            return
        self.clear_pairs()
        for pair in data.get("image_pairs", []):
            orig = pair.get("original")
            comp = pair.get("compressed")
            if orig and comp:
                name = pair.get("original_name", Path(orig).name)
                image_pair = ImagePair(orig, comp, name)
                self.image_pairs.append(image_pair)
                self.carousel.add_image_pair(image_pair)
        if self.image_pairs:
            self.load_image_pair_from_thumbnail(self.image_pairs[0])
        self.update_status()

    def load_directories(self) -> None:
        """Load image pairs from two directories."""
        dir1 = QFileDialog.getExistingDirectory(self, "Select First Directory")
        if not dir1:
            return
        dir2 = QFileDialog.getExistingDirectory(self, "Select Second Directory")
        if not dir2:
            return
        self.load_directories_from_paths(Path(dir1), Path(dir2))

    def load_directories_from_paths(self, dir1: Path, dir2: Path) -> None:
        self.clear_pairs()
        stats1_file = dir1 / "compression_settings.json"
        stats2_file = dir2 / "compression_settings.json"
        stats1: Path | None = stats1_file if stats1_file.exists() else None
        stats2: Path | None = stats2_file if stats2_file.exists() else None

        for file1 in dir1.rglob("*"):
            if not file1.is_file() or file1.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            rel = file1.relative_to(dir1)
            file2 = dir2 / rel
            if not file2.exists():
                for ext in SUPPORTED_EXTENSIONS:
                    candidate = file2.with_suffix(ext)
                    if candidate.exists():
                        file2 = candidate
                        break
            if file2.exists():
                pair_name = rel.as_posix()
                image_pair = ImagePair(str(file1), str(file2), pair_name)
                self.image_pairs.append(image_pair)
                self.carousel.add_image_pair(image_pair)

        if self.image_pairs:
            self.load_image_pair_from_thumbnail(self.image_pairs[0])

        if stats1 and stats2:
            try:
                with stats1.open() as f1, stats2.open() as f2:
                    data1 = json.load(f1)
                    data2 = json.load(f2)
                self.stats_data = (
                    data1.get("stats", {}),
                    data2.get("stats", {}),
                    data1.get("compression_settings", {}),
                    data2.get("compression_settings", {}),
                )
                self.stats_button.setEnabled(True)
            except Exception:
                self.stats_data = None
                self.stats_button.setEnabled(False)
        else:
            self.stats_data = None
            self.stats_button.setEnabled(False)

        self.update_status()

    def show_stats(self) -> None:
        """Show compression statistics comparison dialog."""
        if not self.stats_data:
            return
        dialog = CompressionStatsDialog(
            self.stats_data[0],
            self.stats_data[1],
            self.stats_data[2],
            self.stats_data[3],
            self,
        )
        dialog.exec()

    def load_image_pair_from_thumbnail(self, image_pair: ImagePair) -> None:
        """Load an image pair from a thumbnail click."""
        self.viewer.set_image_pair(image_pair)
        self.current_pair_index = self.image_pairs.index(image_pair)
        self.update_status()

    def reset_view(self) -> None:
        """Reset the viewer to fit images."""
        self.viewer.reset_view()

    def update_status(self) -> None:
        """Update the status label."""
        if self.image_pairs:
            current_pair = self.image_pairs[self.current_pair_index] if self.current_pair_index >= 0 else None
            if current_pair:
                self.status_label.setText(
                    f"Showing: {current_pair.name} ({self.current_pair_index + 1}/{len(self.image_pairs)})"
                )
            else:
                self.status_label.setText(f"Loaded {len(self.image_pairs)} image pairs")
        else:
            self.status_label.setText("No images loaded")


def main() -> None:
    """Main application entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Image Comparison Viewer")
    parser.add_argument("--config", type=str, help="Path to preview config file")
    parser.add_argument("--dir1", type=str, help="First directory for comparison")
    parser.add_argument("--dir2", type=str, help="Second directory for comparison")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Image Comparison Viewer")
    app.setApplicationVersion("1.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    if args.config:
        window.load_config_from_path(Path(args.config))
    elif args.dir1 and args.dir2:
        window.load_directories_from_paths(Path(args.dir1), Path(args.dir2))

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
