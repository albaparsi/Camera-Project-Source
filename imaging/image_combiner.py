# imaging/image_combiner.py
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
import numpy as np
from PIL import Image

CombineMode = Literal["rgb", "grayscale_mean", "grayscale_max", "grayscale_sum"]


def _load_mono(path: Path) -> np.ndarray:
    """Load image as grayscale float32 array."""
    img = Image.open(path).convert("L")
    return np.asarray(img, dtype=np.float32)


def combine_filters_rgb(
    filter_images: Dict[str, Path],
    r_filter: str,
    g_filter: str,
    b_filter: str,
    out_path: Path,
) -> Path:
    """
    Combine 3 monochrome filter images into an RGB color image.
    
    Args:
        filter_images: Dict mapping filter name -> image path.
        r_filter: Key for the red channel.
        g_filter: Key for the green channel.
        b_filter: Key for the blue channel.
        out_path: Where to save the RGB output.
    
    Returns:
        out_path
    """
    if r_filter not in filter_images:
        raise ValueError(f"Red filter '{r_filter}' not in filter_images")
    if g_filter not in filter_images:
        raise ValueError(f"Green filter '{g_filter}' not in filter_images")
    if b_filter not in filter_images:
        raise ValueError(f"Blue filter '{b_filter}' not in filter_images")

    r = _load_mono(filter_images[r_filter])
    g = _load_mono(filter_images[g_filter])
    b_arr = _load_mono(filter_images[b_filter])

    # Validate same size
    if not (r.shape == g.shape == b_arr.shape):
        raise ValueError(f"Size mismatch: R={r.shape}, G={g.shape}, B={b_arr.shape}")

    # Stack into (H, W, 3)
    rgb = np.stack([r, g, b_arr], axis=-1)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    out_img = Image.fromarray(rgb, mode="RGB")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(out_path)

    return out_path


def combine_filters_grayscale(
    filter_images: Dict[str, Path],
    mode: Literal["mean", "max", "sum"] = "mean",
    out_path: Optional[Path] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Path:
    """
    Combine multiple monochrome filter images into one grayscale output.
    
    Args:
        filter_images: Dict mapping filter name -> image path.
        mode: 'mean', 'max', or 'sum'.
        out_path: Where to save the combined grayscale output.
        weights: Optional per-filter weights (only used for 'mean' mode).
    
    Returns:
        out_path
    """
    if not filter_images:
        raise ValueError("No filter images provided")
    
    if out_path is None:
        raise ValueError("out_path must be provided")

    arrays = []
    filter_names = []
    for name, path in filter_images.items():
        arr = _load_mono(path)
        arrays.append(arr)
        filter_names.append(name)

    # Validate same size
    shape0 = arrays[0].shape
    for i, a in enumerate(arrays[1:], start=1):
        if a.shape != shape0:
            raise ValueError(f"Size mismatch: {filter_names[0]}={shape0} vs {filter_names[i]}={a.shape}")

    stack = np.stack(arrays, axis=0)  # (N, H, W)

    if mode == "mean":
        if weights:
            # Weighted mean
            w = np.array([weights.get(name, 1.0) for name in filter_names], dtype=np.float32)
            w = w / w.sum()  # normalize
            combined = np.average(stack, axis=0, weights=w)
        else:
            combined = stack.mean(axis=0)
    elif mode == "max":
        combined = stack.max(axis=0)
    elif mode == "sum":
        combined = stack.sum(axis=0)
    else:
        raise ValueError("mode must be 'mean', 'max', or 'sum'")

    combined = np.clip(combined, 0, 255).astype(np.uint8)
    out_img = Image.fromarray(combined, mode="L")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(out_path)

    return out_path


def combine_filters(
    filter_images: Dict[str, Path],
    out_path: Path,
    mode: CombineMode = "grayscale_mean",
    rgb_mapping: Optional[Tuple[str, str, str]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Path:
    """
    Universal combine function: RGB or grayscale.
    
    Args:
        filter_images: Dict mapping filter name (e.g., "F0", "Red") -> stacked/raw image path.
        out_path: Output path in captures/combined/.
        mode: Combine mode.
        rgb_mapping: (r_filter, g_filter, b_filter) required if mode='rgb'.
        weights: Optional per-filter weights (grayscale mean only).
    
    Returns:
        out_path
    """
    if mode == "rgb":
        if rgb_mapping is None or len(rgb_mapping) != 3:
            raise ValueError("rgb mode requires rgb_mapping=(r_filter, g_filter, b_filter)")
        return combine_filters_rgb(
            filter_images,
            r_filter=rgb_mapping[0],
            g_filter=rgb_mapping[1],
            b_filter=rgb_mapping[2],
            out_path=out_path,
        )
    elif mode.startswith("grayscale_"):
        gray_mode = mode.replace("grayscale_", "")
        return combine_filters_grayscale(
            filter_images,
            mode=gray_mode,  # type: ignore
            out_path=out_path,
            weights=weights,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")
