from pathlib import Path

from service.image_compression import ImageCompressor


def test_skip_unsupported_files(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "note.txt").write_text("hello", encoding="utf-8")
    output_dir = tmp_path / "output"

    compressor = ImageCompressor(copy_unsupported=False)
    compressor.process_directory(input_dir, output_dir, profiles=[])

    assert not (output_dir / "note.txt").exists()


def test_copy_unsupported_to_separate_dir(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "note.txt").write_text("hello", encoding="utf-8")
    output_dir = tmp_path / "output"
    unsupported_dir = tmp_path / "unsupported"

    compressor = ImageCompressor(copy_unsupported=True, unsupported_dir=unsupported_dir)
    compressor.process_directory(input_dir, output_dir, profiles=[])

    assert not (output_dir / "note.txt").exists()
    assert (unsupported_dir / "note.txt").exists()
