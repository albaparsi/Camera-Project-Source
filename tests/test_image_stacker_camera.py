import sys
sys.path.append('/home/albasam/camera_project')

from pathlib import Path
import numpy as np
from PIL import Image

from hardware.camera import Camera
from imaging.file_manager import get_capture_path
from imaging.image_stacker import stack_frames_mono


def _image_stats(path: Path) -> dict:
    img = Image.open(path).convert("L")
    arr = np.asarray(img, dtype=np.uint8)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": int(arr.min()),
        "max": int(arr.max()),
    }


def main():
    N_FRAMES = 6
    METHOD = "median"   # "mean" or "median"

    cam = Camera()
    cam.start()

    try:
        # 1) Take one auto baseline frame
        baseline_path = get_capture_path(kind="raw", prefix="baseline_auto", label="stacktest", ext="jpg")
        cam.capture_auto(str(baseline_path))

        settings = cam.get_current_settings()
        iso = settings["iso"]
        exposure_s = settings["exposure_seconds"]
        print(f"Baseline auto picked: ISO={iso}, exposure={exposure_s:.4f}s")
        print("Baseline stats:", _image_stats(baseline_path))

        # 2) Capture N frames with locked manual settings (better for stacking)
        raw_paths = []
        for i in range(N_FRAMES):
            p = get_capture_path(kind="raw", prefix="raw", label=f"stacktest_frame{i}", ext="jpg")
            cam.capture(str(p), iso=iso, shutter_speed=exposure_s)
            raw_paths.append(p)
            print(f"Saved raw: {p} stats: {_image_stats(p)}")

    finally:
        cam.stop()

    # 3) Stack and save
    out_path = get_capture_path(kind="stacked", prefix=f"stack_{METHOD}", label=f"stacktest_{N_FRAMES}frames", ext="jpg")
    stack_frames_mono(raw_paths, out_path=out_path, method=METHOD)

    print(f"\nSaved stacked: {out_path}")
    print("Stacked stats:", _image_stats(out_path))
    print("\nCheck folders:")
    print(" - captures/raw/")
    print(" - captures/stacked/")


if __name__ == "__main__":
    main()
