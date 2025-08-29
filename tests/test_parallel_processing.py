import os
from concurrent.futures import ThreadPoolExecutor as RealThreadPoolExecutor
from pathlib import Path
from typing import Any

from PIL import Image

from service import image_compression
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


def test_default_worker_count(tmp_path: Path, monkeypatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    Image.new("RGB", (10, 10)).save(input_dir / "img.jpg")
    output_dir = tmp_path / "out"

    called: dict[str, int] = {}

    def recording_executor(max_workers: int, *args: Any, **kwargs: Any) -> RealThreadPoolExecutor:
        called["max_workers"] = max_workers
        return RealThreadPoolExecutor(max_workers, *args, **kwargs)

    monkeypatch.setattr(image_compression, "ThreadPoolExecutor", recording_executor)

    compressor = ImageCompressor()
    compressor.process_directory(input_dir, output_dir)

    assert called["max_workers"] == os.cpu_count()
