import os
from datetime import timedelta
from pathlib import Path


def copy_times_from_src(src: Path, dst: Path) -> None:
    """Copy access and modification times from src to dst."""
    st = src.stat()
    os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))


def format_timedelta(delta: timedelta) -> str:
    """Format a timedelta to a human-readable string."""
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)
