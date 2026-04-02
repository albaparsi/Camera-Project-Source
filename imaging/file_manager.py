# captures/file_manager.py
from pathlib import Path
from datetime import datetime
from typing import Literal, Optional

# Always write into the top-level captures directory
BASE_DIR = Path(__file__).resolve().parent.parent / "captures"

CaptureKind = Literal["raw", "stacked", "combined"]

# Optional subfolder for current session, e.g. "session_2026-03-17T01-55-00"
CURRENT_SESSION_SUBDIR: Optional[str] = None
SESSION_IMAGE_COUNTER = 0


def _timestamp() -> str:
    """Return a compact timestamp for filenames."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def set_session_subdir(name: Optional[str]) -> None:
    """
    Set or clear the current session subdirectory.

    If name is None, paths go directly under captures/raw, captures/stacked, etc.
    If name is "session_xxx", paths go under captures/session_xxx/raw, etc.
    """
    global CURRENT_SESSION_SUBDIR, SESSION_IMAGE_COUNTER
    CURRENT_SESSION_SUBDIR = name
    SESSION_IMAGE_COUNTER = 0


def make_new_session_name() -> str:
    """Generate a new session folder name."""
    return f"session_{_timestamp()}"


def get_capture_path(
    kind: CaptureKind,
    prefix: str = "",
    ext: str = "jpg",
    label: Optional[str] = None,
) -> Path:
    """
    Build a path for a capture file under captures[/session]/raw|stacked|combined.

    Args:
        kind: 'raw', 'stacked', or 'combined'
        prefix: short string like 'auto', 'manual', 'stack'
        ext: file extension without dot ('jpg', 'png', 'tiff')
        label: optional extra label (e.g. filter name or index)

    Returns:
        Path object. The subdirectory is created if needed.
    """
    if kind not in ("raw", "stacked", "combined"):
        raise ValueError("kind must be 'raw', 'stacked', or 'combined'")

    # Base may include a session subdir
    if CURRENT_SESSION_SUBDIR:
        base = BASE_DIR / CURRENT_SESSION_SUBDIR
    else:
        base = BASE_DIR

    subdir = base / kind
    subdir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()

    # Increment per-session counter and format as imageNNN
    global SESSION_IMAGE_COUNTER
    SESSION_IMAGE_COUNTER += 1
    image_token = f"image{SESSION_IMAGE_COUNTER:03d}"

    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(ts)
    parts.append(image_token)
    if label:
        parts.append(str(label))

    stem = "_".join(parts)
    filename = f"{stem}.{ext}"

    return subdir / filename
