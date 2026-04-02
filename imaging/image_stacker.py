# imaging/image_stacker.py
from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional, Tuple, Dict, Any

import numpy as np
from PIL import Image

from imaging.file_manager import get_capture_path

StackMethod = Literal["mean", "median"]
ImageMode = Literal["L", "RGB"]


def _load(path: Path, mode: ImageMode) -> np.ndarray:
    img = Image.open(path).convert(mode)
    return np.asarray(img, dtype=np.float32)


def stack_frames(
    input_paths: List[Path],
    out_path: Optional[Path] = None,
    method: StackMethod = "median",
    mode: ImageMode = "L",
    return_stats: bool = False,
    label: Optional[str] = None,
    ext: str = "jpg",
) -> Path | Tuple[Path, Dict[str, Any]]:
    """
    Stack multiple frames of the SAME filter/scene into one output image.

    If out_path is None, the output is saved via file_manager to captures/stacked/.
    """
    if not input_paths:
        raise ValueError("No input images provided")

    paths = [Path(p) for p in input_paths]
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Missing input image: {p}")

    arrays = [_load(p, mode) for p in paths]

    shape0 = arrays[0].shape
    for i, a in enumerate(arrays[1:], start=1):
        if a.shape != shape0:
            raise ValueError(f"Image size mismatch: {paths[0]}={shape0} vs {paths[i]}={a.shape}")

    stack = np.stack(arrays, axis=0)

    if method == "mean":
        combined = stack.mean(axis=0)
    elif method == "median":
        combined = np.median(stack, axis=0)
    else:
        raise ValueError("method must be 'mean' or 'median'")

    combined_u8 = np.clip(combined, 0, 255).astype(np.uint8)
    out_img = Image.fromarray(combined_u8, mode=mode)

    if out_path is None:
        out_path = get_capture_path(
            kind="stacked",
            prefix=f"stack_{method}",
            label=label,
            ext=ext,
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)  # create parent dirs if missing [web:254]
    out_img.save(out_path)

    if not return_stats:
        return out_path

    stats: Dict[str, Any] = {
        "n_images": int(stack.shape[0]),
        "mode": mode,
        "method": method,
        "shape": tuple(shape0),
        "mean": float(combined_u8.mean()),
        "min": int(combined_u8.min()),
        "max": int(combined_u8.max()),
    }
    return out_path, stats


def stack_frames_mono(
    input_paths: List[Path],
    out_path: Optional[Path] = None,
    method: StackMethod = "median",
    label: Optional[str] = None,
    ext: str = "jpg",
) -> Path:
    result = stack_frames(
        input_paths=input_paths,
        out_path=out_path,
        method=method,
        mode="L",
        return_stats=False,
        label=label,
        ext=ext,
    )
    # return_stats=False => Path
    return result  # type: ignore[return-value]
