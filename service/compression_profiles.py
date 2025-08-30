"""Utilities for working with compression profiles."""

from __future__ import annotations

import json
import subprocess
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
            self._match(self.smallest_side, smallest_side),
            self._match(self.largest_side, largest_side),
            self._match(self.pixel_count, pixels),
            self._match(self.aspect_ratio, aspect_ratio),
            self.orientation is None or orientation == self.orientation,
            self.input_formats is None
            or (image_format is not None and image_format.upper() in [f.upper() for f in self.input_formats]),
            self.requires_transparency is None
            or (has_transparency is not None and has_transparency == self.requires_transparency),
            self._match(self.file_size, file_size),
            not self.required_exif
            or (exif is not None and all(exif.get(k) == v for k, v in self.required_exif.items())),
        ]
        return all(conditions)

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
    image: Path | str | Image.Image, profiles: Sequence[CompressionProfile]
) -> CompressionProfile | None:
    """Return the first profile whose conditions match the image.

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
    for profile in reversed(profiles):
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


# --- Video profile support -------------------------------------------------


@dataclass(slots=True)
class VideoProfileConditions:
    """Conditions for selecting a video compression profile."""

    width: NumericCondition | None = None
    height: NumericCondition | None = None
    duration: NumericCondition | None = None
    frame_rate: NumericCondition | None = None
    input_formats: list[str] | None = None
    file_size: NumericCondition | None = None

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

    def matches(
        self,
        *,
        width: int,
        height: int,
        duration: float | None = None,
        frame_rate: float | None = None,
        video_format: str | None = None,
        file_size: int | None = None,
    ) -> bool:
        conditions = [
            self._match(self.width, width),
            self._match(self.height, height),
            self._match(self.duration, duration),
            self._match(self.frame_rate, frame_rate),
            self.input_formats is None
            or (video_format is not None and video_format.upper() in [f.upper() for f in self.input_formats]),
            self._match(self.file_size, file_size),
        ]
        return all(conditions)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VideoProfileConditions:
        def _nc(key: str) -> NumericCondition | None:
            val = data.get(key)
            return NumericCondition(**val) if isinstance(val, dict) else None

        return cls(
            width=_nc("width"),
            height=_nc("height"),
            duration=_nc("duration"),
            frame_rate=_nc("frame_rate"),
            input_formats=data.get("input_formats"),
            file_size=_nc("file_size"),
        )


@dataclass(slots=True)
class VideoCompressionProfile:
    """Compression settings for videos with optional selection conditions."""

    name: str
    bitrate: str | None = None
    max_width: int | None = None
    max_height: int | None = None
    output_format: str = "mp4"
    codec: str = "libx264"
    advanced_params: dict[str, Any] = field(default_factory=dict)
    conditions: VideoProfileConditions = field(default_factory=VideoProfileConditions)


def save_video_profiles(profiles: Sequence[VideoCompressionProfile], file_path: Path) -> Path:
    """Save video compression profiles to ``file_path``."""

    data = [asdict(profile) for profile in profiles]
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return file_path


def load_video_profiles(file_path: Path) -> list[VideoCompressionProfile]:
    """Load video compression profiles from ``file_path``."""

    if not file_path.exists():
        return []
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    profiles: list[VideoCompressionProfile] = []
    for item in raw:
        cond = VideoProfileConditions.from_dict(item.get("conditions", {}))
        profile = VideoCompressionProfile(
            name=item["name"],
            bitrate=item.get("bitrate"),
            max_width=item.get("max_width"),
            max_height=item.get("max_height"),
            output_format=item.get("output_format", "mp4"),
            codec=item.get("codec", "libx264"),
            advanced_params=item.get("advanced_params", {}),
            conditions=cond,
        )
        profiles.append(profile)
    return profiles


def _probe_video(path: Path) -> dict[str, Any]:
    """Return basic video information using ``ffprobe``."""

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
    data = json.loads(result.stdout or "{}")
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})
    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))
    duration = float(fmt.get("duration", 0)) if fmt.get("duration") else None
    size = int(fmt.get("size", 0)) if fmt.get("size") else None
    fr_str = stream.get("avg_frame_rate", "0/0")
    num, den = fr_str.split("/")
    frame_rate = float(num) / float(den) if den != "0" else None
    return {
        "width": width,
        "height": height,
        "duration": duration,
        "frame_rate": frame_rate,
        "size": size,
    }


def select_video_profile(
    path: Path | str, profiles: Sequence[VideoCompressionProfile]
) -> VideoCompressionProfile | None:
    """Return the first video profile whose conditions match the video."""

    info = _probe_video(Path(path))
    extension = Path(path).suffix.lstrip(".").upper()
    for profile in reversed(profiles):
        if profile.conditions.matches(
            width=info["width"],
            height=info["height"],
            duration=info["duration"],
            frame_rate=info["frame_rate"],
            video_format=extension,
            file_size=info["size"],
        ):
            return profile
    return None
