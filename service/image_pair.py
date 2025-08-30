"""Helpers for working with pairs of images.

This module implements dynamic loading of full-size images and their previews
using LRU caches whose limits are defined in ``cache_config.toml``. A value of
``0`` disables the respective limit.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass, field

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from service.cache_config import CacheConfig, load_cache_config


def _load_pixmap(path: str) -> QPixmap:
    """Load an image file into a :class:`QPixmap`."""

    image = Image.open(path).convert("RGBA")
    data = image.tobytes()
    qimg = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def _create_preview_image(path: str, width: int, height: int) -> QImage:
    """Create a lightweight preview image for the given path."""

    image = Image.open(path).convert("RGBA")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    data = image.tobytes()
    return QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()


CONFIG: CacheConfig = load_cache_config()
_IMAGE_CACHE: OrderedDict[str, QPixmap] = OrderedDict()
_PREVIEW_CACHE: OrderedDict[str, QImage] = OrderedDict()


def _get_cached_pixmap(path: str) -> QPixmap:
    if path in _IMAGE_CACHE:
        _IMAGE_CACHE.move_to_end(path)
        return _IMAGE_CACHE[path]

    pixmap = _load_pixmap(path)
    if CONFIG.max_loaded_images > 0 and len(_IMAGE_CACHE) >= CONFIG.max_loaded_images:
        _IMAGE_CACHE.popitem(last=False)
    _IMAGE_CACHE[path] = pixmap
    return pixmap


def _create_combined_preview_image(path1: str, path2: str, size: QSize) -> QImage:
    key = f"{path1}|{path2}|{size.width()}x{size.height()}"
    if key in _PREVIEW_CACHE:
        _PREVIEW_CACHE.move_to_end(key)
        return _PREVIEW_CACHE[key]

    thumb_width = size.width() // 2
    thumb_height = size.height()

    img1 = _create_preview_image(path1, thumb_width, thumb_height)
    img2 = _create_preview_image(path2, thumb_width, thumb_height)

    combined = QImage(size, QImage.Format.Format_RGBA8888)
    combined.fill(QColor("#333333"))
    painter = QPainter(combined)

    x1 = (thumb_width - img1.width()) // 2
    y1 = (thumb_height - img1.height()) // 2
    painter.drawImage(x1, y1, img1)

    x2 = thumb_width + (thumb_width - img2.width()) // 2
    y2 = (thumb_height - img2.height()) // 2
    painter.drawImage(x2, y2, img2)

    pen = QPen(QColor(100, 100, 100), 2)
    painter.setPen(pen)
    painter.drawLine(thumb_width, 0, thumb_width, thumb_height)
    painter.end()

    if CONFIG.max_loaded_previews > 0 and len(_PREVIEW_CACHE) >= CONFIG.max_loaded_previews:
        _PREVIEW_CACHE.popitem(last=False)
    _PREVIEW_CACHE[key] = combined
    return combined


@dataclass(slots=True)
class ImagePair:
    image1_path: str
    image2_path: str
    name: str = ""
    profile1: str = "Raw"
    profile2: str = "Raw"
    conditions1: dict[str, dict[str, bool]] = field(default_factory=dict)
    conditions2: dict[str, dict[str, bool]] = field(default_factory=dict)

    def __post_init__(self) -> None:  # pragma: no cover - simple post-init
        if not self.name:
            self.name = f"{os.path.basename(self.image1_path)} vs {os.path.basename(self.image2_path)}"
        if not self.profile1:
            self.profile1 = "Raw"
        if not self.profile2:
            self.profile2 = "Raw"

    def get_pixmap1(self) -> QPixmap:
        """Get the first image pixmap using the cache."""

        return _get_cached_pixmap(self.image1_path)

    def get_pixmap2(self) -> QPixmap:
        """Get the second image pixmap using the cache."""

        return _get_cached_pixmap(self.image2_path)

    def ensure_thumbnail_cached(self, size: QSize | None = None) -> None:
        size = size or QSize(100, 100)
        _create_combined_preview_image(self.image1_path, self.image2_path, size)

    def create_thumbnail(self, size: QSize | None = None) -> QPixmap:
        size = size or QSize(100, 100)
        image = _create_combined_preview_image(self.image1_path, self.image2_path, size)
        return QPixmap.fromImage(image)
