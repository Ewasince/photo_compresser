import os
from pathlib import Path


def copy_times_from_src(src: Path, dst: Path) -> None:
    """Copy access and modification times from src to dst."""
    st = src.stat()
    os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))
