"""Configuration loader for image cache limits."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CacheConfig:
    """Cache configuration.

    ``max_loaded_images`` defines the maximum number of full-size images kept in
    memory. ``0`` disables the limit.
    """

    max_loaded_images: int = 0


def load_cache_config(path: Path | None = None) -> CacheConfig:
    """Load cache configuration from ``cache_config.toml``."""

    config_path = path or Path(__file__).resolve().parent.parent / "cache_config.toml"
    if not config_path.exists():
        return CacheConfig()

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return CacheConfig()

    return CacheConfig(
        max_loaded_images=int(data.get("max_loaded_images", 0)),
    )
