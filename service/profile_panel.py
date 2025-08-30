from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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

from service.collapsible_box import CollapsibleBox
from service.compression_profiles import (
    CompressionProfile,
    NumericCondition,
    ProfileConditions,
)
from service.parameters_defaults import (
    AVIF_DEFAULTS,
    BASIC_DEFAULTS,
    JPEG_DEFAULTS,
    WEBP_DEFAULTS,
)
from service.translator import tr


def parse_size(text: str) -> int | None:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMG]?B)?", text.strip(), re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    factor = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
    return int(number * factor)


def format_size(value: int) -> str:
    unit = "B"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            break
        size /= 1024
    if unit == "B":
        return f"{int(size)}B"
    return f"{size:.0f}{unit}"


SUBSAMPLING_MAP = {
    "Auto (-1)": -1,
    "4:4:4 (0)": 0,
    "4:2:2 (1)": 1,
    "4:2:0 (2)": 2,
}


def subsampling_label(value: int) -> str:
    for label, val in SUBSAMPLING_MAP.items():
        if val == value:
            return label
    return "Auto (-1)"


class _WheelBlocker(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            QApplication.sendEvent(obj.parent(), event)
            return True
        return False


class ProfilePanel(QWidget):
    """Panel containing compression parameters and matching conditions."""

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
        self._wheel_blocker = _WheelBlocker(self)
        self._build_ui()
        self.update_translations()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Profile name and remove button
        name_layout = QHBoxLayout()
        self.name_label = QLabel("🖼️ " + tr("Name") + ":")
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
            name_layout.addSpacing(4)
            self.remove_btn = remove_btn
        layout.addLayout(name_layout)

        # Compression settings
        self.basic_group = QGroupBox(tr("Compression Settings"))
        grid = QGridLayout(self.basic_group)

        self.quality_label = QLabel(tr("Quality") + ":")
        grid.addWidget(self.quality_label, 0, 0)
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(BASIC_DEFAULTS["quality"])
        self.quality.setSuffix("%")
        grid.addWidget(self.quality, 0, 1)

        self.max_largest_cb = QCheckBox(tr("Max largest side") + ":")
        self.max_largest_cb.setChecked(BASIC_DEFAULTS["max_largest_enabled"])
        grid.addWidget(self.max_largest_cb, 1, 0)
        self.max_largest = QSpinBox()
        self.max_largest.setRange(1, 10000)
        self.max_largest.setValue(BASIC_DEFAULTS["max_largest_side"])
        self.max_largest.setEnabled(BASIC_DEFAULTS["max_largest_enabled"])
        grid.addWidget(self.max_largest, 1, 1)

        self.max_smallest_cb = QCheckBox(tr("Max smallest side") + ":")
        self.max_smallest_cb.setChecked(BASIC_DEFAULTS["max_smallest_enabled"])
        grid.addWidget(self.max_smallest_cb, 2, 0)
        self.max_smallest = QSpinBox()
        self.max_smallest.setRange(1, 10000)
        self.max_smallest.setValue(BASIC_DEFAULTS["max_smallest_side"])
        self.max_smallest.setEnabled(BASIC_DEFAULTS["max_smallest_enabled"])
        grid.addWidget(self.max_smallest, 2, 1)

        self.format_label = QLabel(tr("Format") + ":")
        grid.addWidget(self.format_label, 3, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "WEBP", "AVIF"])
        self.format_combo.setCurrentText(BASIC_DEFAULTS["output_format"])
        grid.addWidget(self.format_combo, 3, 1)

        layout.addWidget(self.basic_group)

        # Advanced settings
        self.advanced_box = CollapsibleBox(tr("Advanced Settings"))

        # JPEG settings
        self.jpeg_group = QGroupBox(tr("JPEG"))
        jpeg_grid = QGridLayout(self.jpeg_group)
        self.jpeg_progressive = QCheckBox(tr("Progressive"))
        self.jpeg_progressive.setChecked(JPEG_DEFAULTS["progressive"])
        jpeg_grid.addWidget(self.jpeg_progressive, 0, 0, 1, 2)
        self.jpeg_subsampling_label = QLabel(tr("Subsampling") + ":")
        jpeg_grid.addWidget(self.jpeg_subsampling_label, 1, 0)
        self.jpeg_subsampling = QComboBox()
        self.jpeg_subsampling.addItems(list(SUBSAMPLING_MAP.keys()))
        self.jpeg_subsampling.setCurrentText(JPEG_DEFAULTS["subsampling"])
        jpeg_grid.addWidget(self.jpeg_subsampling, 1, 1)
        self.jpeg_optimize = QCheckBox(tr("Optimize"))
        self.jpeg_optimize.setChecked(JPEG_DEFAULTS["optimize"])
        jpeg_grid.addWidget(self.jpeg_optimize, 2, 0, 1, 2)
        self.jpeg_smooth_label = QLabel(tr("Smooth") + ":")
        jpeg_grid.addWidget(self.jpeg_smooth_label, 3, 0)
        self.jpeg_smooth = QSpinBox()
        self.jpeg_smooth.setRange(0, 100)
        self.jpeg_smooth.setValue(JPEG_DEFAULTS["smooth"])
        jpeg_grid.addWidget(self.jpeg_smooth, 3, 1)
        self.jpeg_keep_rgb = QCheckBox(tr("Keep RGB"))
        self.jpeg_keep_rgb.setChecked(JPEG_DEFAULTS["keep_rgb"])
        jpeg_grid.addWidget(self.jpeg_keep_rgb, 4, 0, 1, 2)
        self.advanced_box.add_widget(self.jpeg_group)

        # WebP settings
        self.webp_group = QGroupBox(tr("WebP"))
        webp_grid = QGridLayout(self.webp_group)
        self.webp_lossless = QCheckBox(tr("Lossless"))
        self.webp_lossless.setChecked(WEBP_DEFAULTS["lossless"])
        webp_grid.addWidget(self.webp_lossless, 0, 0, 1, 2)
        self.webp_method_label = QLabel(tr("Method") + ":")
        webp_grid.addWidget(self.webp_method_label, 1, 0)
        self.webp_method = QSpinBox()
        self.webp_method.setRange(0, 6)
        self.webp_method.setValue(WEBP_DEFAULTS["method"])
        webp_grid.addWidget(self.webp_method, 1, 1)
        self.webp_alpha_quality_label = QLabel(tr("Alpha Quality") + ":")
        webp_grid.addWidget(self.webp_alpha_quality_label, 2, 0)
        self.webp_alpha_quality = QSpinBox()
        self.webp_alpha_quality.setRange(0, 100)
        self.webp_alpha_quality.setValue(WEBP_DEFAULTS["alpha_quality"])
        webp_grid.addWidget(self.webp_alpha_quality, 2, 1)
        self.webp_exact = QCheckBox(tr("Exact alpha"))
        self.webp_exact.setChecked(WEBP_DEFAULTS["exact"])
        webp_grid.addWidget(self.webp_exact, 3, 0, 1, 2)
        self.advanced_box.add_widget(self.webp_group)

        # AVIF settings
        self.avif_group = QGroupBox(tr("AVIF"))
        avif_grid = QGridLayout(self.avif_group)
        self.avif_subsampling_label = QLabel(tr("Subsampling") + ":")
        avif_grid.addWidget(self.avif_subsampling_label, 0, 0)
        self.avif_subsampling = QComboBox()
        self.avif_subsampling.addItems(["4:2:0", "4:2:2", "4:4:4"])
        self.avif_subsampling.setCurrentText(AVIF_DEFAULTS["subsampling"])
        avif_grid.addWidget(self.avif_subsampling, 0, 1)
        self.avif_speed_label = QLabel(tr("Speed") + ":")
        avif_grid.addWidget(self.avif_speed_label, 1, 0)
        self.avif_speed = QSpinBox()
        self.avif_speed.setRange(0, 10)
        self.avif_speed.setValue(AVIF_DEFAULTS["speed"])
        avif_grid.addWidget(self.avif_speed, 1, 1)
        self.avif_codec_label = QLabel(tr("Codec") + ":")
        avif_grid.addWidget(self.avif_codec_label, 2, 0)
        self.avif_codec = QComboBox()
        self.avif_codec.addItems(["auto", "aom", "rav1e", "svt"])
        self.avif_codec.setCurrentText(AVIF_DEFAULTS["codec"])
        avif_grid.addWidget(self.avif_codec, 2, 1)
        self.avif_range_label = QLabel(tr("Range") + ":")
        avif_grid.addWidget(self.avif_range_label, 3, 0)
        self.avif_range = QComboBox()
        self.avif_range.addItems(["full", "limited"])
        self.avif_range.setCurrentText(AVIF_DEFAULTS["range"])
        avif_grid.addWidget(self.avif_range, 3, 1)
        self.avif_qmin_label = QLabel(tr("Qmin") + ":")
        avif_grid.addWidget(self.avif_qmin_label, 4, 0)
        self.avif_qmin = QSpinBox()
        self.avif_qmin.setRange(-1, 63)
        self.avif_qmin.setValue(AVIF_DEFAULTS["qmin"])
        avif_grid.addWidget(self.avif_qmin, 4, 1)
        self.avif_qmax_label = QLabel(tr("Qmax") + ":")
        avif_grid.addWidget(self.avif_qmax_label, 5, 0)
        self.avif_qmax = QSpinBox()
        self.avif_qmax.setRange(-1, 63)
        self.avif_qmax.setValue(AVIF_DEFAULTS["qmax"])
        avif_grid.addWidget(self.avif_qmax, 5, 1)
        self.avif_autotiling = QCheckBox(tr("Autotiling"))
        self.avif_autotiling.setChecked(AVIF_DEFAULTS["autotiling"])
        avif_grid.addWidget(self.avif_autotiling, 6, 0, 1, 2)
        self.avif_tile_rows_label = QLabel(tr("Tile Rows") + ":")
        avif_grid.addWidget(self.avif_tile_rows_label, 7, 0)
        self.avif_tile_rows = QSpinBox()
        self.avif_tile_rows.setRange(0, 6)
        self.avif_tile_rows.setValue(AVIF_DEFAULTS["tile_rows"])
        avif_grid.addWidget(self.avif_tile_rows, 7, 1)
        self.avif_tile_cols_label = QLabel(tr("Tile Cols") + ":")
        avif_grid.addWidget(self.avif_tile_cols_label, 8, 0)
        self.avif_tile_cols = QSpinBox()
        self.avif_tile_cols.setRange(0, 6)
        self.avif_tile_cols.setValue(AVIF_DEFAULTS["tile_cols"])
        avif_grid.addWidget(self.avif_tile_cols, 8, 1)
        self.advanced_box.add_widget(self.avif_group)

        layout.addWidget(self.advanced_box)

        self.format_combo.currentTextChanged.connect(self._update_advanced_visibility)
        self._update_advanced_visibility(self.format_combo.currentText())

        # Conditions sub-panel
        self.conditions_box = CollapsibleBox(tr("Conditions"))
        conditions_widget = QWidget()
        cond_grid = QGridLayout(conditions_widget)
        row = 0

        self.cond_smallest_cb = QCheckBox(tr("Smallest side") + ":")
        cond_grid.addWidget(self.cond_smallest_cb, row, 0)
        self.cond_smallest_op = QComboBox()
        self.cond_smallest_op.addItems(["<=", "<", ">=", ">", "=="])
        self.cond_smallest_op.setEnabled(False)
        cond_grid.addWidget(self.cond_smallest_op, row, 1)
        self.cond_smallest = QSpinBox()
        self.cond_smallest.setRange(1, 10000)
        self.cond_smallest.setEnabled(False)
        cond_grid.addWidget(self.cond_smallest, row, 2)
        self.cond_smallest_cb.stateChanged.connect(
            lambda s: self._toggle_widgets(s, self.cond_smallest, self.cond_smallest_op)
        )
        row += 1

        self.cond_largest_cb = QCheckBox(tr("Largest side") + ":")
        cond_grid.addWidget(self.cond_largest_cb, row, 0)
        self.cond_largest_op = QComboBox()
        self.cond_largest_op.addItems(["<=", "<", ">=", ">", "=="])
        self.cond_largest_op.setEnabled(False)
        cond_grid.addWidget(self.cond_largest_op, row, 1)
        self.cond_largest = QSpinBox()
        self.cond_largest.setRange(1, 10000)
        self.cond_largest.setEnabled(False)
        cond_grid.addWidget(self.cond_largest, row, 2)
        self.cond_largest_cb.stateChanged.connect(
            lambda s: self._toggle_widgets(s, self.cond_largest, self.cond_largest_op)
        )
        row += 1

        self.cond_pixels_cb = QCheckBox(tr("Pixels") + ":")
        cond_grid.addWidget(self.cond_pixels_cb, row, 0)
        self.cond_pixels_op = QComboBox()
        self.cond_pixels_op.addItems(["<=", "<", ">=", ">", "=="])
        self.cond_pixels_op.setEnabled(False)
        cond_grid.addWidget(self.cond_pixels_op, row, 1)
        self.cond_pixels = QSpinBox()
        self.cond_pixels.setRange(1, 1_000_000_000)
        self.cond_pixels.setEnabled(False)
        cond_grid.addWidget(self.cond_pixels, row, 2)
        self.cond_pixels_cb.stateChanged.connect(
            lambda s: self._toggle_widgets(s, self.cond_pixels, self.cond_pixels_op)
        )
        row += 1

        self.cond_aspect_cb = QCheckBox(tr("Aspect ratio") + ":")
        cond_grid.addWidget(self.cond_aspect_cb, row, 0)
        self.cond_aspect_op = QComboBox()
        self.cond_aspect_op.addItems(["<=", "<", ">=", ">", "=="])
        self.cond_aspect_op.setEnabled(False)
        cond_grid.addWidget(self.cond_aspect_op, row, 1)
        self.cond_aspect = QDoubleSpinBox()
        self.cond_aspect.setRange(0.01, 100.0)
        self.cond_aspect.setSingleStep(0.1)
        self.cond_aspect.setEnabled(False)
        cond_grid.addWidget(self.cond_aspect, row, 2)
        self.cond_aspect_cb.stateChanged.connect(
            lambda s: self._toggle_widgets(s, self.cond_aspect, self.cond_aspect_op)
        )
        row += 1

        self.orientation_label = QLabel(tr("Orientation") + ":")
        cond_grid.addWidget(self.orientation_label, row, 0)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem(tr("Any"), "any")
        self.orientation_combo.addItem(tr("Landscape"), "landscape")
        self.orientation_combo.addItem(tr("Portrait"), "portrait")
        self.orientation_combo.addItem(tr("Square"), "square")
        cond_grid.addWidget(self.orientation_combo, row, 1)
        row += 1

        self.input_formats_label = QLabel(tr("Input formats") + ":")
        cond_grid.addWidget(self.input_formats_label, row, 0)
        self.input_formats_edit = QLineEdit()
        self.input_formats_edit.setPlaceholderText("jpg,png")
        cond_grid.addWidget(self.input_formats_edit, row, 1)
        row += 1

        self.transparency_label = QLabel(tr("Transparency") + ":")
        cond_grid.addWidget(self.transparency_label, row, 0)
        self.transparency_combo = QComboBox()
        self.transparency_combo.addItem(tr("Any"), "any")
        self.transparency_combo.addItem(tr("Requires"), "requires")
        self.transparency_combo.addItem(tr("No"), "no")
        cond_grid.addWidget(self.transparency_combo, row, 1)
        row += 1

        self.cond_bytes_cb = QCheckBox(tr("File size") + ":")
        cond_grid.addWidget(self.cond_bytes_cb, row, 0)
        self.cond_bytes_op = QComboBox()
        self.cond_bytes_op.addItems(["<=", "<", ">=", ">", "=="])
        self.cond_bytes_op.setEnabled(False)
        cond_grid.addWidget(self.cond_bytes_op, row, 1)
        self.cond_bytes = QLineEdit()
        self.cond_bytes.setPlaceholderText("1MB")
        self.cond_bytes.setToolTip(tr("Examples: 500KB, 2MB, 1.5GB"))
        self.cond_bytes.setEnabled(False)
        cond_grid.addWidget(self.cond_bytes, row, 2)
        self.cond_bytes_cb.stateChanged.connect(lambda s: self._toggle_widgets(s, self.cond_bytes, self.cond_bytes_op))
        row += 1

        self.exif_label = QLabel(tr("Required EXIF (k=v,...)") + ":")
        cond_grid.addWidget(self.exif_label, row, 0)
        self.exif_edit = QLineEdit()
        cond_grid.addWidget(self.exif_edit, row, 1)

        self.conditions_box.add_widget(conditions_widget)
        layout.addWidget(self.conditions_box)

        for w in self.findChildren(QWidget):
            if isinstance(w, QSpinBox | QDoubleSpinBox | QComboBox):
                w.installEventFilter(self._wheel_blocker)

        if not self.allow_conditions:
            self.conditions_box.toggle_button.setText(tr("Conditions (default profile - always used)"))
            self.conditions_box.toggle_button.setEnabled(False)
            self.conditions_box.content.setEnabled(False)

    def _toggle_widgets(self, state: int, *widgets: QWidget) -> None:
        enabled = bool(state)
        for w in widgets:
            w.setEnabled(enabled)

    def _update_advanced_visibility(self, fmt: str) -> None:
        self.jpeg_group.setVisible(fmt == "JPEG")
        self.webp_group.setVisible(fmt == "WEBP")
        self.avif_group.setVisible(fmt == "AVIF")

    def update_translations(self) -> None:
        self.name_label.setText(tr("Name") + ":")
        if not self.name_edit.text():
            self.name_edit.setPlaceholderText(self.title)
        self.basic_group.setTitle(tr("Compression Settings"))
        self.quality_label.setText(tr("Quality") + ":")
        self.max_largest_cb.setText(tr("Max largest side") + ":")
        self.max_smallest_cb.setText(tr("Max smallest side") + ":")
        self.format_label.setText(tr("Format") + ":")

        self.advanced_box.toggle_button.setText(tr("Advanced Settings"))
        self.jpeg_group.setTitle(tr("JPEG"))
        self.jpeg_progressive.setText(tr("Progressive"))
        self.jpeg_subsampling_label.setText(tr("Subsampling") + ":")
        self.jpeg_optimize.setText(tr("Optimize"))
        self.jpeg_smooth_label.setText(tr("Smooth") + ":")
        self.jpeg_keep_rgb.setText(tr("Keep RGB"))

        self.webp_group.setTitle(tr("WebP"))
        self.webp_lossless.setText(tr("Lossless"))
        self.webp_method_label.setText(tr("Method") + ":")
        self.webp_alpha_quality_label.setText(tr("Alpha Quality") + ":")
        self.webp_exact.setText(tr("Exact alpha"))

        self.avif_group.setTitle(tr("AVIF"))
        self.avif_subsampling_label.setText(tr("Subsampling") + ":")
        self.avif_speed_label.setText(tr("Speed") + ":")
        self.avif_codec_label.setText(tr("Codec") + ":")
        self.avif_range_label.setText(tr("Range") + ":")
        self.avif_qmin_label.setText(tr("Qmin") + ":")
        self.avif_qmax_label.setText(tr("Qmax") + ":")
        self.avif_autotiling.setText(tr("Autotiling"))
        self.avif_tile_rows_label.setText(tr("Tile Rows") + ":")
        self.avif_tile_cols_label.setText(tr("Tile Cols") + ":")

        self.conditions_box.toggle_button.setText(tr("Conditions"))
        self.cond_smallest_cb.setText(tr("Smallest side") + ":")
        self.cond_largest_cb.setText(tr("Largest side") + ":")
        self.cond_pixels_cb.setText(tr("Pixels") + ":")
        self.cond_aspect_cb.setText(tr("Aspect ratio") + ":")
        self.orientation_label.setText(tr("Orientation") + ":")
        current_orientation = self.orientation_combo.currentData()
        self.orientation_combo.clear()
        self.orientation_combo.addItem(tr("Any"), "any")
        self.orientation_combo.addItem(tr("Landscape"), "landscape")
        self.orientation_combo.addItem(tr("Portrait"), "portrait")
        self.orientation_combo.addItem(tr("Square"), "square")
        idx = self.orientation_combo.findData(current_orientation if current_orientation else "any")
        if idx != -1:
            self.orientation_combo.setCurrentIndex(idx)

        self.input_formats_label.setText(tr("Input formats") + ":")
        self.transparency_label.setText(tr("Transparency") + ":")
        current_trans = self.transparency_combo.currentData()
        self.transparency_combo.clear()
        self.transparency_combo.addItem(tr("Any"), "any")
        self.transparency_combo.addItem(tr("Requires"), "requires")
        self.transparency_combo.addItem(tr("No"), "no")
        idx = self.transparency_combo.findData(current_trans if current_trans else "any")
        if idx != -1:
            self.transparency_combo.setCurrentIndex(idx)

        self.cond_bytes_cb.setText(tr("File size") + ":")
        self.cond_bytes.setToolTip(tr("Examples: 500KB, 2MB, 1.5GB"))
        self.exif_label.setText(tr("Required EXIF (k=v,...)") + ":")
        if not self.allow_conditions:
            self.conditions_box.toggle_button.setText(tr("Conditions (default profile - always used)"))

    # ------------------------------------------------------------------
    def get_parameters(self) -> dict[str, Any]:
        """Return compression parameters from the panel."""
        return {
            "quality": self.quality.value(),
            "max_largest_side": self.max_largest.value() if self.max_largest_cb.isChecked() else None,
            "max_smallest_side": self.max_smallest.value() if self.max_smallest_cb.isChecked() else None,
            "output_format": self.format_combo.currentText(),
            "jpeg_params": {
                "progressive": self.jpeg_progressive.isChecked(),
                "subsampling": SUBSAMPLING_MAP[self.jpeg_subsampling.currentText()],
                "optimize": self.jpeg_optimize.isChecked(),
                "smooth": self.jpeg_smooth.value(),
                "keep_rgb": self.jpeg_keep_rgb.isChecked(),
            },
            "webp_params": {
                "lossless": self.webp_lossless.isChecked(),
                "method": self.webp_method.value(),
                "alpha_quality": self.webp_alpha_quality.value(),
                "exact": self.webp_exact.isChecked(),
            },
            "avif_params": {
                "subsampling": self.avif_subsampling.currentText(),
                "speed": self.avif_speed.value(),
                "codec": self.avif_codec.currentText(),
                "range": self.avif_range.currentText(),
                "qmin": self.avif_qmin.value(),
                "qmax": self.avif_qmax.value(),
                "autotiling": self.avif_autotiling.isChecked(),
                "tile_rows": self.avif_tile_rows.value(),
                "tile_cols": self.avif_tile_cols.value(),
            },
        }

    def get_conditions(self) -> ProfileConditions:
        """Return matching conditions configured in the panel."""
        if not self.allow_conditions:
            return ProfileConditions()
        bytes_val = parse_size(self.cond_bytes.text()) if self.cond_bytes_cb.isChecked() else None
        return ProfileConditions(
            smallest_side=NumericCondition(self.cond_smallest_op.currentText(), self.cond_smallest.value())
            if self.cond_smallest_cb.isChecked()
            else None,
            largest_side=NumericCondition(self.cond_largest_op.currentText(), self.cond_largest.value())
            if self.cond_largest_cb.isChecked()
            else None,
            pixel_count=NumericCondition(self.cond_pixels_op.currentText(), self.cond_pixels.value())
            if self.cond_pixels_cb.isChecked()
            else None,
            aspect_ratio=NumericCondition(self.cond_aspect_op.currentText(), self.cond_aspect.value())
            if self.cond_aspect_cb.isChecked()
            else None,
            orientation=None if self.orientation_combo.currentData() == "any" else self.orientation_combo.currentData(),
            input_formats=[s.strip() for s in self.input_formats_edit.text().split(",") if s.strip()] or None,
            requires_transparency={
                "requires": True,
                "no": False,
            }.get(self.transparency_combo.currentData()),
            file_size=NumericCondition(self.cond_bytes_op.currentText(), bytes_val) if bytes_val is not None else None,
            required_exif=dict(part.split("=", 1) for part in self.exif_edit.text().split(",") if "=" in part) or None,
        )

    def to_profile(self) -> CompressionProfile:
        params = self.get_parameters()
        profile = CompressionProfile(
            name=self.name_edit.text() or self.title,
            quality=params["quality"],
            max_largest_side=params["max_largest_side"],
            max_smallest_side=params["max_smallest_side"],
            output_format=params["output_format"],
            jpeg_params=params["jpeg_params"],
            webp_params=params["webp_params"],
            avif_params=params["avif_params"],
        )
        profile.conditions = self.get_conditions()
        return profile

    def apply_profile(self, profile: CompressionProfile) -> None:
        self.name_edit.setText(profile.name)
        self.quality.setValue(profile.quality)

        if profile.max_largest_side is not None:
            self.max_largest_cb.setChecked(True)
            self.max_largest.setValue(profile.max_largest_side)
        else:
            self.max_largest_cb.setChecked(False)
            self.max_largest.setEnabled(False)

        if profile.max_smallest_side is not None:
            self.max_smallest_cb.setChecked(True)
            self.max_smallest.setValue(profile.max_smallest_side)
        else:
            self.max_smallest_cb.setChecked(False)
            self.max_smallest.setEnabled(False)

        self.format_combo.setCurrentText(profile.output_format)

        jpeg = profile.jpeg_params
        self.jpeg_progressive.setChecked(jpeg.get("progressive", JPEG_DEFAULTS["progressive"]))
        default_sub = SUBSAMPLING_MAP[JPEG_DEFAULTS["subsampling"]]
        self.jpeg_subsampling.setCurrentText(subsampling_label(jpeg.get("subsampling", default_sub)))
        self.jpeg_optimize.setChecked(jpeg.get("optimize", JPEG_DEFAULTS["optimize"]))
        self.jpeg_smooth.setValue(jpeg.get("smooth", JPEG_DEFAULTS["smooth"]))
        self.jpeg_keep_rgb.setChecked(jpeg.get("keep_rgb", JPEG_DEFAULTS["keep_rgb"]))

        webp = profile.webp_params
        self.webp_lossless.setChecked(webp.get("lossless", WEBP_DEFAULTS["lossless"]))
        self.webp_method.setValue(webp.get("method", WEBP_DEFAULTS["method"]))
        self.webp_alpha_quality.setValue(webp.get("alpha_quality", WEBP_DEFAULTS["alpha_quality"]))
        self.webp_exact.setChecked(webp.get("exact", WEBP_DEFAULTS["exact"]))

        avif = profile.avif_params
        self.avif_subsampling.setCurrentText(avif.get("subsampling", AVIF_DEFAULTS["subsampling"]))
        self.avif_speed.setValue(avif.get("speed", AVIF_DEFAULTS["speed"]))
        self.avif_codec.setCurrentText(avif.get("codec", AVIF_DEFAULTS["codec"]))
        self.avif_range.setCurrentText(avif.get("range", AVIF_DEFAULTS["range"]))
        self.avif_qmin.setValue(avif.get("qmin", AVIF_DEFAULTS["qmin"]))
        self.avif_qmax.setValue(avif.get("qmax", AVIF_DEFAULTS["qmax"]))
        self.avif_autotiling.setChecked(avif.get("autotiling", AVIF_DEFAULTS["autotiling"]))
        self.avif_tile_rows.setValue(avif.get("tile_rows", AVIF_DEFAULTS["tile_rows"]))
        self.avif_tile_cols.setValue(avif.get("tile_cols", AVIF_DEFAULTS["tile_cols"]))

        cond = profile.conditions
        if cond.smallest_side is not None:
            self.cond_smallest_cb.setChecked(True)
            self.cond_smallest_op.setCurrentText(cond.smallest_side.op)
            self.cond_smallest.setValue(int(cond.smallest_side.value))
        else:
            self.cond_smallest_cb.setChecked(False)
            self.cond_smallest.setEnabled(False)
            self.cond_smallest_op.setEnabled(False)

        if cond.largest_side is not None:
            self.cond_largest_cb.setChecked(True)
            self.cond_largest_op.setCurrentText(cond.largest_side.op)
            self.cond_largest.setValue(int(cond.largest_side.value))
        else:
            self.cond_largest_cb.setChecked(False)
            self.cond_largest.setEnabled(False)
            self.cond_largest_op.setEnabled(False)

        if cond.pixel_count is not None:
            self.cond_pixels_cb.setChecked(True)
            self.cond_pixels_op.setCurrentText(cond.pixel_count.op)
            self.cond_pixels.setValue(int(cond.pixel_count.value))
        else:
            self.cond_pixels_cb.setChecked(False)
            self.cond_pixels.setEnabled(False)
            self.cond_pixels_op.setEnabled(False)

        if cond.aspect_ratio is not None:
            self.cond_aspect_cb.setChecked(True)
            self.cond_aspect_op.setCurrentText(cond.aspect_ratio.op)
            self.cond_aspect.setValue(cond.aspect_ratio.value)
        else:
            self.cond_aspect_cb.setChecked(False)
            self.cond_aspect.setEnabled(False)
            self.cond_aspect_op.setEnabled(False)

        if cond.orientation:
            index = self.orientation_combo.findData(cond.orientation)
            if index != -1:
                self.orientation_combo.setCurrentIndex(index)
        else:
            self.orientation_combo.setCurrentIndex(self.orientation_combo.findData("any"))

        if cond.input_formats:
            self.input_formats_edit.setText(",".join(cond.input_formats))
        else:
            self.input_formats_edit.clear()

        if cond.requires_transparency is True:
            self.transparency_combo.setCurrentIndex(self.transparency_combo.findData("requires"))
        elif cond.requires_transparency is False:
            self.transparency_combo.setCurrentIndex(self.transparency_combo.findData("no"))
        else:
            self.transparency_combo.setCurrentIndex(self.transparency_combo.findData("any"))

        if cond.file_size is not None:
            self.cond_bytes_cb.setChecked(True)
            self.cond_bytes_op.setCurrentText(cond.file_size.op)
            self.cond_bytes.setText(format_size(int(cond.file_size.value)))
        else:
            self.cond_bytes_cb.setChecked(False)
            self.cond_bytes.setEnabled(False)
            self.cond_bytes_op.setEnabled(False)
            self.cond_bytes.clear()

        if cond.required_exif:
            self.exif_edit.setText(",".join(f"{k}={v}" for k, v in cond.required_exif.items()))
        else:
            self.exif_edit.clear()

    def reset_to_defaults(self) -> None:
        self.name_edit.clear()
        self.quality.setValue(BASIC_DEFAULTS["quality"])

        self.max_largest_cb.setChecked(BASIC_DEFAULTS["max_largest_enabled"])
        self.max_largest.setValue(BASIC_DEFAULTS["max_largest_side"])
        self.max_largest.setEnabled(BASIC_DEFAULTS["max_largest_enabled"])

        self.max_smallest_cb.setChecked(BASIC_DEFAULTS["max_smallest_enabled"])
        self.max_smallest.setValue(BASIC_DEFAULTS["max_smallest_side"])
        self.max_smallest.setEnabled(BASIC_DEFAULTS["max_smallest_enabled"])

        self.format_combo.setCurrentText(BASIC_DEFAULTS["output_format"])

        self.jpeg_progressive.setChecked(JPEG_DEFAULTS["progressive"])
        self.jpeg_subsampling.setCurrentText(JPEG_DEFAULTS["subsampling"])
        self.jpeg_optimize.setChecked(JPEG_DEFAULTS["optimize"])
        self.jpeg_smooth.setValue(JPEG_DEFAULTS["smooth"])
        self.jpeg_keep_rgb.setChecked(JPEG_DEFAULTS["keep_rgb"])

        self.webp_lossless.setChecked(WEBP_DEFAULTS["lossless"])
        self.webp_method.setValue(WEBP_DEFAULTS["method"])
        self.webp_alpha_quality.setValue(WEBP_DEFAULTS["alpha_quality"])
        self.webp_exact.setChecked(WEBP_DEFAULTS["exact"])

        self.avif_subsampling.setCurrentText(AVIF_DEFAULTS["subsampling"])
        self.avif_speed.setValue(AVIF_DEFAULTS["speed"])
        self.avif_codec.setCurrentText(AVIF_DEFAULTS["codec"])
        self.avif_range.setCurrentText(AVIF_DEFAULTS["range"])
        self.avif_qmin.setValue(AVIF_DEFAULTS["qmin"])
        self.avif_qmax.setValue(AVIF_DEFAULTS["qmax"])
        self.avif_autotiling.setChecked(AVIF_DEFAULTS["autotiling"])
        self.avif_tile_rows.setValue(AVIF_DEFAULTS["tile_rows"])
        self.avif_tile_cols.setValue(AVIF_DEFAULTS["tile_cols"])

        self.cond_smallest_cb.setChecked(False)
        self.cond_smallest.setEnabled(False)
        self.cond_smallest_op.setEnabled(False)
        self.cond_largest_cb.setChecked(False)
        self.cond_largest.setEnabled(False)
        self.cond_largest_op.setEnabled(False)
        self.cond_pixels_cb.setChecked(False)
        self.cond_pixels.setEnabled(False)
        self.cond_pixels_op.setEnabled(False)
        self.cond_aspect_cb.setChecked(False)
        self.cond_aspect.setEnabled(False)
        self.cond_aspect_op.setEnabled(False)
        self.orientation_combo.setCurrentIndex(self.orientation_combo.findData("any"))
        self.input_formats_edit.clear()
        self.transparency_combo.setCurrentIndex(self.transparency_combo.findData("any"))
        self.cond_bytes_cb.setChecked(False)
        self.cond_bytes.setEnabled(False)
        self.cond_bytes_op.setEnabled(False)
        self.cond_bytes.clear()
        self.exif_edit.clear()
