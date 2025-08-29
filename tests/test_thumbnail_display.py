"""Tests for thumbnail generation ensuring previews display images."""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QSize

from service.image_pair import ImagePair


def test_thumbnail_shows_images(tmp_path) -> None:
    """Thumbnails should contain the source images, not a grey placeholder."""
    red_path = tmp_path / "red.png"
    blue_path = tmp_path / "blue.png"

    Image.new("RGBA", (50, 100), (255, 0, 0, 255)).save(red_path)
    Image.new("RGBA", (50, 100), (0, 0, 255, 255)).save(blue_path)

    pair = ImagePair(str(red_path), str(blue_path))
    thumb = pair.create_thumbnail(QSize(100, 100))

    assert thumb.size() == QSize(100, 100)
    # Middle of the left half should be red
    assert thumb.pixelColor(25, 50).red() > 200
    # Middle of the right half should be blue
    assert thumb.pixelColor(75, 50).blue() > 200
