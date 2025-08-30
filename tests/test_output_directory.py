import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from service.image_compression import ImageCompressor
from service.main import MainWindow
from service.translator import tr


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


def test_auto_update_unsupported_directory_on_output_change(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow()
    qapp.processEvents()
    window.copy_unsupported_cb.setChecked(True)
    window.copy_unsupported_separate_cb.setChecked(True)

    first_out = tmp_path / "out1"
    window.output_directory = first_out
    window.output_dir_edit.setText(str(first_out))
    qapp.processEvents()
    first_unsup = Path(window.unsupported_dir_edit.text())
    assert first_unsup.parent == first_out.parent
    assert first_unsup.name.startswith(f"{first_out.name}_{tr('not_proceed')}")

    second_out = tmp_path / "out2"
    window.output_directory = second_out
    window.output_dir_edit.setText(str(second_out))
    qapp.processEvents()
    second_unsup = Path(window.unsupported_dir_edit.text())
    assert second_unsup.parent == second_out.parent
    assert second_unsup.name.startswith(f"{second_out.name}_{tr('not_proceed')}")
    assert second_unsup != first_unsup


def test_regenerate_unsupported_directory_button(qapp: QApplication, tmp_path: Path) -> None:
    window = MainWindow()
    qapp.processEvents()
    window.copy_unsupported_cb.setChecked(True)
    window.copy_unsupported_separate_cb.setChecked(True)
    window.output_directory = tmp_path / "out"
    window.output_dir_edit.setText(str(window.output_directory))
    qapp.processEvents()
    first = Path(window.unsupported_dir_edit.text())
    first.mkdir()
    window.regen_unsupported_btn.click()
    qapp.processEvents()
    second = Path(window.unsupported_dir_edit.text())
    assert second != first
    assert not second.exists()
