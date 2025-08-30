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


def _write_settings(
    dir_path: Path,
    image_path: Path,
    profile: str,
    quality: int,
    conditions: dict | None = None,
) -> None:
    data = {
        "profiles": [{"name": profile, "quality": quality, "conditions": conditions or {}}],
        "image_pairs": [
            {
                "original": str(image_path),
                "compressed": str(image_path),
                "profile": profile,
                "original_name": image_path.name,
                "compressed_name": image_path.name,
            }
        ],
    }
    with (dir_path / "compression_settings.json").open("w") as f:
        json.dump(data, f)


def test_profile_tooltip_shows_parameters(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    img1 = _create_image(dir1, "img.jpg", "red")
    img2 = _create_image(dir2, "img.jpg", "blue")
    _write_settings(dir1, img1, "P1", 80, {"largest_side": {"op": "<", "value": 20}})
    _write_settings(dir2, img2, "P2", 60, {"largest_side": {"op": "<", "value": 5}})

    viewer = MainWindow()
    viewer._preload_thumbnails = lambda: None
    viewer.load_directories_from_paths(dir1, dir2)

    tooltip1 = viewer.profile_label1.toolTip()
    tooltip2 = viewer.profile_label2.toolTip()
    assert "Quality: 80" in tooltip1
    assert "Largest Side < 20" in tooltip1
    assert "✓" in tooltip1
    assert "Quality: 60" in tooltip2
    assert "Largest Side < 5" in tooltip2
    assert "✗" in tooltip2
