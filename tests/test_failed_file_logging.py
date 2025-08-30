import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from service.image_compression import (
    ImageCompressor,
    load_compression_settings,
    save_compression_settings,
)


def test_failed_file_logging(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    bad_file = input_dir / "bad.jpg"
    bad_file.write_text("not an image")
    output_dir = tmp_path / "out"
    compressor = ImageCompressor()
    total, compressed, _, failed, _ = compressor.process_directory(input_dir, output_dir)
    assert total == 1
    assert compressed == 0
    assert len(failed) == 1
    failed_path, error = failed[0]
    assert failed_path == bad_file
    assert error
    stats = compressor.get_compression_stats(input_dir, output_dir, [], [failed_path])
    stats["total_files"] = total
    stats["compressed_files"] = compressed
    stats["failed_files_count"] = len(failed)
    save_compression_settings(output_dir, {}, [], stats, failed)
    data = load_compression_settings(output_dir / "compression_settings.json")
    assert data is not None
    assert data["failed_files"][0]["path"].endswith("bad.jpg")
    assert data["failed_files"][0]["error"]
    assert data["stats"]["failed_files_count"] == 1
