from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from service.compression_profiles import CompressionProfile, ProfileConditions
from service.parameters_defaults import BASIC_DEFAULTS


class ProfilePanel(QWidget):
    """Panel containing compression parameters and matching conditions."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
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

        # Conditions sub-panel
        self.conditions_group = QGroupBox("Conditions")
        cond_grid = QGridLayout(self.conditions_group)

        self.cond_smallest_cb = QCheckBox("Max smallest side:")
        cond_grid.addWidget(self.cond_smallest_cb, 0, 0)
        self.cond_smallest = QSpinBox()
        self.cond_smallest.setRange(1, 10000)
        self.cond_smallest.setEnabled(False)
        cond_grid.addWidget(self.cond_smallest, 0, 1)
        self.cond_smallest_cb.stateChanged.connect(lambda s: self.cond_smallest.setEnabled(bool(s)))

        cond_grid.addWidget(QLabel("Orientation:"), 1, 0)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Any", "landscape", "portrait", "square"])
        cond_grid.addWidget(self.orientation_combo, 1, 1)

        layout.addWidget(self.conditions_group)

    # ------------------------------------------------------------------
    def get_parameters(self) -> dict[str, Any]:
        """Return compression parameters from the panel."""
        return {
            "quality": self.quality.value(),
            "max_largest_side": self.max_largest.value() if self.max_largest_cb.isChecked() else None,
            "max_smallest_side": self.max_smallest.value() if self.max_smallest_cb.isChecked() else None,
            "preserve_structure": self.preserve_cb.isChecked(),
            "output_format": self.format_combo.currentText(),
        }

    def get_conditions(self) -> ProfileConditions:
        """Return matching conditions configured in the panel."""
        return ProfileConditions(
            max_input_smallest_side=self.cond_smallest.value() if self.cond_smallest_cb.isChecked() else None,
            orientation=None if self.orientation_combo.currentText() == "Any" else self.orientation_combo.currentText(),
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

        cond = profile.conditions
        if cond.max_input_smallest_side is not None:
            self.cond_smallest_cb.setChecked(True)
            self.cond_smallest.setValue(cond.max_input_smallest_side)
        else:
            self.cond_smallest_cb.setChecked(False)
            self.cond_smallest.setEnabled(False)

        if cond.orientation:
            self.orientation_combo.setCurrentText(cond.orientation)
        else:
            self.orientation_combo.setCurrentText("Any")

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

        self.cond_smallest_cb.setChecked(False)
        self.cond_smallest.setEnabled(False)
        self.orientation_combo.setCurrentText("Any")
