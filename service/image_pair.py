import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Hashable, TypeVar

from PIL import Image
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QImage,
    QImageReader,
    QPainter,
    QPen,
    QPixmap,
)


def pixmap_from_heic(path: str) -> QPixmap:
    im = Image.open(path).convert("RGBA")
    data = im.tobytes()  # байты RGBA
    qimg = QImage(data, im.width, im.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache[K: Hashable, V](OrderedDict[K, V]):
    """Simple LRU cache for limiting loaded images."""

    def __init__(self, max_size: int) -> None:
        super().__init__()
        self.max_size = max_size

    def get(self, key: K) -> V | None:  # type: ignore[override]
        if key in self:
            self.move_to_end(key)
            return super().__getitem__(key)
        return None

    def put(self, key: K, value: V) -> None:
        self[key] = value
        self.move_to_end(key)
        if self.max_size > 0 and len(self) > self.max_size:
            self.popitem(last=False)


def _load_limits() -> tuple[int, int]:
    """Load cache limits from viewer_config.json."""
    config_path = Path(__file__).with_name("viewer_config.json")
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return int(data.get("max_images_in_memory", 0)), int(data.get("max_thumbnails_in_memory", 0))
        except Exception:  # pragma: no cover - fallback to defaults
            return 0, 0
    return 0, 0


MAX_IMAGES, MAX_THUMBS = _load_limits()
_image_cache: LRUCache[str, QPixmap] = LRUCache(MAX_IMAGES)
_thumb_cache: LRUCache[tuple[str, str, int, int], QPixmap] = LRUCache(MAX_THUMBS)


def _load_pixmap(path: str) -> QPixmap:
    """Load full-resolution pixmap with caching."""
    cached = _image_cache.get(path)
    if cached is not None:
        return cached
    suffix = Path(path).suffix.lower()
    pixmap = pixmap_from_heic(path) if suffix in {".heic", ".heif"} else QPixmap(path)
    _image_cache.put(path, pixmap)
    return pixmap


def _load_preview(path: str, size: QSize) -> QPixmap:
    """Load scaled preview pixmap without keeping full image."""
    suffix = Path(path).suffix.lower()
    if suffix in {".heic", ".heif"}:
        pix = pixmap_from_heic(path)
        return pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    orig_size = reader.size()
    if orig_size.width() > 0 and orig_size.height() > 0:
        scale = min(size.width() / orig_size.width(), size.height() / orig_size.height())
        if scale < 1.0:
            reader.setScaledSize(QSize(int(orig_size.width() * scale), int(orig_size.height() * scale)))
    image = reader.read()
    pix = QPixmap.fromImage(image) if not image.isNull() else QPixmap(path)
    return pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def _load_thumbnail(path1: str, path2: str, size: QSize) -> QPixmap:
    """Create or retrieve a cached thumbnail for an image pair."""
    key = (path1, path2, size.width(), size.height())
    cached = _thumb_cache.get(key)
    if cached is not None:
        return cached

    combined = QPixmap(size)
    combined.fill(Qt.GlobalColor.white)
    painter = QPainter(combined)

    thumb_width = size.width() // 2
    thumb_height = size.height()

    scaled1 = _load_preview(path1, QSize(thumb_width, thumb_height))
    x1 = (thumb_width - scaled1.width()) // 2
    y1 = (thumb_height - scaled1.height()) // 2
    painter.drawPixmap(x1, y1, scaled1)

    scaled2 = _load_preview(path2, QSize(thumb_width, thumb_height))
    x2 = thumb_width + (thumb_width - scaled2.width()) // 2
    y2 = (thumb_height - scaled2.height()) // 2
    painter.drawPixmap(x2, y2, scaled2)

    pen = QPen(QColor(100, 100, 100), 2)
    painter.setPen(pen)
    painter.drawLine(thumb_width, 0, thumb_width, thumb_height)

    painter.end()
    _thumb_cache.put(key, combined)
    return combined


class ImagePair:
    def __init__(self, image1_path: str, image2_path: str, name: str = "") -> None:
        self.image1_path = image1_path
        self.image2_path = image2_path
        self.name = name or f"{os.path.basename(image1_path)} vs {os.path.basename(image2_path)}"

    def get_pixmap1(self) -> QPixmap:
        """Get the first image pixmap, loading it if necessary."""
        return _load_pixmap(self.image1_path)

    def get_pixmap2(self) -> QPixmap:
        """Get the second image pixmap, loading it if necessary."""
        return _load_pixmap(self.image2_path)

    def get_cached_thumbnail(self, size: QSize | None = None) -> QPixmap | None:
        """Return a cached thumbnail if available without loading from disk."""
        size = size or QSize(100, 100)
        key = (self.image1_path, self.image2_path, size.width(), size.height())
        return _thumb_cache.get(key)

    def create_thumbnail(self, size: QSize | None = None) -> QPixmap:
        size = size or QSize(100, 100)
        """Create a thumbnail showing both images side by side."""
        return _load_thumbnail(self.image1_path, self.image2_path, size)
