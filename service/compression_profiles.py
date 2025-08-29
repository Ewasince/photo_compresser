"""Utilities for working with compression profiles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from PIL import ExifTags, Image


@dataclass(slots=True)
class ProfileConditions:
    """Conditions for selecting a compression profile."""

    max_input_smallest_side: int | None = None
    max_input_largest_side: int | None = None
    max_input_pixels: int | None = None
    min_aspect_ratio: float | None = None
    max_aspect_ratio: float | None = None
    orientation: str | None = None
    input_formats: list[str] | None = None
    requires_transparency: bool | None = None
    max_input_bytes: int | None = None
    required_exif: dict[str, Any] | None = None

    def matches(
        self,
        width: int,
        height: int,
        *,
        image_format: str | None = None,
        has_transparency: bool | None = None,
        file_size: int | None = None,
        exif: dict[str, Any] | None = None,
    ) -> bool:
        """Return ``True`` if the image properties satisfy the conditions."""
        smallest_side = min(width, height)
        largest_side = max(width, height)
        pixels = width * height
        aspect_ratio = width / height
        orientation = "square" if width == height else ("landscape" if width > height else "portrait")

        conditions = [
            self.max_input_smallest_side is None or smallest_side <= self.max_input_smallest_side,
            self.max_input_largest_side is None or largest_side <= self.max_input_largest_side,
            self.max_input_pixels is None or pixels <= self.max_input_pixels,
            self.min_aspect_ratio is None or aspect_ratio >= self.min_aspect_ratio,
            self.max_aspect_ratio is None or aspect_ratio <= self.max_aspect_ratio,
            self.orientation is None or orientation == self.orientation,
            self.input_formats is None
            or (image_format is not None and image_format.upper() in [f.upper() for f in self.input_formats]),
            self.requires_transparency is None
            or (has_transparency is not None and has_transparency == self.requires_transparency),
            self.max_input_bytes is None or (file_size is not None and file_size <= self.max_input_bytes),
            not self.required_exif
            or (exif is not None and all(exif.get(k) == v for k, v in self.required_exif.items())),
        ]
        return all(conditions)


@dataclass(slots=True)
class CompressionProfile:
    """Compression settings with optional selection conditions."""

    name: str
    quality: int = 75
    max_largest_side: int | None = None
    max_smallest_side: int | None = None
    output_format: str = "JPEG"
    preserve_structure: bool = True
    jpeg_params: dict[str, Any] = field(default_factory=dict)
    webp_params: dict[str, Any] = field(default_factory=dict)
    avif_params: dict[str, Any] = field(default_factory=dict)
    conditions: ProfileConditions = field(default_factory=ProfileConditions)


def save_profiles(profiles: Sequence[CompressionProfile], file_path: Path) -> Path:
    """Save compression profiles to ``file_path`` in JSON format."""
    data = [asdict(profile) for profile in profiles]
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return file_path


def load_profiles(file_path: Path) -> list[CompressionProfile]:
    """Load compression profiles from ``file_path``."""
    if not file_path.exists():
        return []
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    profiles: list[CompressionProfile] = []
    for item in raw:
        cond = ProfileConditions(**item.get("conditions", {}))
        profile = CompressionProfile(
            name=item["name"],
            quality=item.get("quality", 75),
            max_largest_side=item.get("max_largest_side"),
            max_smallest_side=item.get("max_smallest_side"),
            output_format=item.get("output_format", "JPEG"),
            preserve_structure=item.get("preserve_structure", True),
            jpeg_params=item.get("jpeg_params", {}),
            webp_params=item.get("webp_params", {}),
            avif_params=item.get("avif_params", {}),
            conditions=cond,
        )
        profiles.append(profile)
    return profiles


def select_profile(
    image: Path | str | Image.Image, profiles: Sequence[CompressionProfile]
) -> CompressionProfile | None:
    """Return the first profile whose conditions match the image."""
    file_size: int | None = None
    if isinstance(image, str | Path):
        path = Path(image)
        file_size = path.stat().st_size if path.exists() else None
        with Image.open(path) as img:
            width, height = img.size
            image_format = (img.format or "").upper()
            has_transparency = "A" in img.getbands() or "transparency" in img.info
            exif = {ExifTags.TAGS.get(k, str(k)): v for k, v in img.getexif().items()}
    else:
        width, height = image.size
        image_format = (image.format or "").upper()
        has_transparency = "A" in image.getbands() or "transparency" in image.info
        exif = {ExifTags.TAGS.get(k, str(k)): v for k, v in image.getexif().items()}
    for profile in profiles:
        if profile.conditions.matches(
            width,
            height,
            image_format=image_format,
            has_transparency=has_transparency,
            file_size=file_size,
            exif=exif,
        ):
            return profile
    return None
