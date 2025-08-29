from pathlib import Path

from PIL import Image

from service.image_compression import ImageCompressor


def test_process_directory_parallel(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(3):
        Image.new("RGB", (10, 10)).save(input_dir / f"img{i}.jpg")
    output_dir = tmp_path / "out"
    compressor = ImageCompressor()
    total, compressed, _, failed = compressor.process_directory(input_dir, output_dir, num_workers=2)
    assert total == 3
    assert compressed == 3
    assert failed == []
