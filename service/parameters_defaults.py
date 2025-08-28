"""Default compression parameter values."""

from typing import TypedDict


class BasicDefaults(TypedDict):
    quality: int
    max_largest_enabled: bool
    max_largest_side: int
    max_smallest_enabled: bool
    max_smallest_side: int
    output_format: str
    preserve_structure: bool


class JpegDefaults(TypedDict):
    progressive: bool
    subsampling: str
    optimize: bool
    smooth: int
    keep_rgb: bool


class WebpDefaults(TypedDict):
    lossless: bool
    method: int
    alpha_quality: int
    exact: bool


class AvifDefaults(TypedDict):
    subsampling: str
    speed: int
    codec: str
    range: str
    qmin: int
    qmax: int
    autotiling: bool
    tile_rows: int
    tile_cols: int


BASIC_DEFAULTS: BasicDefaults = {
    "quality": 75,
    "max_largest_enabled": False,
    "max_largest_side": 1920,
    "max_smallest_enabled": True,
    "max_smallest_side": 1080,
    "output_format": "JPEG",
    "preserve_structure": True,
}

JPEG_DEFAULTS: JpegDefaults = {
    "progressive": False,
    "subsampling": "Auto (-1)",
    "optimize": False,
    "smooth": 0,
    "keep_rgb": False,
}

WEBP_DEFAULTS: WebpDefaults = {
    "lossless": False,
    "method": 4,
    "alpha_quality": 100,
    "exact": False,
}

AVIF_DEFAULTS: AvifDefaults = {
    "subsampling": "4:2:0",
    "speed": 6,
    "codec": "auto",
    "range": "full",
    "qmin": -1,
    "qmax": -1,
    "autotiling": True,
    "tile_rows": 0,
    "tile_cols": 0,
}
