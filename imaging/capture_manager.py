# imaging/capture_manager.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any
import time

from PIL import Image  # for downscaling

from hardware.camera import Camera
from imaging.file_manager import get_capture_path
from imaging.image_stacker import stack_frames_mono  # renamed


ExposureMode = Literal["auto", "manual"]
StackMethod = Literal["mean", "median"]
OutputScale = Literal["full", "half"]


@dataclass(frozen=True)
class ExposureSetting:
    """
    - mode="auto": camera decides ISO + exposure time
    - mode="manual": user specifies ISO + exposure_ms (milliseconds)
    """
    mode: ExposureMode = "auto"
    iso: Optional[int] = None
    exposure_ms: Optional[float] = None  # user-facing number (ms)

    @staticmethod
    def auto() -> "ExposureSetting":
        return ExposureSetting(mode="auto")

    @staticmethod
    def manual(iso: int, exposure_ms: float) -> "ExposureSetting":
        return ExposureSetting(mode="manual", iso=iso, exposure_ms=exposure_ms)


@dataclass(frozen=True)
class FilterSpec:
    filter_id: int  # 0..7
    name: str
    exposure: ExposureSetting = field(default_factory=ExposureSetting.auto)
    enabled: bool = True


@dataclass(frozen=True)
class CapturePlan:
    """
    sequences = number of full filter rounds (1..5).
    frames_per_filter = number of frames captured per filter per sequence (1..10).
    Total frames per filter = sequences * frames_per_filter.
    """
    filters: List[FilterSpec]

    sequences: int = 1                  # 1..5 (full wheel rounds)
    frames_per_filter: int = 1          # 1..10 (frames per filter per round)

    settle_after_move_s: float = 0.2    # used later when motor exists
    inter_frame_delay_s: float = 0.0    # optional delay between frames at same filter

    stack_per_filter: bool = False      # stack within each filter across all seq+frames
    stack_method: StackMethod = "median"

    image_ext: str = "jpg"
    output_scale: OutputScale = "full"  # "full" or "half"


class FilterWheelMock:
    """Fallback wheel used when motor hardware is unavailable."""
    def move_to(self, filter_id: int) -> None:
        return


def _make_default_wheel() -> object:
    """Create a real wheel controller, or fall back to mock on non-Pi setups."""

    try:
        from hardware.filter_wheel import StepperFilterWheel

        return StepperFilterWheel(start_position=0)
    except Exception as exc:
        print(f"[HW] Stepper wheel unavailable: {exc}. Using mock wheel.")
        return FilterWheelMock()


def _safe_name(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s).strip("_")


def _exposure_ms_to_s(exposure_ms: float) -> float:
    return float(exposure_ms) / 1000.0


def _downscale_half_inplace(path: Path) -> None:
    """Resize image at path to half width/height in-place."""
    try:
        img = Image.open(path)
        w, h = img.size
        new_size = (max(1, w // 2), max(1, h // 2))
        img = img.resize(new_size, Image.LANCZOS)
        img.save(path)
        print(f"[DOWNSCALE] {path.name}: {w}x{h} -> {new_size[0]}x{new_size[1]}")
    except Exception as e:
        print(f"[DOWNSCALE] failed for {path}: {e}")


def run_capture_plan(
    camera: Camera,
    plan: CapturePlan,
    wheel: Optional[object] = None,
) -> Dict[str, Any]:
    """
    Executes:
      for seq in 0..sequences-1:
        for each enabled filter:
          move wheel
          for frame in 0..frames_per_filter-1:
            capture one raw frame (auto/manual) and save

    If stack_per_filter=True and there is >1 raw frame for a filter:
      stack all that filter's frames into captures/stacked/

    If plan.output_scale == "half":
      raw and stacked images are downscaled to half resolution (per dimension).
    """
    if plan.sequences < 1 or plan.sequences > 5:
        raise ValueError("sequences must be between 1 and 5")

    if plan.frames_per_filter < 1 or plan.frames_per_filter > 10:
        raise ValueError("frames_per_filter must be between 1 and 10")

    enabled_filters = [f for f in plan.filters if f.enabled]
    if not enabled_filters:
        raise ValueError("No enabled filters in plan")

    if wheel is None:
        wheel = _make_default_wheel()

    print(f"[PLAN] image_ext={plan.image_ext}, output_scale={plan.output_scale}, stack_per_filter={plan.stack_per_filter}")

    raw_by_filter: Dict[int, List[Path]] = {f.filter_id: [] for f in enabled_filters}
    metadata_log: List[Dict[str, Any]] = []

    light_off = None
    run_find_start = None
    try:
        from ui import testlight  # type: ignore[import-not-found]

        testlight.light_on()
        light_off = testlight.light_off
        print("[HW] Sequence LED on")
    except Exception as exc:
        print(f"[HW] Sequence LED unavailable: {exc}")

    try:
        from ui.FindStart import run_find_start as _run_find_start  # type: ignore[import-not-found]

        run_find_start = _run_find_start
    except Exception as exc:
        print(f"[HW] FindStart unavailable: {exc}")

    camera.start()
    try:
        for seq in range(plan.sequences):
            for f in enabled_filters:
                if hasattr(wheel, "move_to"):
                    wheel.move_to(f.filter_id)
                    time.sleep(plan.settle_after_move_s)

                for frame_idx in range(plan.frames_per_filter):
                    fname_label = f"F{f.filter_id}_{_safe_name(f.name)}_seq{seq}_frame{frame_idx}"
                    raw_path = get_capture_path(
                        kind="raw",
                        prefix="raw",
                        label=fname_label,
                        ext=plan.image_ext,
                    )

                    if f.exposure.mode == "auto":
                        camera.capture_auto(str(raw_path))
                        used = camera.get_current_settings()
                        metadata_log.append({
                            "path": str(raw_path),
                            "filter_id": f.filter_id,
                            "filter_name": f.name,
                            "seq": seq,
                            "frame": frame_idx,
                            "mode": "auto",
                            "used_iso": used.get("iso"),
                            "used_exposure_s": used.get("exposure_seconds"),
                            "used_exposure_ms": (used.get("exposure_seconds") or 0.0) * 1000.0,
                        })
                    else:
                        if f.exposure.iso is None or f.exposure.exposure_ms is None:
                            raise ValueError(
                                f"Manual exposure requires iso and exposure_ms (filter_id={f.filter_id})"
                            )

                        exposure_s = _exposure_ms_to_s(f.exposure.exposure_ms)
                        camera.capture(
                            str(raw_path),
                            iso=int(f.exposure.iso),
                            shutter_speed=exposure_s,
                        )
                        metadata_log.append({
                            "path": str(raw_path),
                            "filter_id": f.filter_id,
                            "filter_name": f.name,
                            "seq": seq,
                            "frame": frame_idx,
                            "mode": "manual",
                            "iso": int(f.exposure.iso),
                            "exposure_ms": float(f.exposure.exposure_ms),
                            "exposure_s": exposure_s,
                        })

                    # Downscale raw if requested
                    if plan.output_scale == "half":
                        _downscale_half_inplace(raw_path)

                    raw_by_filter[f.filter_id].append(raw_path)

                    if plan.inter_frame_delay_s and frame_idx != plan.frames_per_filter - 1:
                        time.sleep(plan.inter_frame_delay_s)

        stacked_outputs: Dict[int, Optional[str]] = {f.filter_id: None for f in enabled_filters}
        if plan.stack_per_filter:
            for f in enabled_filters:
                inputs = raw_by_filter[f.filter_id]
                if len(inputs) <= 1:
                    continue

                out_label = (
                    f"F{f.filter_id}_{_safe_name(f.name)}_"
                    f"{plan.sequences}seq_{plan.frames_per_filter}f"
                )
                out_path = get_capture_path(
                    kind="stacked",
                    prefix=f"stack_{plan.stack_method}",
                    label=out_label,
                    ext=plan.image_ext,
                )

                stack_frames_mono(inputs, out_path=out_path, method=plan.stack_method)

                # Downscale stacked if requested
                if plan.output_scale == "half":
                    _downscale_half_inplace(out_path)

                stacked_outputs[f.filter_id] = str(out_path)

        return {
            "raw_by_filter": {k: [str(p) for p in v] for k, v in raw_by_filter.items()},
            "stacked_by_filter": stacked_outputs,
            "log": metadata_log,
        }
    finally:
        camera.stop()
        homing_ran = False
        if run_find_start is not None:
            try:
                print("[HW] Re-homing filter wheel with FindStart...")
                run_find_start()
                homing_ran = True
            except Exception as exc:
                print(f"[HW] FindStart failed after sequence: {exc}")

        # Keep LED on through capture + homing; if homing did not run, turn it off here.
        if light_off is not None and not homing_ran:
            try:
                light_off()
                print("[HW] Sequence LED off")
            except Exception as exc:
                print(f"[HW] Failed to switch LED off: {exc}")


def make_auto_plan(
    sequences: int = 1,
    frames_per_filter: int = 1,
    stack_per_filter: bool = True,
    stack_method: StackMethod = "median",
    image_ext: str = "jpg",
    output_scale: OutputScale = "full",
) -> CapturePlan:
    filters = [FilterSpec(i, f"F{i}", ExposureSetting.auto(), enabled=True) for i in range(8)]
    return CapturePlan(
        filters=filters,
        sequences=sequences,
        frames_per_filter=frames_per_filter,
        stack_per_filter=stack_per_filter,
        stack_method=stack_method,
        image_ext=image_ext,
        output_scale=output_scale,
    )


def make_manual_plan(
    selected_filter_ids: List[int],
    sequences: int = 1,
    frames_per_filter: int = 1,
    stack_per_filter: bool = False,
    stack_method: StackMethod = "median",
    image_ext: str = "jpg",
    output_scale: OutputScale = "full",
) -> CapturePlan:
    filters = [
        FilterSpec(i, f"F{i}", ExposureSetting.auto(), enabled=True)
        for i in selected_filter_ids
    ]
    return CapturePlan(
        filters=filters,
        sequences=sequences,
        frames_per_filter=frames_per_filter,
        stack_per_filter=stack_per_filter,
        stack_method=stack_method,
        image_ext=image_ext,
        output_scale=output_scale,
    )
