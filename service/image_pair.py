"""Helpers for working with pairs of images.

This module implements dynamic loading of full-size images and their previews
using LRU caches whose limits are defined in ``cache_config.toml``. A value of
``0`` disables the respective limit.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import cast

from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QBuffer, QIODevice, QSize
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from service.cache_config import CacheConfig, load_cache_config


def _load_pixmap(path: str) -> QPixmap:
    """Load an image file into a :class:`QPixmap`."""

    image = Image.open(path).convert("RGBA")
    return QPixmap.fromImage(ImageQt(image).copy())


def _create_preview(path: str, width: int, height: int) -> QImage:
    """Create a lightweight preview for the given image path."""

    image = Image.open(path).convert("RGBA")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    return ImageQt(image).copy()


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


def _create_combined_preview(path1: str, path2: str, size: QSize) -> QImage:
    key = f"{path1}|{path2}|{size.width()}x{size.height()}"
    if key in _PREVIEW_CACHE:
        _PREVIEW_CACHE.move_to_end(key)
        return _PREVIEW_CACHE[key]

    thumb_width = size.width() // 2
    thumb_height = size.height()

    image1 = _create_preview(path1, thumb_width, thumb_height)
    image2 = _create_preview(path2, thumb_width, thumb_height)

    combined = QImage(size, QImage.Format.Format_RGBA8888)
    combined.fill(QColor("#333333"))
    painter = QPainter(combined)

    x1 = (thumb_width - image1.width()) // 2
    y1 = (thumb_height - image1.height()) // 2
    painter.drawImage(x1, y1, image1)

    x2 = thumb_width + (thumb_width - image2.width()) // 2
    y2 = (thumb_height - image2.height()) // 2
    painter.drawImage(x2, y2, image2)

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

    def __post_init__(self) -> None:  # pragma: no cover - simple post-init
        if not self.name:
            self.name = f"{os.path.basename(self.image1_path)} vs {os.path.basename(self.image2_path)}"

    def get_pixmap1(self) -> QPixmap:
        """Get the first image pixmap using the cache."""

        return _get_cached_pixmap(self.image1_path)

    def get_pixmap2(self) -> QPixmap:
        """Get the second image pixmap using the cache."""

        return _get_cached_pixmap(self.image2_path)

    def create_thumbnail(self, size: QSize | None = None) -> QImage:
        size = size or QSize(100, 100)
        return _create_combined_preview(self.image1_path, self.image2_path, size)

    def create_thumbnail_bytes(self, size: tuple[int, int] | QSize | None = None) -> bytes:
        """Create a thumbnail and return it as PNG-encoded bytes."""
        if size is None:
            qsize = QSize(100, 100)
        elif isinstance(size, tuple):
            qsize = QSize(*size)
        else:
            qsize = size
        image = _create_combined_preview(self.image1_path, self.image2_path, qsize)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        return cast(bytes, buffer.data())
