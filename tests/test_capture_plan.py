# tests/test_capture_plan.py
import sys
sys.path.append('/home/albasam/camera_project')

from hardware.camera import Camera
from imaging.capture_manager import CapturePlan, FilterSpec, ExposureSetting, run_capture_plan

def main():
    cam = Camera()

    # Example: user selects 3 filters, and wants auto exposure for them (even in "manual filter selection" mode)
    plan = CapturePlan(
        filters=[
            FilterSpec(0, "F0", ExposureSetting.auto()),
            FilterSpec(3, "F3", ExposureSetting.auto()),
            FilterSpec(7, "F7", ExposureSetting.auto()),
        ],
        sequences=2,            # 2 full rounds
        stack_per_filter=True,  # stacks per filter across the 2 rounds
        stack_method="median",
    )

    result = run_capture_plan(cam, plan)
    print(result["stacked_by_filter"])
    print("Done. Check captures/raw and captures/stacked.")

if __name__ == "__main__":
    main()
