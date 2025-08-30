import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from service.main import MainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_video_profile_panels(qapp: QApplication) -> None:
    window = MainWindow()
    qapp.processEvents()

    assert len(window.video_profile_panels) == 1
    assert window.video_profile_panels[0].title == "Default Video"

    window.add_video_profile_panel()
    qapp.processEvents()
    assert len(window.video_profile_panels) == 2

    window.video_profile_panels[1].remove_btn.click()
    qapp.processEvents()
    assert len(window.video_profile_panels) == 1

    window.reset_settings()
    qapp.processEvents()
    assert len(window.video_profile_panels) == 1
    assert window.video_profile_panels[0].title == "Default Video"
