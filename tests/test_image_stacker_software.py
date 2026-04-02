import sys
sys.path.append('/home/albasam/camera_project')  # keep your current style

from pathlib import Path
import shutil
import numpy as np
from PIL import Image

from imaging.image_stacker import stack_frames_mono


def _write_dummy_gray(path: Path, seed: int, base: int = 80, noise: int = 25, size=(256, 256)):
    rng = np.random.default_rng(seed)
    img = rng.normal(loc=base, scale=noise, size=size).clip(0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, mode="L").save(path)


def _verify_image(path: Path):
    # Fast validity check (detects corruption/truncation)
    with Image.open(path) as im:
        im.verify()


def main():
    root = Path("tests/_tmp_stack")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    inputs = []
    for i in range(6):
        p = root / f"frame_{i}.jpg"
        _write_dummy_gray(p, seed=1234 + i)
        inputs.append(p)

    out_median = stack_frames_mono(inputs, method="median", label="software_test_median")
    out_mean = stack_frames_mono(inputs, method="mean", label="software_test_mean")

    assert out_median.exists(), "Median stacked output missing"
    assert out_mean.exists(), "Mean stacked output missing"

    _verify_image(out_median)
    _verify_image(out_mean)

    print("Outputs:", out_median, out_mean)



if __name__ == "__main__":
    main()
