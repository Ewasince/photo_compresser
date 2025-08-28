#!/usr/bin/env python3
"""
Image Comparison Module
Provides functionality for comparing pairs of images with interactive features.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
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
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from service.constants import SUPPORTED_EXTENSIONS
from service.image_pair import ImagePair

FORMATS_PATTERNS = " ".join(f"*.{f}" for f in SUPPORTED_EXTENSIONS)
FORMATS_PATTERN = f"Images ({FORMATS_PATTERNS})"


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

    def get_original_image_sizes(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Get original dimensions of both images."""
        if not self.image_pair:
            return (0, 0), (0, 0)

        pixmap1 = self.image_pair.get_pixmap1()
        pixmap2 = self.image_pair.get_pixmap2()

        return (pixmap1.width(), pixmap1.height()), (pixmap2.width(), pixmap2.height())

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

        # Fill unused space with a slightly lighter shade
        painter.fillRect(display_rect, QColor("#333333"))

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

        # Draw image resolutions
        self.draw_image_resolutions(
            painter,
            display_rect,
            img1_x,
            img1_y,
            img2_x,
            img2_y,
            pixmap1.width(),
            pixmap1.height(),
            pixmap2.width(),
            pixmap2.height(),
        )

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
            # Vertical scroll (inverted)
            scroll_delta = delta // 8
            self.pan_offset.setY(self.pan_offset.y() + scroll_delta)
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

    def draw_image_resolutions(
        self,
        painter: QPainter,
        display_rect: QRect,  # noqa: ARG002
        img1_x: int,
        img1_y: int,
        img2_x: int,
        img2_y: int,
        scaled_width1: int,  # noqa: ARG002
        scaled_height1: int,
        scaled_width2: int,
        scaled_height2: int,
    ) -> None:
        """Draw image resolutions at the bottom of each image."""
        if not self.image_pair:
            return

        # Get original image sizes
        (orig_width1, orig_height1), (orig_width2, orig_height2) = self.get_original_image_sizes()

        # Set up font and colors for resolution text
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        # Background color for text (semi-transparent black)
        painter.setPen(QPen(QColor(255, 255, 255)))  # White text

        # Resolution text for left image (bottom left)
        left_resolution_text = f"{orig_width1} × {orig_height1}"
        left_text_rect = QRect(img1_x + 10, img1_y + scaled_height1 - 40, 200, 30)

        # Draw background rectangle for left resolution
        painter.fillRect(left_text_rect, QColor(0, 0, 0, 180))  # Semi-transparent black
        painter.drawText(
            left_text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            left_resolution_text,
        )

        # Resolution text for right image (bottom right)
        right_resolution_text = f"{orig_width2} × {orig_height2}"
        right_text_rect = QRect(img2_x + scaled_width2 - 210, img2_y + scaled_height2 - 40, 200, 30)

        # Draw background rectangle for right resolution
        painter.fillRect(right_text_rect, QColor(0, 0, 0, 180))  # Semi-transparent black
        painter.drawText(
            right_text_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            right_resolution_text,
        )


class ThumbnailWidget(QWidget):
    """Widget for displaying a thumbnail in the carousel."""

    clicked = pyqtSignal(ImagePair)

    def __init__(self, image_pair: ImagePair, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_pair = image_pair
        self.setFixedSize(120, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.thumbnail_size = QSize(100, 100)
        self._thumbnail: QPixmap | None = None
        self._is_loading = False
        self._spinner_angle = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._advance_spinner)

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

    def _advance_spinner(self) -> None:
        self._spinner_angle = (self._spinner_angle + 30) % 360
        self.update()

    def start_loading(self) -> None:
        if self._thumbnail is not None or self._is_loading:
            return
        self._is_loading = True
        self._spinner_timer.start(100)
        QTimer.singleShot(0, self._load_thumbnail)
        self.update()

    def _load_thumbnail(self) -> None:
        self._thumbnail = self.image_pair.create_thumbnail(self.thumbnail_size)
        self._is_loading = False
        self._spinner_timer.stop()
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:  # noqa: ARG002
        """Draw the thumbnail or a loading spinner."""
        painter = QPainter(self)

        if self._thumbnail is None:
            if self._is_loading:
                radius = 15
                center = self.rect().center()
                pen = QPen(QColor(200, 200, 200))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.drawArc(
                    center.x() - radius,
                    center.y() - radius,
                    radius * 2,
                    radius * 2,
                    self._spinner_angle * 16,
                    120 * 16,
                )
        else:
            label_height = 20
            available_height = self.height() - label_height
            x = (self.width() - self._thumbnail.width()) // 2
            y = (available_height - self._thumbnail.height()) // 2
            painter.drawPixmap(x, y, self._thumbnail)

        # Draw name below the thumbnail
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        text_rect = QRect(0, available_height, self.width(), label_height)
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
        self.container.setStyleSheet("background-color: #1a1a1a;")
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(10)

        self.setWidget(self.container)

        self.thumbnails: list[ThumbnailWidget] = []

        self.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
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
        self.thumbnails.append(thumbnail)

        delay = (len(self.thumbnails) - 1) * 100
        QTimer.singleShot(delay, thumbnail.start_loading)

    def clear(self) -> None:
        """Clear all thumbnails."""
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()
        self.thumbnails.clear()


class ComparisonWindow(QMainWindow):
    """Window for image comparison functionality."""

    def __init__(
        self,
        image_pairs: list[ImagePair] | None = None,
        settings_file: Path | None = None,
    ) -> None:
        super().__init__()
        self.image_pairs: list[ImagePair] = image_pairs or []
        self.current_pair_index = -1
        self.settings_file = settings_file

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

        self.settings_button = QPushButton("View Settings")
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addWidget(self.settings_button)
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

        # Load initial image pairs if provided
        if self.image_pairs:
            self.load_image_pairs(self.image_pairs)

    def setup_connections(self) -> None:
        """Set up signal connections."""
        self.load_button.clicked.connect(self.load_image_pair)
        self.reset_button.clicked.connect(self.reset_view)
        self.settings_button.clicked.connect(self.view_settings)
        self.carousel.thumbnail_clicked.connect(self.load_image_pair_from_thumbnail)

    def load_image_pairs(self, image_pairs: list[ImagePair]) -> None:
        """Load multiple image pairs."""
        self.image_pairs = image_pairs
        self.carousel.clear()

        for image_pair in image_pairs:
            self.carousel.add_image_pair(image_pair)

        if image_pairs:
            self.load_image_pair_from_thumbnail(image_pairs[0])

        self.update_status()

    def load_image_pair(self) -> None:
        """Load a pair of images."""
        # Load first image
        file1, _ = QFileDialog.getOpenFileName(
            self,
            "Select First Image",
            "",
            FORMATS_PATTERN,
        )

        if not file1:
            return

        # Load second image
        file2, _ = QFileDialog.getOpenFileName(
            self,
            "Select Second Image",
            "",
            FORMATS_PATTERN,
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

    def view_settings(self) -> None:
        """View compression settings."""
        if not self.settings_file or not self.settings_file.exists():
            QMessageBox.information(self, "No Settings", "No compression settings file found.")
            return

        try:
            from image_compression import load_compression_settings

            settings_data = load_compression_settings(self.settings_file)

            if not settings_data:
                QMessageBox.warning(self, "Error", "Failed to load compression settings.")
                return

            # Format settings for display
            comp_settings = settings_data.get("compression_settings", {})
            settings_text = f"""
Compression Settings:

Quality: {comp_settings.get("quality", "N/A")}%
Max Largest Side: {comp_settings.get("max_largest_side", "N/A")} px
Max Smallest Side: {comp_settings.get("max_smallest_side", "N/A")} px
Output Format: {comp_settings.get("output_format", "N/A")}
Preserve Structure: {comp_settings.get("preserve_structure", "N/A")}

Input Directory: {comp_settings.get("input_directory", "N/A")}
Output Directory: {comp_settings.get("output_directory", "N/A")}

Compression Date: {settings_data.get("compression_date", "N/A")}
Total Image Pairs: {settings_data.get("total_pairs", "N/A")}
            """

            QMessageBox.information(self, "Compression Settings", settings_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to view settings:\n\n{e!s}")


def show_comparison_window(
    image_pairs: list[ImagePair] | None = None,
    settings_file: Path | None = None,
) -> "ComparisonWindow":
    """Show the comparison window with optional image pairs."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = ComparisonWindow(image_pairs, settings_file)
    window.show()
    return window
