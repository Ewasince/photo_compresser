from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from service.collapsible_box import CollapsibleBox
from service.compression_profiles import CompressionProfile, ProfileConditions
from service.parameters_defaults import (
    AVIF_DEFAULTS,
    BASIC_DEFAULTS,
    JPEG_DEFAULTS,
    WEBP_DEFAULTS,
)


class ProfilePanel(QWidget):
    """Panel containing compression parameters and matching conditions."""

    def __init__(self, title: str, *, allow_conditions: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        self.allow_conditions = allow_conditions
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Profile name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.title)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Compression settings
        self.basic_group = QGroupBox("Compression Settings")
        grid = QGridLayout(self.basic_group)

        grid.addWidget(QLabel("Quality:"), 0, 0)
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(BASIC_DEFAULTS["quality"])
        self.quality.setSuffix("%")
        grid.addWidget(self.quality, 0, 1)

        self.max_largest_cb = QCheckBox("Max largest side:")
        self.max_largest_cb.setChecked(BASIC_DEFAULTS["max_largest_enabled"])
        grid.addWidget(self.max_largest_cb, 1, 0)
        self.max_largest = QSpinBox()
        self.max_largest.setRange(1, 10000)
        self.max_largest.setValue(BASIC_DEFAULTS["max_largest_side"])
        self.max_largest.setEnabled(BASIC_DEFAULTS["max_largest_enabled"])
        grid.addWidget(self.max_largest, 1, 1)

        self.max_smallest_cb = QCheckBox("Max smallest side:")
        self.max_smallest_cb.setChecked(BASIC_DEFAULTS["max_smallest_enabled"])
        grid.addWidget(self.max_smallest_cb, 2, 0)
        self.max_smallest = QSpinBox()
        self.max_smallest.setRange(1, 10000)
        self.max_smallest.setValue(BASIC_DEFAULTS["max_smallest_side"])
        self.max_smallest.setEnabled(BASIC_DEFAULTS["max_smallest_enabled"])
        grid.addWidget(self.max_smallest, 2, 1)

        grid.addWidget(QLabel("Format:"), 3, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "WEBP", "AVIF"])
        self.format_combo.setCurrentText(BASIC_DEFAULTS["output_format"])
        grid.addWidget(self.format_combo, 3, 1)

        self.preserve_cb = QCheckBox("Preserve folder structure")
        self.preserve_cb.setChecked(BASIC_DEFAULTS["preserve_structure"])
        grid.addWidget(self.preserve_cb, 4, 0, 1, 2)

        layout.addWidget(self.basic_group)

        # Advanced settings
        self.advanced_box = CollapsibleBox("Advanced Settings")

        # JPEG settings
        jpeg_group = QGroupBox("JPEG")
        jpeg_grid = QGridLayout(jpeg_group)
        self.jpeg_progressive = QCheckBox("Progressive")
        self.jpeg_progressive.setChecked(JPEG_DEFAULTS["progressive"])
        jpeg_grid.addWidget(self.jpeg_progressive, 0, 0, 1, 2)
        jpeg_grid.addWidget(QLabel("Subsampling:"), 1, 0)
        self.jpeg_subsampling = QComboBox()
        self.jpeg_subsampling.addItems(["Auto (-1)", "4:4:4 (0)", "4:2:2 (1)", "4:2:0 (2)"])
        self.jpeg_subsampling.setCurrentText(JPEG_DEFAULTS["subsampling"])
        jpeg_grid.addWidget(self.jpeg_subsampling, 1, 1)
        self.jpeg_optimize = QCheckBox("Optimize")
        self.jpeg_optimize.setChecked(JPEG_DEFAULTS["optimize"])
        jpeg_grid.addWidget(self.jpeg_optimize, 2, 0, 1, 2)
        jpeg_grid.addWidget(QLabel("Smooth:"), 3, 0)
        self.jpeg_smooth = QSpinBox()
        self.jpeg_smooth.setRange(0, 100)
        self.jpeg_smooth.setValue(JPEG_DEFAULTS["smooth"])
        jpeg_grid.addWidget(self.jpeg_smooth, 3, 1)
        self.jpeg_keep_rgb = QCheckBox("Keep RGB")
        self.jpeg_keep_rgb.setChecked(JPEG_DEFAULTS["keep_rgb"])
        jpeg_grid.addWidget(self.jpeg_keep_rgb, 4, 0, 1, 2)
        self.advanced_box.add_widget(jpeg_group)

        # WebP settings
        webp_group = QGroupBox("WebP")
        webp_grid = QGridLayout(webp_group)
        self.webp_lossless = QCheckBox("Lossless")
        self.webp_lossless.setChecked(WEBP_DEFAULTS["lossless"])
        webp_grid.addWidget(self.webp_lossless, 0, 0, 1, 2)
        webp_grid.addWidget(QLabel("Method:"), 1, 0)
        self.webp_method = QSpinBox()
        self.webp_method.setRange(0, 6)
        self.webp_method.setValue(WEBP_DEFAULTS["method"])
        webp_grid.addWidget(self.webp_method, 1, 1)
        webp_grid.addWidget(QLabel("Alpha quality:"), 2, 0)
        self.webp_alpha_quality = QSpinBox()
        self.webp_alpha_quality.setRange(0, 100)
        self.webp_alpha_quality.setValue(WEBP_DEFAULTS["alpha_quality"])
        webp_grid.addWidget(self.webp_alpha_quality, 2, 1)
        self.webp_exact = QCheckBox("Exact alpha")
        self.webp_exact.setChecked(WEBP_DEFAULTS["exact"])
        webp_grid.addWidget(self.webp_exact, 3, 0, 1, 2)
        self.advanced_box.add_widget(webp_group)

        # AVIF settings
        avif_group = QGroupBox("AVIF")
        avif_grid = QGridLayout(avif_group)
        avif_grid.addWidget(QLabel("Subsampling:"), 0, 0)
        self.avif_subsampling = QComboBox()
        self.avif_subsampling.addItems(["4:2:0", "4:2:2", "4:4:4"])
        self.avif_subsampling.setCurrentText(AVIF_DEFAULTS["subsampling"])
        avif_grid.addWidget(self.avif_subsampling, 0, 1)
        avif_grid.addWidget(QLabel("Speed:"), 1, 0)
        self.avif_speed = QSpinBox()
        self.avif_speed.setRange(0, 10)
        self.avif_speed.setValue(AVIF_DEFAULTS["speed"])
        avif_grid.addWidget(self.avif_speed, 1, 1)
        avif_grid.addWidget(QLabel("Codec:"), 2, 0)
        self.avif_codec = QComboBox()
        self.avif_codec.addItems(["auto", "aom", "rav1e", "svt"])
        self.avif_codec.setCurrentText(AVIF_DEFAULTS["codec"])
        avif_grid.addWidget(self.avif_codec, 2, 1)
        avif_grid.addWidget(QLabel("Range:"), 3, 0)
        self.avif_range = QComboBox()
        self.avif_range.addItems(["full", "limited"])
        self.avif_range.setCurrentText(AVIF_DEFAULTS["range"])
        avif_grid.addWidget(self.avif_range, 3, 1)
        avif_grid.addWidget(QLabel("Qmin:"), 4, 0)
        self.avif_qmin = QSpinBox()
        self.avif_qmin.setRange(-1, 63)
        self.avif_qmin.setValue(AVIF_DEFAULTS["qmin"])
        avif_grid.addWidget(self.avif_qmin, 4, 1)
        avif_grid.addWidget(QLabel("Qmax:"), 5, 0)
        self.avif_qmax = QSpinBox()
        self.avif_qmax.setRange(-1, 63)
        self.avif_qmax.setValue(AVIF_DEFAULTS["qmax"])
        avif_grid.addWidget(self.avif_qmax, 5, 1)
        self.avif_autotiling = QCheckBox("Autotiling")
        self.avif_autotiling.setChecked(AVIF_DEFAULTS["autotiling"])
        avif_grid.addWidget(self.avif_autotiling, 6, 0, 1, 2)
        avif_grid.addWidget(QLabel("Tile rows:"), 7, 0)
        self.avif_tile_rows = QSpinBox()
        self.avif_tile_rows.setRange(0, 6)
        self.avif_tile_rows.setValue(AVIF_DEFAULTS["tile_rows"])
        avif_grid.addWidget(self.avif_tile_rows, 7, 1)
        avif_grid.addWidget(QLabel("Tile cols:"), 8, 0)
        self.avif_tile_cols = QSpinBox()
        self.avif_tile_cols.setRange(0, 6)
        self.avif_tile_cols.setValue(AVIF_DEFAULTS["tile_cols"])
        avif_grid.addWidget(self.avif_tile_cols, 8, 1)
        self.advanced_box.add_widget(avif_group)

        layout.addWidget(self.advanced_box)

        # Conditions sub-panel
        self.conditions_box = CollapsibleBox("Conditions")
        conditions_widget = QWidget()
        cond_grid = QGridLayout(conditions_widget)
        row = 0

        self.cond_smallest_cb = QCheckBox("Max smallest side:")
        cond_grid.addWidget(self.cond_smallest_cb, row, 0)
        self.cond_smallest = QSpinBox()
        self.cond_smallest.setRange(1, 10000)
        self.cond_smallest.setEnabled(False)
        cond_grid.addWidget(self.cond_smallest, row, 1)
        self.cond_smallest_cb.stateChanged.connect(lambda s: self.cond_smallest.setEnabled(bool(s)))
        row += 1

        self.cond_largest_cb = QCheckBox("Max largest side:")
        cond_grid.addWidget(self.cond_largest_cb, row, 0)
        self.cond_largest = QSpinBox()
        self.cond_largest.setRange(1, 10000)
        self.cond_largest.setEnabled(False)
        cond_grid.addWidget(self.cond_largest, row, 1)
        self.cond_largest_cb.stateChanged.connect(lambda s: self.cond_largest.setEnabled(bool(s)))
        row += 1

        self.cond_pixels_cb = QCheckBox("Max pixels:")
        cond_grid.addWidget(self.cond_pixels_cb, row, 0)
        self.cond_pixels = QSpinBox()
        self.cond_pixels.setRange(1, 1_000_000_000)
        self.cond_pixels.setEnabled(False)
        cond_grid.addWidget(self.cond_pixels, row, 1)
        self.cond_pixels_cb.stateChanged.connect(lambda s: self.cond_pixels.setEnabled(bool(s)))
        row += 1

        self.cond_min_aspect_cb = QCheckBox("Min aspect ratio:")
        cond_grid.addWidget(self.cond_min_aspect_cb, row, 0)
        self.cond_min_aspect = QDoubleSpinBox()
        self.cond_min_aspect.setRange(0.01, 100.0)
        self.cond_min_aspect.setSingleStep(0.1)
        self.cond_min_aspect.setEnabled(False)
        cond_grid.addWidget(self.cond_min_aspect, row, 1)
        self.cond_min_aspect_cb.stateChanged.connect(lambda s: self.cond_min_aspect.setEnabled(bool(s)))
        row += 1

        self.cond_max_aspect_cb = QCheckBox("Max aspect ratio:")
        cond_grid.addWidget(self.cond_max_aspect_cb, row, 0)
        self.cond_max_aspect = QDoubleSpinBox()
        self.cond_max_aspect.setRange(0.01, 100.0)
        self.cond_max_aspect.setSingleStep(0.1)
        self.cond_max_aspect.setEnabled(False)
        cond_grid.addWidget(self.cond_max_aspect, row, 1)
        self.cond_max_aspect_cb.stateChanged.connect(lambda s: self.cond_max_aspect.setEnabled(bool(s)))
        row += 1

        cond_grid.addWidget(QLabel("Orientation:"), row, 0)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Any", "landscape", "portrait", "square"])
        cond_grid.addWidget(self.orientation_combo, row, 1)
        row += 1

        cond_grid.addWidget(QLabel("Input formats:"), row, 0)
        self.input_formats_edit = QLineEdit()
        self.input_formats_edit.setPlaceholderText("jpg,png")
        cond_grid.addWidget(self.input_formats_edit, row, 1)
        row += 1

        cond_grid.addWidget(QLabel("Transparency:"), row, 0)
        self.transparency_combo = QComboBox()
        self.transparency_combo.addItems(["Any", "Requires", "No"])
        cond_grid.addWidget(self.transparency_combo, row, 1)
        row += 1

        self.cond_bytes_cb = QCheckBox("Max file size (bytes):")
        cond_grid.addWidget(self.cond_bytes_cb, row, 0)
        self.cond_bytes = QSpinBox()
        self.cond_bytes.setRange(1, 1_000_000_000)
        self.cond_bytes.setEnabled(False)
        cond_grid.addWidget(self.cond_bytes, row, 1)
        self.cond_bytes_cb.stateChanged.connect(lambda s: self.cond_bytes.setEnabled(bool(s)))
        row += 1

        cond_grid.addWidget(QLabel("Required EXIF (k=v,...):"), row, 0)
        self.exif_edit = QLineEdit()
        cond_grid.addWidget(self.exif_edit, row, 1)

        self.conditions_box.add_widget(conditions_widget)
        layout.addWidget(self.conditions_box)

        if not self.allow_conditions:
            self.conditions_box.toggle_button.setText("Conditions (default profile - always used)")
            self.conditions_box.toggle_button.setEnabled(False)
            self.conditions_box.content.setEnabled(False)

    # ------------------------------------------------------------------
    def get_parameters(self) -> dict[str, Any]:
        """Return compression parameters from the panel."""
        return {
            "quality": self.quality.value(),
            "max_largest_side": self.max_largest.value() if self.max_largest_cb.isChecked() else None,
            "max_smallest_side": self.max_smallest.value() if self.max_smallest_cb.isChecked() else None,
            "preserve_structure": self.preserve_cb.isChecked(),
            "output_format": self.format_combo.currentText(),
            "jpeg_params": {
                "progressive": self.jpeg_progressive.isChecked(),
                "subsampling": self.jpeg_subsampling.currentText(),
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
        return ProfileConditions(
            max_input_smallest_side=self.cond_smallest.value() if self.cond_smallest_cb.isChecked() else None,
            max_input_largest_side=self.cond_largest.value() if self.cond_largest_cb.isChecked() else None,
            max_input_pixels=self.cond_pixels.value() if self.cond_pixels_cb.isChecked() else None,
            min_aspect_ratio=self.cond_min_aspect.value() if self.cond_min_aspect_cb.isChecked() else None,
            max_aspect_ratio=self.cond_max_aspect.value() if self.cond_max_aspect_cb.isChecked() else None,
            orientation=None if self.orientation_combo.currentText() == "Any" else self.orientation_combo.currentText(),
            input_formats=[s.strip() for s in self.input_formats_edit.text().split(",") if s.strip()] or None,
            requires_transparency={
                "Any": None,
                "Requires": True,
                "No": False,
            }[self.transparency_combo.currentText()],
            max_input_bytes=self.cond_bytes.value() if self.cond_bytes_cb.isChecked() else None,
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
            preserve_structure=params["preserve_structure"],
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
        self.preserve_cb.setChecked(profile.preserve_structure)

        jpeg = profile.jpeg_params
        self.jpeg_progressive.setChecked(jpeg.get("progressive", JPEG_DEFAULTS["progressive"]))
        self.jpeg_subsampling.setCurrentText(jpeg.get("subsampling", JPEG_DEFAULTS["subsampling"]))
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
        if cond.max_input_smallest_side is not None:
            self.cond_smallest_cb.setChecked(True)
            self.cond_smallest.setValue(cond.max_input_smallest_side)
        else:
            self.cond_smallest_cb.setChecked(False)
            self.cond_smallest.setEnabled(False)

        if cond.max_input_largest_side is not None:
            self.cond_largest_cb.setChecked(True)
            self.cond_largest.setValue(cond.max_input_largest_side)
        else:
            self.cond_largest_cb.setChecked(False)
            self.cond_largest.setEnabled(False)

        if cond.max_input_pixels is not None:
            self.cond_pixels_cb.setChecked(True)
            self.cond_pixels.setValue(cond.max_input_pixels)
        else:
            self.cond_pixels_cb.setChecked(False)
            self.cond_pixels.setEnabled(False)

        if cond.min_aspect_ratio is not None:
            self.cond_min_aspect_cb.setChecked(True)
            self.cond_min_aspect.setValue(cond.min_aspect_ratio)
        else:
            self.cond_min_aspect_cb.setChecked(False)
            self.cond_min_aspect.setEnabled(False)

        if cond.max_aspect_ratio is not None:
            self.cond_max_aspect_cb.setChecked(True)
            self.cond_max_aspect.setValue(cond.max_aspect_ratio)
        else:
            self.cond_max_aspect_cb.setChecked(False)
            self.cond_max_aspect.setEnabled(False)

        if cond.orientation:
            self.orientation_combo.setCurrentText(cond.orientation)
        else:
            self.orientation_combo.setCurrentText("Any")

        if cond.input_formats:
            self.input_formats_edit.setText(",".join(cond.input_formats))
        else:
            self.input_formats_edit.clear()

        if cond.requires_transparency is True:
            self.transparency_combo.setCurrentText("Requires")
        elif cond.requires_transparency is False:
            self.transparency_combo.setCurrentText("No")
        else:
            self.transparency_combo.setCurrentText("Any")

        if cond.max_input_bytes is not None:
            self.cond_bytes_cb.setChecked(True)
            self.cond_bytes.setValue(cond.max_input_bytes)
        else:
            self.cond_bytes_cb.setChecked(False)
            self.cond_bytes.setEnabled(False)

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
        self.preserve_cb.setChecked(BASIC_DEFAULTS["preserve_structure"])

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
        self.cond_largest_cb.setChecked(False)
        self.cond_largest.setEnabled(False)
        self.cond_pixels_cb.setChecked(False)
        self.cond_pixels.setEnabled(False)
        self.cond_min_aspect_cb.setChecked(False)
        self.cond_min_aspect.setEnabled(False)
        self.cond_max_aspect_cb.setChecked(False)
        self.cond_max_aspect.setEnabled(False)
        self.orientation_combo.setCurrentText("Any")
        self.input_formats_edit.clear()
        self.transparency_combo.setCurrentText("Any")
        self.cond_bytes_cb.setChecked(False)
        self.cond_bytes.setEnabled(False)
        self.exif_edit.clear()
