import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from service.image_comparison_viewer import ThumbnailObserver, ThumbnailRunnable


class FailingPair:
    name = "bad"

    def ensure_thumbnail_cached(self) -> None:
        raise RuntimeError("boom")


def test_thumbnail_runnable_reports_done_on_exception() -> None:
    QApplication.instance() or QApplication([])
    observer = ThumbnailObserver(1)
    finished: list[bool] = []
    loop = QEventLoop()

    def handle_finished() -> None:
        finished.append(True)
        loop.quit()

    observer.finished.connect(handle_finished)

    runnable = ThumbnailRunnable(FailingPair(), observer)
    runnable.run()

    QTimer.singleShot(100, loop.quit)
    loop.exec()

    assert finished
