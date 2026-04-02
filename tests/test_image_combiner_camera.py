import sys
sys.path.append('/home/albasam/camera_project')

from pathlib import Path
import numpy as np
from PIL import Image

from hardware.camera import Camera
from imaging.file_manager import get_capture_path
from imaging.image_combiner import combine_filters


def _verify_image(path: Path) -> None:
    with Image.open(path) as im:
        im.verify()  # raises exception if corrupted


def _stats(path: Path) -> dict:
    arr = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": int(arr.min()),
        "max": int(arr.max()),
    }


def main():
    cam = Camera()
    cam.start()

    try:
        # 1) Auto baseline (get stable manual settings)
        base = get_capture_path(kind="raw", prefix="baseline_auto", label="combine_test", ext="jpg")
        cam.capture_auto(str(base))
        s = cam.get_current_settings()
        iso = s["iso"]
        exp_s = s["exposure_seconds"]
        print("Baseline:", base, "stats:", _stats(base))
        print(f"Locked settings: ISO={iso}, exposure={exp_s:.4f}s")

        # 2) Capture 3 raw frames to act as "filters"
        f0 = get_capture_path(kind="raw", prefix="raw", label="F0_R", ext="jpg")
        f1 = get_capture_path(kind="raw", prefix="raw", label="F1_G", ext="jpg")
        f2 = get_capture_path(kind="raw", prefix="raw", label="F2_B", ext="jpg")

        for p in (f0, f1, f2):
            cam.capture(str(p), iso=iso, shutter_speed=exp_s)
            print("Saved:", p, "stats:", _stats(p))

    finally:
        cam.stop()

    # 3) Combine (RGB + grayscale mean)
    filter_images = {"F0": f0, "F1": f1, "F2": f2}

    out_rgb = get_capture_path(kind="combined", prefix="combined_rgb", label="F0_F1_F2", ext="jpg")
    out_gray = get_capture_path(kind="combined", prefix="combined_gray_mean", label="F0_F1_F2", ext="jpg")

    combine_filters(filter_images, out_path=out_rgb, mode="rgb", rgb_mapping=("F0", "F1", "F2"))
    combine_filters(filter_images, out_path=out_gray, mode="grayscale_mean")

    assert out_rgb.exists(), "RGB output not created"
    assert out_gray.exists(), "Gray output not created"

    _verify_image(out_rgb)
    _verify_image(out_gray)

    print("\nOK: combine test passed")
    print("RGB:", out_rgb)
    print("Gray:", out_gray)
    print("Gray stats:", _stats(out_gray))


if __name__ == "__main__":
    main()
