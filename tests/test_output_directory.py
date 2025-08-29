import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from service.image_compression import ImageCompressor
from service.main import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_process_directory_rejects_existing(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    Image.new("RGB", (10, 10)).save(input_dir / "a.jpg")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    compressor = ImageCompressor()
    with pytest.raises(FileExistsError):
        compressor.process_directory(input_dir, output_dir)


def test_regenerate_output_directory_button(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow()
    qapp.processEvents()
    window.input_directory = tmp_path / "in"
    window.input_directory.mkdir()
    window.regenerate_output_directory()
    first = window.output_directory
    assert first is not None
    first.mkdir()
    window.regen_output_btn.click()
    qapp.processEvents()
    assert window.output_directory != first
    assert not window.output_directory.exists()
