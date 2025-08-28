import os

from PIL import Image
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap


def pixmap_from_heic(path: str) -> QPixmap:
    im = Image.open(path).convert("RGBA")
    data = im.tobytes()  # байты RGBA
    qimg = QImage(data, im.width, im.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class ImagePair:
    def __init__(self, image1_path: str, image2_path: str, name: str = "") -> None:
        self.image1_path = image1_path
        self.image2_path = image2_path
        self.name = name or f"{os.path.basename(image1_path)} vs {os.path.basename(image2_path)}"
        self._pixmap1: QPixmap | None = None
        self._pixmap2: QPixmap | None = None

    def get_pixmap1(self) -> QPixmap:
        """Get the first image pixmap, loading it if necessary."""
        if self._pixmap1 is None:
            self._pixmap1 = pixmap_from_heic(self.image1_path)
        return self._pixmap1

    def get_pixmap2(self) -> QPixmap:
        """Get the second image pixmap, loading it if necessary."""
        if self._pixmap2 is None:
            self._pixmap2 = pixmap_from_heic(self.image2_path)
        return self._pixmap2

    def create_thumbnail(self, size: QSize | None = None) -> QPixmap:
        size = size or QSize(100, 100)
        """Create a thumbnail showing both images side by side."""
        pixmap1 = self.get_pixmap1()
        pixmap2 = self.get_pixmap2()

        # Create a combined thumbnail with a subtle background
        combined = QPixmap(size)
        combined.fill(QColor("#333333"))

        painter = QPainter(combined)

        # Calculate thumbnail dimensions
        thumb_width = size.width() // 2
        thumb_height = size.height()

        # Draw first image (left side)
        scaled1 = pixmap1.scaled(
            thumb_width,
            thumb_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x1 = (thumb_width - scaled1.width()) // 2
        y1 = (thumb_height - scaled1.height()) // 2
        painter.drawPixmap(x1, y1, scaled1)

        # Draw second image (right side)
        scaled2 = pixmap2.scaled(
            thumb_width,
            thumb_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x2 = thumb_width + (thumb_width - scaled2.width()) // 2
        y2 = (thumb_height - scaled2.height()) // 2
        painter.drawPixmap(x2, y2, scaled2)

        # Draw divider line
        pen = QPen(QColor(100, 100, 100), 2)
        painter.setPen(pen)
        painter.drawLine(thumb_width, 0, thumb_width, thumb_height)

        painter.end()
        return combined
