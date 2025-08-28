"""Helpers for working with pairs of images.

This module implements dynamic loading of full-size images with an LRU cache
whose limit is defined in ``cache_config.toml``. A value of 0 disables the
limit. Previews are generated on demand without caching to avoid interface
freezes.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass

from PIL import Image
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from service.cache_config import CacheConfig, load_cache_config


def _load_pixmap(path: str) -> QPixmap:
    """Load an image file into a :class:`QPixmap`."""

    image = Image.open(path).convert("RGBA")
    data = image.tobytes()
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def _create_preview(path: str, width: int, height: int) -> QPixmap:
    """Create a lightweight preview for the given image path."""

    image = Image.open(path).convert("RGBA")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    data = image.tobytes()
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


CONFIG: CacheConfig = load_cache_config()
_IMAGE_CACHE: OrderedDict[str, QPixmap] = OrderedDict()


def _get_cached_pixmap(path: str) -> QPixmap:
    if path in _IMAGE_CACHE:
        _IMAGE_CACHE.move_to_end(path)
        return _IMAGE_CACHE[path]

    pixmap = _load_pixmap(path)
    if CONFIG.max_loaded_images > 0 and len(_IMAGE_CACHE) >= CONFIG.max_loaded_images:
        _IMAGE_CACHE.popitem(last=False)
    _IMAGE_CACHE[path] = pixmap
    return pixmap


def _create_combined_preview(path1: str, path2: str, size: QSize) -> QPixmap:
    thumb_width = size.width() // 2
    thumb_height = size.height()

    pixmap1 = _create_preview(path1, thumb_width, thumb_height)
    pixmap2 = _create_preview(path2, thumb_width, thumb_height)

    combined = QPixmap(size)
    combined.fill(QColor("#333333"))
    painter = QPainter(combined)

    x1 = (thumb_width - pixmap1.width()) // 2
    y1 = (thumb_height - pixmap1.height()) // 2
    painter.drawPixmap(x1, y1, pixmap1)

    x2 = thumb_width + (thumb_width - pixmap2.width()) // 2
    y2 = (thumb_height - pixmap2.height()) // 2
    painter.drawPixmap(x2, y2, pixmap2)

    pen = QPen(QColor(100, 100, 100), 2)
    painter.setPen(pen)
    painter.drawLine(thumb_width, 0, thumb_width, thumb_height)
    painter.end()

    return combined


@dataclass(slots=True)
class ImagePair:
    image1_path: str
    image2_path: str
    name: str = ""

    def __post_init__(self) -> None:  # pragma: no cover - simple post-init
        if not self.name:
            self.name = f"{os.path.basename(self.image1_path)} vs {os.path.basename(self.image2_path)}"

    def get_pixmap1(self) -> QPixmap:
        """Get the first image pixmap using the cache."""

        return _get_cached_pixmap(self.image1_path)

    def get_pixmap2(self) -> QPixmap:
        """Get the second image pixmap using the cache."""

        return _get_cached_pixmap(self.image2_path)

    def create_thumbnail(self, size: QSize | None = None) -> QPixmap:
        size = size or QSize(100, 100)
        return _create_combined_preview(self.image1_path, self.image2_path, size)
