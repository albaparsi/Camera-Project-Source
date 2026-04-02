# tests/test_stacking.py
import sys
sys.path.append('/home/albasam/camera_project')

from pathlib import Path
from hardware.camera import Camera
from imaging.image_stacker import stack_images
from imaging.file_manager import get_capture_path
import time


def main():
    cam = Camera()

    # 1) Get baseline from auto
    baseline_path = get_capture_path(kind="raw", prefix="auto")
    cam.capture_auto(str(baseline_path))
    settings = cam.get_current_settings()
    iso = settings["iso"]
    shutter = settings["exposure_seconds"]

    # 2) Capture a small sequence for stacking
    raw_paths = []
    for i in range(5):
        p = get_capture_path(kind="raw", prefix="stacksrc", label=f"{i}")
        cam.capture(str(p), iso=iso, shutter_speed=shutter)
        raw_paths.append(p)
        time.sleep(0.2)

    cam.stop()

    # 3) Stack them
    out_path = stack_images(raw_paths, method="median")
    print(f"Stacked image saved to: {out_path}")


if __name__ == "__main__":
    main()
