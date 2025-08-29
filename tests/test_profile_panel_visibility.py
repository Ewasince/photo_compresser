import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from service.profile_panel import ProfilePanel


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_advanced_settings_visibility(qapp: QApplication) -> None:
    assert qapp is not None  # ensure fixture is used
    panel = ProfilePanel("Test")
    panel.show()
    qapp.processEvents()
    panel.advanced_box.toggle_button.click()  # expand to check visibility

    assert panel.jpeg_group.isVisible()
    assert not panel.webp_group.isVisible()
    assert not panel.avif_group.isVisible()

    panel.format_combo.setCurrentText("WEBP")
    assert not panel.jpeg_group.isVisible()
    assert panel.webp_group.isVisible()
    assert not panel.avif_group.isVisible()

    panel.format_combo.setCurrentText("AVIF")
    assert not panel.jpeg_group.isVisible()
    assert not panel.webp_group.isVisible()
    assert panel.avif_group.isVisible()
