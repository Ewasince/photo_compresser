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


def test_remove_and_reset_profiles(qapp: QApplication) -> None:
    window = MainWindow()
    qapp.processEvents()

    assert len(window.profile_panels) == 1
    assert window.profile_panels[0].title == "Default"

    window.add_profile_panel()
    qapp.processEvents()
    assert len(window.profile_panels) == 2

    window.profile_panels[1].remove_btn.click()
    qapp.processEvents()
    assert len(window.profile_panels) == 1

    window.reset_settings()
    qapp.processEvents()
    assert len(window.profile_panels) == 1
    assert window.profile_panels[0].title == "Default"
