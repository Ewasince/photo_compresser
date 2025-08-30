"""Video compression utilities using ffmpeg."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from threading import Event
from typing import Any, Callable, Sequence

from service.compression_profiles import (
    VideoCompressionProfile,
    select_video_profile,
)
from service.constants import VIDEO_EXTENSIONS
from service.file_utils import copy_times_from_src
from service.translator import tr

logger = logging.getLogger(__name__)


class VideoCompressor:
    """Simple video compressor based on ffmpeg."""

    def __init__(
        self,
        bitrate: str | None = "1000k",
        max_width: int | None = None,
        max_height: int | None = None,
        output_format: str = "mp4",
        *,
        preserve_structure: bool = True,
        copy_unsupported: bool = True,
    ) -> None:
        self.bitrate = bitrate
        self.max_width = max_width
        self.max_height = max_height
        self.output_format = output_format
        self.preserve_structure = preserve_structure
        self.copy_unsupported = copy_unsupported
        self.codec = "libx264"
        self.advanced_params: dict[str, Any] = {}

    def apply_profile(self, profile: VideoCompressionProfile) -> None:
        self.bitrate = profile.bitrate
        self.max_width = profile.max_width
        self.max_height = profile.max_height
        self.output_format = profile.output_format
        self.codec = profile.codec
        self.advanced_params = profile.advanced_params

    def set_advanced_parameters(self, **kwargs: Any) -> None:
        self.advanced_params = kwargs

    def compress_video(self, input_path: Path, output_path: Path) -> Path | None:
        cmd = ["ffmpeg", "-y", "-i", str(input_path)]
        if self.bitrate:
            cmd += ["-b:v", str(self.bitrate)]
        cmd += ["-c:v", self.codec]
        for k, v in self.advanced_params.items():
            cmd += [str(k), str(v)]
        cmd.append(str(output_path))
        try:
            subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
            copy_times_from_src(input_path, output_path)
            logger.info("Compressed video %s", input_path.name)
            return output_path
        except Exception as exc:  # pragma: no cover - log and skip
            logger.error("Failed to compress %s: %s", input_path, exc)
            return None

    def process_directory(
        self,
        input_root: Path,
        output_root: Path,
        profiles: Sequence[VideoCompressionProfile] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
        stop_event: Event | None = None,
    ) -> tuple[int, int, list[Path], list[Path]]:
        """Process directory and compress supported video files."""

        total_files = sum(1 for f in input_root.rglob("*") if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS)
        if not profiles or total_files == 0:
            return (0, 0, [], [])

        processed = 0
        compressed = 0
        compressed_paths: list[Path] = []
        failed: list[Path] = []

        for file_path in input_root.rglob("*"):
            if stop_event and stop_event.is_set():
                break
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
                if self.copy_unsupported:
                    if self.preserve_structure:
                        rel = file_path.relative_to(input_root)
                        out_file = output_root / rel
                    else:
                        out_file = output_root / file_path.name
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                    out_file.write_bytes(file_path.read_bytes())
                    copy_times_from_src(file_path, out_file)
                continue

            profile = select_video_profile(file_path, profiles) if profiles else None
            comp = VideoCompressor(
                bitrate=self.bitrate,
                max_width=self.max_width,
                max_height=self.max_height,
                output_format=self.output_format,
                preserve_structure=self.preserve_structure,
                copy_unsupported=self.copy_unsupported,
            )
            if profile:
                comp.apply_profile(profile)

            if comp.preserve_structure:
                rel = file_path.relative_to(input_root)
                out_file = output_root / rel
                out_file = out_file.with_suffix(f".{comp.output_format}")
            else:
                out_file = output_root / f"{file_path.stem}.{comp.output_format}"

            out_file.parent.mkdir(parents=True, exist_ok=True)
            saved = comp.compress_video(file_path, out_file)
            profile_name = profile.name if profile else tr("Default")
            if saved:
                compressed += 1
                compressed_paths.append(saved)
                msg = tr("Compressed video: {name} with profile {profile}").format(
                    name=file_path.name, profile=profile_name
                )
            else:
                failed.append(file_path)
                msg = tr("Failed to compress video: {name}").format(name=file_path.name)
            if log_callback:
                log_callback(msg)
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files)
            if status_callback:
                status_callback(msg)

        return (total_files, compressed, compressed_paths, failed)
