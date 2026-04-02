# tests/test_camera_with_files.py
import sys
sys.path.append('/home/albasam/camera_project')

from hardware.camera import Camera
from imaging.file_manager import get_capture_path
import time


def main():
    camera = Camera()

    print("=== Raw auto capture ===")
    auto_path = get_capture_path(kind="raw", prefix="auto")
    camera.capture_auto(str(auto_path))
    print(f"Saved auto to {auto_path}")

    settings = camera.get_current_settings()
    iso = settings["iso"]
    shutter = settings["exposure_seconds"]
    print(f"Auto baseline: ISO {iso}, {shutter:.3f}s")

    print("\n=== Raw manual sequence for stacking ===")
    paths = []
    for i in range(5):
        path = get_capture_path(
            kind="raw",
            prefix="manual",
            label=f"seq{i}",
        )
        camera.capture(str(path), iso=iso, shutter_speed=shutter)
        print(f"Saved frame {i} to {path}")
        paths.append(path)
        time.sleep(0.3)

    camera.stop()
    print("\nDone. Check captures/raw/ for files.")


if __name__ == "__main__":
    main()
