#!/usr/bin/env python3
"""
Image Comparison Viewer
A PyQt6 application for comparing pairs of images with interactive features.
"""

import sys

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from service.image_pair import ImagePair


class ComparisonViewer(QWidget):
    """Main widget for displaying and comparing images."""

    def __init__(self):
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

    def set_image_pair(self, image_pair: ImagePair):
        """Set the image pair to display."""
        self.image_pair = image_pair
        self.reset_view()
        self.update()

    def reset_view(self):
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

    def paintEvent(self, event):  # noqa: ARG002
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

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on slider
            if self.is_near_slider(event.pos()):
                self.is_dragging_slider = True
            else:
                self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_panning = False
            self.is_dragging_slider = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events."""
        if not self.image_pair:
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

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming and scrolling."""
        if not self.image_pair:
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

    def __init__(self, image_pair: ImagePair, parent=None):
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

    def paintEvent(self, event):  # noqa: ARG002
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

    def mousePressEvent(self, event: QMouseEvent):
        """Handle click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_pair)


class ThumbnailCarousel(QScrollArea):
    """Horizontal scroll area for displaying image pair thumbnails."""

    thumbnail_clicked = pyqtSignal(ImagePair)

    def __init__(self):
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

    def add_image_pair(self, image_pair: ImagePair):
        """Add an image pair thumbnail to the carousel."""
        thumbnail = ThumbnailWidget(image_pair)
        thumbnail.clicked.connect(self.thumbnail_clicked.emit)
        self.container_layout.addWidget(thumbnail)

    def clear(self):
        """Clear all thumbnails."""
        while self.container_layout.count():
            child = self.container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.image_pairs: list[ImagePair] = []
        self.current_pair_index = -1

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

    def setup_ui(self):
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

        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.reset_button)
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

    def setup_connections(self):
        """Set up signal connections."""
        self.load_button.clicked.connect(self.load_image_pair)
        self.reset_button.clicked.connect(self.reset_view)
        self.carousel.thumbnail_clicked.connect(self.load_image_pair_from_thumbnail)

    def load_image_pair(self):
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

    def load_image_pair_from_thumbnail(self, image_pair: ImagePair):
        """Load an image pair from a thumbnail click."""
        self.viewer.set_image_pair(image_pair)
        self.current_pair_index = self.image_pairs.index(image_pair)
        self.update_status()

    def reset_view(self):
        """Reset the viewer to fit images."""
        self.viewer.reset_view()

    def update_status(self):
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


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Image Comparison Viewer")
    app.setApplicationVersion("1.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
