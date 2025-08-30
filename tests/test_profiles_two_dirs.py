import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from service.image_comparison_viewer import MainWindow


def _create_image(dir_path: Path, name: str, color: str) -> Path:
    path = dir_path / name
    Image.new("RGB", (10, 10), color=color).save(path)
    return path


def _write_settings(dir_path: Path, image_path: Path, profile: str) -> None:
    data = {
        "image_pairs": [
            {
                "original": str(image_path),
                "compressed": str(image_path),
                "profile": profile,
                "original_name": image_path.name,
                "compressed_name": image_path.name,
            }
        ]
    }
    with (dir_path / "compression_settings.json").open("w") as f:
        json.dump(data, f)


def test_profiles_loaded_for_two_directories(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    img1 = _create_image(dir1, "img.jpg", "red")
    img2 = _create_image(dir2, "img.png", "blue")
    _write_settings(dir1, img1, "P1")
    _write_settings(dir2, img2, "P2")

    viewer = MainWindow()
    viewer._preload_thumbnails = lambda: None
    viewer.load_directories_from_paths(dir1, dir2)

    assert viewer.image_pairs
    pair = viewer.image_pairs[0]
    assert pair.profile1 == "P1"
    assert pair.profile2 == "P2"


def test_profiles_preserved_after_move(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    sub1 = src1 / "sub"
    sub2 = src2 / "sub"
    sub1.mkdir()
    sub2.mkdir()
    img1 = _create_image(sub1, "img.jpg", "red")
    img2 = _create_image(sub2, "img.jpg", "blue")
    _write_settings(src1, img1, "P1")
    _write_settings(src2, img2, "P2")

    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    src1.rename(dir1)
    src2.rename(dir2)

    viewer = MainWindow()
    viewer._preload_thumbnails = lambda: None
    viewer.load_directories_from_paths(dir1, dir2)

    assert viewer.image_pairs
    pair = viewer.image_pairs[0]
    assert pair.profile1 == "P1"
    assert pair.profile2 == "P2"
