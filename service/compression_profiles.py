"""Utilities for working with compression profiles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from PIL import ExifTags, Image


@dataclass(slots=True)
class NumericCondition:
    """Numeric comparison condition."""

    op: str
    value: float


@dataclass(slots=True)
class ProfileConditions:
    """Conditions for selecting a compression profile."""

    smallest_side: NumericCondition | None = None
    largest_side: NumericCondition | None = None
    pixel_count: NumericCondition | None = None
    aspect_ratio: NumericCondition | None = None
    orientation: str | None = None
    input_formats: list[str] | None = None
    requires_transparency: bool | None = None
    file_size: NumericCondition | None = None
    required_exif: dict[str, Any] | None = None

    @staticmethod
    def _match(cond: NumericCondition | None, actual: float | None) -> bool:
        if cond is None:
            return True
        if actual is None:
            return False
        return {
            "<": actual < cond.value,
            "<=": actual <= cond.value,
            ">": actual > cond.value,
            ">=": actual >= cond.value,
            "==": actual == cond.value,
        }.get(cond.op, False)

    def evaluate(
        self,
        width: int,
        height: int,
        *,
        image_format: str | None = None,
        has_transparency: bool | None = None,
        file_size: int | None = None,
        exif: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Return evaluation results for all active conditions."""
        smallest_side = min(width, height)
        largest_side = max(width, height)
        pixels = width * height
        aspect_ratio = width / height
        orientation = "square" if width == height else ("landscape" if width > height else "portrait")

        results: dict[str, bool] = {}
        if self.smallest_side is not None:
            results["smallest_side"] = self._match(self.smallest_side, smallest_side)
        if self.largest_side is not None:
            results["largest_side"] = self._match(self.largest_side, largest_side)
        if self.pixel_count is not None:
            results["pixel_count"] = self._match(self.pixel_count, pixels)
        if self.aspect_ratio is not None:
            results["aspect_ratio"] = self._match(self.aspect_ratio, aspect_ratio)
        if self.orientation is not None:
            results["orientation"] = orientation == self.orientation
        if self.input_formats is not None:
            results["input_formats"] = image_format is not None and image_format.upper() in [
                f.upper() for f in self.input_formats
            ]
        if self.requires_transparency is not None:
            results["requires_transparency"] = (
                has_transparency is not None and has_transparency == self.requires_transparency
            )
        if self.file_size is not None:
            results["file_size"] = self._match(self.file_size, file_size)
        if self.required_exif:
            results["required_exif"] = exif is not None and all(exif.get(k) == v for k, v in self.required_exif.items())
        return results

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
        return all(
            self.evaluate(
                width,
                height,
                image_format=image_format,
                has_transparency=has_transparency,
                file_size=file_size,
                exif=exif,
            ).values()
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileConditions:
        def _nc(key: str) -> NumericCondition | None:
            val = data.get(key)
            return NumericCondition(**val) if isinstance(val, dict) else None

        return cls(
            smallest_side=_nc("smallest_side"),
            largest_side=_nc("largest_side"),
            pixel_count=_nc("pixel_count"),
            aspect_ratio=_nc("aspect_ratio"),
            orientation=data.get("orientation"),
            input_formats=data.get("input_formats"),
            requires_transparency=data.get("requires_transparency"),
            file_size=_nc("file_size"),
            required_exif=data.get("required_exif"),
        )


@dataclass(slots=True)
class CompressionProfile:
    """Compression settings with optional selection conditions."""

    name: str
    quality: int = 75
    max_largest_side: int | None = None
    max_smallest_side: int | None = None
    output_format: str = "JPEG"
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
        cond = ProfileConditions.from_dict(item.get("conditions", {}))
        profile = CompressionProfile(
            name=item["name"],
            quality=item.get("quality", 75),
            max_largest_side=item.get("max_largest_side"),
            max_smallest_side=item.get("max_smallest_side"),
            output_format=item.get("output_format", "JPEG"),
            jpeg_params=item.get("jpeg_params", {}),
            webp_params=item.get("webp_params", {}),
            avif_params=item.get("avif_params", {}),
            conditions=cond,
        )
        profiles.append(profile)
    return profiles


def select_profile(
    image: Path | str | Image.Image,
    profiles: Sequence[CompressionProfile],
    *,
    return_condition_results: bool = False,
) -> CompressionProfile | None | tuple[CompressionProfile | None, dict[str, dict[str, bool]]]:
    """Return the first profile whose conditions match the image.

    If ``return_condition_results`` is ``True``, also return evaluation
    results for all profiles.

    Profiles are evaluated from the end of the sequence to the start so that
    lower panels in the UI take precedence over the ones above them. The top
    profile therefore acts as a default fallback.
    """
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

    results: dict[str, dict[str, bool]] = {}
    for profile in profiles:
        results[profile.name] = profile.conditions.evaluate(
            width,
            height,
            image_format=image_format,
            has_transparency=has_transparency,
            file_size=file_size,
            exif=exif,
        )

    selected: CompressionProfile | None = None
    for profile in reversed(profiles):
        if all(results[profile.name].values()):
            selected = profile
            break

    if return_condition_results:
        return selected, results
    return selected
