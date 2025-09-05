from pathlib import Path

from service.image_compression import ImageCompressor


def test_collects_video_files(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_bytes(b"data")
    output_dir = tmp_path / "out"
    unsupported_dir = tmp_path / "unsupported"
    compressor = ImageCompressor(unsupported_dir=unsupported_dir)
    total, compressed, _, failed, _, videos = compressor.process_directory(input_dir, output_dir, profiles=[])
    assert total == 0
    assert compressed == 0
    assert failed == []
    assert videos == [video]
    assert not (unsupported_dir / "clip.mp4").exists()
    assert not (output_dir / "clip.mp4").exists()
