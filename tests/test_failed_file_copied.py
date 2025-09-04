from __future__ import annotations

import os
from pathlib import Path

from service.image_compression import ImageCompressor


def test_failed_file_copied_to_unsupported(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    bad_file = input_dir / "bad.jpg"
    bad_file.write_text("not an image", encoding="utf-8")

    # Set specific timestamps
    atime = 1_700_000_000
    mtime = 1_700_000_100
    os.utime(bad_file, (atime, mtime))
    orig_mtime = bad_file.stat().st_mtime_ns

    output_dir = tmp_path / "out"
    unsupported_dir = tmp_path / "unsupported"

    compressor = ImageCompressor(unsupported_dir=unsupported_dir)
    compressor.process_directory(input_dir, output_dir, profiles=[])

    copied = unsupported_dir / "bad.jpg"
    assert copied.exists()
    assert copied.stat().st_mtime_ns == orig_mtime
