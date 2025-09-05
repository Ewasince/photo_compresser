#!/usr/bin/env python3
"""Video conversion helpers using Adobe Media Encoder."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

AME_COMMAND = "Adobe Media Encoder"


def enqueue_videos(
    videos: Iterable[tuple[Path, Path]],
    presets_dir: Path,
) -> None:
    """Launch Adobe Media Encoder with encoding jobs.

    Parameters
    ----------
    videos:
        Iterable of ``(input_path, output_path)`` pairs.
    presets_dir:
        Directory containing ``.epr`` preset files exported from Adobe Media Encoder.
        The first preset found is used for all videos.
    """
    presets = list(presets_dir.glob("*.epr"))
    if not presets:
        logger.warning("No video presets found in %s", presets_dir)
        return

    preset = presets[0]
    for src, dst in videos:
        try:
            subprocess.Popen(  # noqa: S603
                [AME_COMMAND, str(src), str(dst), str(preset)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Queued %s for Adobe Media Encoder", src.name)
        except FileNotFoundError:
            logger.error("Adobe Media Encoder executable not found")
            break
