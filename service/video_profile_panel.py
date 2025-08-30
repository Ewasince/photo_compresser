from __future__ import annotations

import contextlib

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from service.compression_profiles import (
    NumericCondition,
    VideoCompressionProfile,
    VideoProfileConditions,
)
from service.translator import tr


class VideoProfilePanel(QWidget):
    """Panel for configuring video compression profiles."""

    remove_requested = Signal()

    def __init__(
        self,
        title: str,
        *,
        allow_conditions: bool = True,
        removable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.allow_conditions = allow_conditions
        self.removable = removable
        self._build_ui()
        self.update_translations()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        name_layout = QHBoxLayout()
        self.name_label = QLabel("🎬 " + tr("Name") + ":")
        name_layout.addWidget(self.name_label)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.title)
        name_layout.addWidget(self.name_edit)
        name_layout.addStretch()
        if self.removable:
            remove_btn = QToolButton()
            remove_btn.setText("✕")
            remove_btn.setFixedSize(16, 16)
            remove_btn.clicked.connect(self.remove_requested.emit)
            name_layout.addWidget(remove_btn)
            self.remove_btn = remove_btn
        layout.addLayout(name_layout)

        # Basic settings
        self.basic_group = QGroupBox(tr("Compression Settings"))
        grid = QGridLayout(self.basic_group)

        self.bitrate_label = QLabel(tr("Bitrate (kbps)") + ":")
        grid.addWidget(self.bitrate_label, 0, 0)
        self.bitrate = QSpinBox()
        self.bitrate.setRange(100, 100000)
        self.bitrate.setValue(1000)
        grid.addWidget(self.bitrate, 0, 1)

        self.max_width_label = QLabel(tr("Max width") + ":")
        grid.addWidget(self.max_width_label, 1, 0)
        self.max_width = QSpinBox()
        self.max_width.setRange(1, 10000)
        self.max_width.setValue(1920)
        grid.addWidget(self.max_width, 1, 1)

        self.max_height_label = QLabel(tr("Max height") + ":")
        grid.addWidget(self.max_height_label, 2, 0)
        self.max_height = QSpinBox()
        self.max_height.setRange(1, 10000)
        self.max_height.setValue(1080)
        grid.addWidget(self.max_height, 2, 1)

        self.format_label = QLabel(tr("Format") + ":")
        grid.addWidget(self.format_label, 3, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "webm"])
        grid.addWidget(self.format_combo, 3, 1)

        layout.addWidget(self.basic_group)

        # Advanced settings
        self.adv_group = QGroupBox(tr("Advanced Settings"))
        adv_grid = QGridLayout(self.adv_group)

        self.codec_label = QLabel(tr("Codec") + ":")
        adv_grid.addWidget(self.codec_label, 0, 0)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["libx264", "libx265", "libvpx-vp9"])
        adv_grid.addWidget(self.codec_combo, 0, 1)

        layout.addWidget(self.adv_group)

        # Conditions
        if self.allow_conditions:
            self.cond_group = QGroupBox(tr("Conditions"))
            cond_grid = QGridLayout(self.cond_group)

            self.cond_width_cb = QCheckBox(tr("Width") + ":")
            cond_grid.addWidget(self.cond_width_cb, 0, 0)
            self.cond_width_op = QComboBox()
            self.cond_width_op.addItems(["<=", "<", ">=", ">", "=="])
            self.cond_width_op.setEnabled(False)
            cond_grid.addWidget(self.cond_width_op, 0, 1)
            self.cond_width = QSpinBox()
            self.cond_width.setRange(1, 10000)
            self.cond_width.setEnabled(False)
            cond_grid.addWidget(self.cond_width, 0, 2)
            self.cond_width_cb.stateChanged.connect(
                lambda s: self._toggle_widgets(s, self.cond_width, self.cond_width_op)
            )

            self.cond_height_cb = QCheckBox(tr("Height") + ":")
            cond_grid.addWidget(self.cond_height_cb, 1, 0)
            self.cond_height_op = QComboBox()
            self.cond_height_op.addItems(["<=", "<", ">=", ">", "=="])
            self.cond_height_op.setEnabled(False)
            cond_grid.addWidget(self.cond_height_op, 1, 1)
            self.cond_height = QSpinBox()
            self.cond_height.setRange(1, 10000)
            self.cond_height.setEnabled(False)
            cond_grid.addWidget(self.cond_height, 1, 2)
            self.cond_height_cb.stateChanged.connect(
                lambda s: self._toggle_widgets(s, self.cond_height, self.cond_height_op)
            )

            layout.addWidget(self.cond_group)

        self.setStyleSheet("background-color: #e0f7fa;")

    def _toggle_widgets(self, state: int, *widgets: QWidget) -> None:
        enabled = state != 0
        for w in widgets:
            w.setEnabled(enabled)

    def to_profile(self) -> VideoCompressionProfile:
        conditions = VideoProfileConditions()
        if self.allow_conditions:
            if self.cond_width_cb.isChecked():
                conditions.width = NumericCondition(self.cond_width_op.currentText(), float(self.cond_width.value()))
            if self.cond_height_cb.isChecked():
                conditions.height = NumericCondition(self.cond_height_op.currentText(), float(self.cond_height.value()))
        return VideoCompressionProfile(
            name=self.name_edit.text() or self.title,
            bitrate=f"{self.bitrate.value()}k",
            max_width=self.max_width.value(),
            max_height=self.max_height.value(),
            output_format=self.format_combo.currentText(),
            codec=self.codec_combo.currentText(),
            conditions=conditions,
        )

    def apply_profile(self, profile: VideoCompressionProfile) -> None:
        self.name_edit.setText(profile.name)
        if profile.bitrate:
            with contextlib.suppress(ValueError):
                self.bitrate.setValue(int(str(profile.bitrate).replace("k", "")))
        if profile.max_width:
            self.max_width.setValue(profile.max_width)
        if profile.max_height:
            self.max_height.setValue(profile.max_height)
        self.format_combo.setCurrentText(profile.output_format)
        self.codec_combo.setCurrentText(profile.codec)
        if self.allow_conditions:
            if profile.conditions.width:
                self.cond_width_cb.setChecked(True)
                self.cond_width_op.setCurrentText(profile.conditions.width.op)
                self.cond_width.setValue(int(profile.conditions.width.value))
            if profile.conditions.height:
                self.cond_height_cb.setChecked(True)
                self.cond_height_op.setCurrentText(profile.conditions.height.op)
                self.cond_height.setValue(int(profile.conditions.height.value))

    def update_translations(self) -> None:
        self.basic_group.setTitle(tr("Compression Settings"))
        self.adv_group.setTitle(tr("Advanced Settings"))
        if self.allow_conditions:
            self.cond_group.setTitle(tr("Conditions"))
