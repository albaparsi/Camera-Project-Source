# ui/screens.py
import pygame
import os
import time
from datetime import datetime
from typing import Optional
from pathlib import Path

from imaging.capture_manager import (
    CapturePlan,
    ExposureSetting,
    FilterSpec,
    make_auto_plan,
    make_manual_plan,
    run_capture_plan,
)
from hardware.camera import Camera
import imaging.file_manager as file_manager
from imaging.file_manager import (
    get_capture_path,
    make_new_session_name,
    set_session_subdir,
)
from imaging.image_combiner import combine_filters


IMAGE_FORMAT = "tiff"  # default image format; toggled via Settings screen
OUTPUT_RESOLUTION = "full"  # "full" or "half"; used to set output_scale in plans
CURRENT_SESSION_LABEL = "Default"
START_DELAY_SECONDS = 0  # 0–30 seconds


WIDTH, HEIGHT = 800, 480

HOME_ITEMS = ["Auto", "Manual", "Live view", "Image review", "Settings"]


class HomeScreen:
    def __init__(self, ui_system):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 40)
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(HOME_ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(HOME_ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = HOME_ITEMS[self.selected]
                print(f"Home selected: {choice}")
                if choice == "Auto":
                    # Go to filter selection for Auto flow
                    self.ui.current_screen = FilterSelectScreen(self.ui, next_mode="auto")
                elif choice == "Manual":
                    # Manual flow goes to filter selection first
                    self.ui.current_screen = FilterSelectScreen(self.ui, next_mode="manual")
                elif choice == "Live view":
                    self.ui.current_screen = LiveViewScreen(self.ui)
                elif choice == "Image review":
                    self.ui.current_screen = ImageReviewScreen(self.ui)
                elif choice == "Settings":
                    self.ui.current_screen = SettingsScreen(self.ui)
                # Settings will use the same FilterSelectScreen later

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Camera Home", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 60))
        screen.blit(title, title_rect)

        start_y = 150
        line_h = 50
        for i, label in enumerate(HOME_ITEMS):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class AutoSetupScreen:
    """
    Auto mode setup:
      - sequences: 1..5
      - frames_per_filter: 1..10
      - stacking: on/off
      - uses selected_filter_ids from FilterSelectScreen
    """
    def __init__(self, ui_system, selected_filter_ids):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)

        self.selected_filter_ids = selected_filter_ids

        self.sequences = 1
        self.frames_per_filter = 1
        self.stacking = True
        self.combine = False

        self.fields = ["Sequences", "Frames/filter", "Stacking", "Combine", "Start", "Back"]
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.fields)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.fields)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_current(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_current(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_current()

    def _adjust_current(self, delta: int):
        field = self.fields[self.selected]
        if field == "Sequences":
            self.sequences = max(1, min(5, self.sequences + delta))
        elif field == "Frames/filter":
            self.frames_per_filter = max(1, min(10, self.frames_per_filter + delta))
        elif field == "Stacking":
            if delta != 0:
                self.stacking = not self.stacking
        elif field == "Combine":
            if delta != 0:
                self.combine = not self.combine

    def _activate_current(self):
        field = self.fields[self.selected]
        if field == "Start":
            # Build an auto plan but only enable selected filters
            base_plan = make_auto_plan(
                sequences=self.sequences,
                frames_per_filter=self.frames_per_filter,
                stack_per_filter=self.stacking,
                stack_method="median",
            )

            enabled_ids = set(self.selected_filter_ids)
            filters = []
            for f in base_plan.filters:
                enabled = f.filter_id in enabled_ids
                filters.append(type(f)(
                    filter_id=f.filter_id,
                    name=f.name,
                    exposure=f.exposure,
                    enabled=enabled,
                ))
            plan = type(base_plan)(
                filters=filters,
                sequences=base_plan.sequences,
                frames_per_filter=base_plan.frames_per_filter,
                settle_after_move_s=base_plan.settle_after_move_s,
                inter_frame_delay_s=base_plan.inter_frame_delay_s,
                stack_per_filter=base_plan.stack_per_filter,
                stack_method=base_plan.stack_method,
                image_ext=IMAGE_FORMAT,
                output_scale="half" if OUTPUT_RESOLUTION == "half" else "full",
            )
            print(f"[AUTO PLAN] image_ext={plan.image_ext}, output_scale={plan.output_scale}")

            cam = Camera()
            if START_DELAY_SECONDS > 0:
                print(f"[AUTO] Waiting {START_DELAY_SECONDS}s before start")
                time.sleep(START_DELAY_SECONDS)
            result = run_capture_plan(cam, plan)

            print(f"[DEBUG] combine flag = {self.combine}")
            if self.combine:
                # Optionally: auto-combine stacked outputs into one grayscale
                source = result["stacked_by_filter"] if plan.stack_per_filter else result["raw_by_filter"]

                def _collect_images(mapping):
                    images = {}
                    for fid, value in mapping.items():
                        if not value:
                            continue
                        if isinstance(value, list):
                            img_path = Path(value[-1])
                        else:
                            img_path = Path(value)
                        images[f"F{fid}"] = img_path
                    return images

                filter_images = _collect_images(source)

                if not filter_images:
                    # Fallback to raw frames if stacked outputs missing (e.g., single frame)
                    filter_images = _collect_images(result["raw_by_filter"])

                print(f"[DEBUG] filter_images keys = {list(filter_images.keys())}")
                if filter_images:
                    combined_out = get_capture_path(kind="combined", prefix="auto", ext=IMAGE_FORMAT)
                    combine_filters(
                        filter_images=filter_images,
                        out_path=combined_out,
                        mode="grayscale_mean",
                    )
                    print(f"[AUTO COMBINE] saved {combined_out}")
                else:
                    print("[AUTO COMBINE] No images found to combine")

            print("[AUTO DONE]")
            self.ui.current_screen = HomeScreen(self.ui)
        elif field == "Back":
            # Return to filter selection, preserving current choices
            self.ui.current_screen = FilterSelectScreen(self.ui, next_mode="auto", selected_filter_ids=self.selected_filter_ids)

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Auto Mode Setup", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # Show selected filters summary
        filter_str = ", ".join(f"F{i}" for i in self.selected_filter_ids) or "(none)"
        filters_text = self.font.render(f"Filters: {filter_str}", True, (180, 180, 180))
        filters_rect = filters_text.get_rect(center=(WIDTH // 2, 90))
        screen.blit(filters_text, filters_rect)

        labels = [
            f"Sequences: {self.sequences}",
            f"Frames/filter: {self.frames_per_filter}",
            f"Stacking: {'ON' if self.stacking else 'OFF'}",
            f"Combine: {'ON' if self.combine else 'OFF'}",
            "Start",
            "Back",
        ]

        start_y = 150
        line_h = 45
        for i, label in enumerate(labels):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class LiveViewScreen:
    """Shows a live camera feed from the PiCamera2 preview stream."""

    def __init__(self, ui_system):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 30)
        self.camera = Camera()
        self.preview_surface: Optional[pygame.Surface] = None
        self.status = "Starting camera..."
        self.last_frame_time = 0.0
        self.frame_interval_s = 0.08
        self._started = False

    def _start_camera(self):
        if not self._started:
            try:
                self.camera.start()
                self.status = "Live view active"
            except Exception as exc:
                self.status = f"Camera start failed: {exc}"
            self._started = True

    def _stop_camera(self):
        try:
            self.camera.stop()
        except Exception:
            pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_BACKSPACE):
            self._stop_camera()
            self.ui.current_screen = HomeScreen(self.ui)

    def update(self):
        self._start_camera()
        if self.status != "Live view active":
            return

        now = time.time()
        if now - self.last_frame_time < self.frame_interval_s:
            return

        self.last_frame_time = now
        try:
            frame = self.camera.capture_frame()
            if frame is None:
                self.status = "No frame available"
                return

            # Picamera2 returns RGB frames; pygame wants a (width, height) surface.
            surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.preview_surface = surface
        except Exception as exc:
            self.status = f"Live view error: {exc}"

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Live View", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 28))
        screen.blit(title, title_rect)

        if self.preview_surface is not None:
            max_w = WIDTH - 20
            max_h = HEIGHT - 90
            frame_w, frame_h = self.preview_surface.get_size()
            scale = min(max_w / frame_w, max_h / frame_h, 1.0)
            display_size = (max(1, int(frame_w * scale)), max(1, int(frame_h * scale)))
            image = pygame.transform.smoothscale(self.preview_surface, display_size)
            image_rect = image.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            screen.blit(image, image_rect)
        else:
            message = self.font.render(self.status, True, (180, 180, 180))
            message_rect = message.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(message, message_rect)

        help_text = self.font.render("Esc / Enter / Space / Backspace to return", True, (160, 160, 160))
        help_rect = help_text.get_rect(center=(WIDTH // 2, HEIGHT - 24))
        screen.blit(help_text, help_rect)


class ManualModeScreen:
    """
    Manual mode: choose apply mode (all vs per-filter) and basic plan params.
    For now, only 'all' is implemented; 'per-filter' will be added later.
    """
    def __init__(self, ui_system, selected_filter_ids):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)
        self.selected_filter_ids = selected_filter_ids

        self.apply_mode = "all"  # 'all' or 'per'
        self.sequences = 1
        self.frames_per_filter = 1
        self.stacking = True
        self.combine = False

        self.fields = ["Apply mode", "Sequences", "Frames/filter", "Stacking", "Combine", "Start", "Back"]
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.fields)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.fields)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_current(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_current(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_current()

    def _adjust_current(self, delta: int):
        field = self.fields[self.selected]
        if field == "Apply mode":
            if delta != 0:
                self.apply_mode = "per" if self.apply_mode == "all" else "all"
        elif field == "Sequences":
            self.sequences = max(1, min(5, self.sequences + delta))
        elif field == "Frames/filter":
            self.frames_per_filter = max(1, min(10, self.frames_per_filter + delta))
        elif field == "Stacking":
            if delta != 0:
                self.stacking = not self.stacking
        elif field == "Combine":
            if delta != 0:
                self.combine = not self.combine

    def _activate_current(self):
        field = self.fields[self.selected]
        if field == "Start":
            if self.apply_mode == "all":
                # Go to screen where user sets one ISO / exposure for all filters
                self.ui.current_screen = ManualAllSettingsScreen(
                    self.ui,
                    selected_filter_ids=self.selected_filter_ids,
                    sequences=self.sequences,
                    frames_per_filter=self.frames_per_filter,
                    stacking=self.stacking,
                    combine=self.combine,
                )
            else:
                # Per-filter ISO/exposure editor
                self.ui.current_screen = ManualPerFilterScreen(
                    self.ui,
                    selected_filter_ids=self.selected_filter_ids,
                    sequences=self.sequences,
                    frames_per_filter=self.frames_per_filter,
                    stacking=self.stacking,
                    combine=self.combine,
                )
        elif field == "Back":
            self.ui.current_screen = FilterSelectScreen(self.ui, next_mode="manual", selected_filter_ids=self.selected_filter_ids)

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Manual Mode Setup", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 40))
        screen.blit(title, title_rect)

        filter_str = ", ".join(f"F{i}" for i in self.selected_filter_ids) or "(none)"
        filters_text = self.font.render(f"Filters: {filter_str}", True, (180, 180, 180))
        filters_rect = filters_text.get_rect(center=(WIDTH // 2, 80))
        screen.blit(filters_text, filters_rect)

        apply_label = "All filters" if self.apply_mode == "all" else "Per-filter"

        labels = [
            f"Apply mode: {apply_label}",
            f"Sequences: {self.sequences}",
            f"Frames/filter: {self.frames_per_filter}",
            f"Stacking: {'ON' if self.stacking else 'OFF'}",
            f"Combine: {'ON' if self.combine else 'OFF'}",
            "Start",
            "Back",
        ]

        start_y = 130
        line_h = 40
        for i, label in enumerate(labels):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class ManualAllSettingsScreen:
    """
    Manual mode (apply to all): choose one ISO + exposure_ms for all selected filters,
    then build and run a manual CapturePlan.
    """
    def __init__(self, ui_system, selected_filter_ids, sequences, frames_per_filter, stacking, combine):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)

        self.selected_filter_ids = selected_filter_ids
        self.sequences = sequences
        self.frames_per_filter = frames_per_filter
        self.stacking = stacking
        self.combine = combine

        # Initial ISO/exposure defaults
        self.iso = 400           # 100–6400 step 100
        self.exposure_ms = 1000  # 10–10000 step 10

        self.fields = ["ISO", "Exposure", "Start", "Back"]
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.fields)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.fields)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_current(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_current(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_current()

    def _adjust_current(self, delta: int):
        field = self.fields[self.selected]
        if field == "ISO":
            # 100–6400 step 100
            self.iso = max(100, min(6400, self.iso + delta * 100))
        elif field == "Exposure":
            # 10–10000 ms step 10
            self.exposure_ms = max(10, min(10000, self.exposure_ms + delta * 10))

    def _activate_current(self):
        field = self.fields[self.selected]
        if field == "Start":
            print(
                f"[MANUAL ALL] filters={self.selected_filter_ids}, "
                f"seq={self.sequences}, frames/filter={self.frames_per_filter}, "
                f"stacking={self.stacking}, combine={self.combine}, "
                f"iso={self.iso}, exposure_ms={self.exposure_ms}"
            )

            total_frames = self.sequences * self.frames_per_filter
            should_stack = self.stacking and total_frames > 1
            if self.stacking and not should_stack:
                print("[MANUAL ALL] Stacking requested but only one frame available; skipping stack")

            # Build plan with manual exposure
            filters_specs = []
            for fid in self.selected_filter_ids:
                filters_specs.append(
                    FilterSpec(
                        filter_id=fid,
                        name=f"F{fid}",
                        exposure=ExposureSetting.manual(self.iso, float(self.exposure_ms)),
                        enabled=True,
                    )
                )
            plan = CapturePlan(
                filters=filters_specs,
                sequences=self.sequences,
                frames_per_filter=self.frames_per_filter,
                stack_per_filter=should_stack,
                stack_method="median",
                image_ext=IMAGE_FORMAT,
                output_scale="half" if OUTPUT_RESOLUTION == "half" else "full",
            )
            print(f"[MANUAL PER PLAN] image_ext={plan.image_ext}, output_scale={plan.output_scale}")
            print(f"[MANUAL ALL PLAN] image_ext={plan.image_ext}, output_scale={plan.output_scale}")

            cam = Camera()
            if START_DELAY_SECONDS > 0:
                print(f"[MANUAL ALL] Waiting {START_DELAY_SECONDS}s before start")
                time.sleep(START_DELAY_SECONDS)
            result = run_capture_plan(cam, plan)

            if plan.stack_per_filter:
                print(f"[MANUAL ALL] Stacked outputs: {result['stacked_by_filter']}")

            if self.combine:
                # Prefer stacked outputs when available; always fall back to raw frames if missing
                source = result["stacked_by_filter"] if plan.stack_per_filter else result["raw_by_filter"]

                def _collect_images(mapping):
                    images = {}
                    for fid, value in mapping.items():
                        if not value:
                            continue
                        if isinstance(value, list):
                            img_path = Path(value[-1])
                        else:
                            img_path = Path(value)
                        images[f"F{fid}"] = img_path
                    return images

                filter_images = _collect_images(source)

                if not filter_images:
                    # Fallback to raw frames regardless of stack flag
                    filter_images = _collect_images(result["raw_by_filter"])

                if filter_images:
                    combined_out = get_capture_path(kind="combined", prefix="manual", ext=IMAGE_FORMAT)
                    combine_filters(
                        filter_images=filter_images,
                        out_path=combined_out,
                        mode="grayscale_mean",
                    )
                    print(f"[MANUAL COMBINE] saved {combined_out}")
                else:
                    print("[MANUAL COMBINE] No images found to combine")

            print("[MANUAL ALL DONE]")
            self.ui.current_screen = HomeScreen(self.ui)

        elif field == "Back":
            # Go back to ManualModeScreen with same selections
            self.ui.current_screen = ManualModeScreen(
                self.ui,
                selected_filter_ids=self.selected_filter_ids,
            )

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Manual: All Filters", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 40))
        screen.blit(title, title_rect)

        filter_str = ", ".join(f"F{i}" for i in self.selected_filter_ids) or "(none)"
        filters_text = self.font.render(f"Filters: {filter_str}", True, (180, 180, 180))
        filters_rect = filters_text.get_rect(center=(WIDTH // 2, 80))
        screen.blit(filters_text, filters_rect)

        labels = [
            f"ISO: {self.iso}",
            f"Exposure: {self.exposure_ms} ms",
            "Start",
            "Back",
        ]

        start_y = 130
        line_h = 45
        for i, label in enumerate(labels):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class ManualPerFilterScreen:
    """
    Manual mode: per-filter ISO + exposure_ms.
    Shows one selected filter at a time.
    """
    def __init__(self, ui_system, selected_filter_ids, sequences, frames_per_filter, stacking, combine):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)

        self.selected_filter_ids = list(selected_filter_ids)
        self.sequences = sequences
        self.frames_per_filter = frames_per_filter
        self.stacking = stacking
        self.combine = combine

        # Per-filter settings
        self.per_filter: dict[int, dict[str, int]] = {}
        for fid in self.selected_filter_ids:
            self.per_filter[fid] = {"iso": 400, "exposure_ms": 1000}

        self.current_filter_index = 0  # index into selected_filter_ids

        # Fields: ISO, Exposure, Next filter, Start, Back
        self.fields = ["ISO", "Exposure", "Next filter", "Start", "Back"]
        self.selected = 0

    @property
    def current_filter_id(self) -> int:
        return self.selected_filter_ids[self.current_filter_index]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.fields)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.fields)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_current(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_current(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_current()

    def _adjust_current(self, delta: int):
        field = self.fields[self.selected]
        fid = self.current_filter_id
        if field == "ISO":
            iso = self.per_filter[fid]["iso"]
            iso = max(100, min(6400, iso + delta * 100))
            self.per_filter[fid]["iso"] = iso
        elif field == "Exposure":
            exp = self.per_filter[fid]["exposure_ms"]
            exp = max(10, min(10000, exp + delta * 10))
            self.per_filter[fid]["exposure_ms"] = exp
        elif field == "Next filter":
            if delta != 0:
                n = len(self.selected_filter_ids)
                self.current_filter_index = (self.current_filter_index + delta) % n

    def _activate_current(self):
        field = self.fields[self.selected]
        if field == "Next filter":
            n = len(self.selected_filter_ids)
            self.current_filter_index = (self.current_filter_index + 1) % n
        elif field == "Start":
            print("[MANUAL PER] starting capture")

            total_frames = self.sequences * self.frames_per_filter
            should_stack = self.stacking and total_frames > 1
            if self.stacking and not should_stack:
                print("[MANUAL PER] Stacking requested but only one frame available; skipping stack")

            filters_specs = []
            for fid in self.selected_filter_ids:
                s = self.per_filter[fid]
                filters_specs.append(
                    FilterSpec(
                        filter_id=fid,
                        name=f"F{fid}",
                        exposure=ExposureSetting.manual(s["iso"], float(s["exposure_ms"])),
                        enabled=True,
                    )
                )
            plan = CapturePlan(
                filters=filters_specs,
                sequences=self.sequences,
                frames_per_filter=self.frames_per_filter,
                stack_per_filter=should_stack,
                stack_method="median",
                image_ext=IMAGE_FORMAT,
                output_scale="half" if OUTPUT_RESOLUTION == "half" else "full",
            )

            cam = Camera()
            if START_DELAY_SECONDS > 0:
                print(f"[MANUAL PER] Waiting {START_DELAY_SECONDS}s before start")
                time.sleep(START_DELAY_SECONDS)
            result = run_capture_plan(cam, plan)

            if plan.stack_per_filter:
                print(f"[MANUAL PER] Stacked outputs: {result['stacked_by_filter']}")

            if self.combine:
                source = result["stacked_by_filter"] if plan.stack_per_filter else result["raw_by_filter"]

                def _collect_images(mapping):
                    images = {}
                    for fid, value in mapping.items():
                        if not value:
                            continue
                        if isinstance(value, list):
                            img_path = Path(value[-1])
                        else:
                            img_path = Path(value)
                        images[f"F{fid}"] = img_path
                    return images

                filter_images = _collect_images(source)

                if not filter_images:
                    filter_images = _collect_images(result["raw_by_filter"])

                if filter_images:
                    combined_out = get_capture_path(kind="combined", prefix="manual_per", ext=IMAGE_FORMAT)
                    combine_filters(
                        filter_images=filter_images,
                        out_path=combined_out,
                        mode="grayscale_mean",
                    )
                    print(f"[MANUAL PER COMBINE] saved {combined_out}")
                else:
                    print("[MANUAL PER COMBINE] No images found to combine")

            print("[MANUAL PER DONE]")
            self.ui.current_screen = HomeScreen(self.ui)

        elif field == "Back":
            # Return to ManualModeScreen, preserving filter selection
            self.ui.current_screen = ManualModeScreen(
                self.ui,
                selected_filter_ids=self.selected_filter_ids,
            )

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        fid = self.current_filter_id
        s = self.per_filter[fid]

        title = self.font.render("Manual: Per Filter", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 40))
        screen.blit(title, title_rect)

        sub = self.font.render(f"Filter: F{fid}", True, (180, 180, 180))
        sub_rect = sub.get_rect(center=(WIDTH // 2, 80))
        screen.blit(sub, sub_rect)

        labels = [
            f"ISO: {s['iso']}",
            f"Exposure: {s['exposure_ms']} ms",
            "Next filter",
            "Start",
            "Back",
        ]

        start_y = 130
        line_h = 45
        for i, label in enumerate(labels):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class SettingsScreen:
    """
        Settings:
            - Image format: JPG / TIFF
            - Output resolution: Full / Half
            - Capture folder: Default / Session_xxx (toggle)
            - Start delay: 0–30 seconds
            - New session
            - Back
    """
    def __init__(self, ui_system):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)
        self.fields = ["Image format", "Output resolution", "Capture folder", "Start delay", "New session", "Back"]
        self.selected = 0

    def handle_event(self, event):
        global IMAGE_FORMAT, OUTPUT_RESOLUTION, CURRENT_SESSION_LABEL, START_DELAY_SECONDS
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.fields)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.fields)
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                delta = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                self._adjust_current(delta)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_current()

    def _adjust_current(self, delta: int):
        global IMAGE_FORMAT, OUTPUT_RESOLUTION, CURRENT_SESSION_LABEL, START_DELAY_SECONDS
        field = self.fields[self.selected]
        if field == "Image format":
            IMAGE_FORMAT = "tiff" if IMAGE_FORMAT == "jpg" else "jpg"
            print(f"[SETTINGS] IMAGE_FORMAT = {IMAGE_FORMAT}")
        elif field == "Output resolution":
            OUTPUT_RESOLUTION = "half" if OUTPUT_RESOLUTION == "full" else "full"
            print(f"[SETTINGS] OUTPUT_RESOLUTION = {OUTPUT_RESOLUTION}")
        elif field == "Capture folder":
            if CURRENT_SESSION_LABEL == "Default":
                session_name = make_new_session_name()
                set_session_subdir(session_name)
                CURRENT_SESSION_LABEL = session_name
                print(f"[SETTINGS] Capture folder = {session_name}")
            else:
                CURRENT_SESSION_LABEL = "Default"
                set_session_subdir(None)
                print("[SETTINGS] Capture folder = Default")
        elif field == "Start delay":
            if delta != 0:
                START_DELAY_SECONDS = max(0, min(30, START_DELAY_SECONDS + delta))
                print(f"[SETTINGS] START_DELAY_SECONDS = {START_DELAY_SECONDS}")
        elif field == "New session":
            # New session is triggered on Enter; ignore left/right
            pass

    def _activate_current(self):
        global CURRENT_SESSION_LABEL
        field = self.fields[self.selected]
        if field == "New session":
            session_name = make_new_session_name()
            set_session_subdir(session_name)
            CURRENT_SESSION_LABEL = session_name
            print(f"[SETTINGS] New session created: {session_name}")
        elif field == "Back":
            self.ui.current_screen = HomeScreen(self.ui)

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Settings", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 60))
        screen.blit(title, title_rect)

        fmt_label = "TIFF" if IMAGE_FORMAT == "tiff" else "JPG"
        res_label = "Half" if OUTPUT_RESOLUTION == "half" else "Full"
        folder_label = CURRENT_SESSION_LABEL
        delay_label = f"{START_DELAY_SECONDS}s"

        labels = [
            f"Image format: {fmt_label}",
            f"Output resolution: {res_label}",
            f"Capture folder: {folder_label}",
            f"Start delay: {delay_label}",
            "New session",
            "Back",
        ]

        start_y = 140
        line_h = 40
        for i, label in enumerate(labels):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)


class ImageReviewScreen:
    """
    Image review for active session:
      - Choose Raw / Stacked / Combined (enter to load)
      - Prev / Next / Delete / Back
    """
    def __init__(self, ui_system):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 28)

        self.menu_items = ["Raw", "Stacked", "Combined", "Prev", "Next", "Delete", "Back"]
        self.selected = 0
        self.current_view: Optional[str] = None  # "raw"/"stacked"/"combined"

        self.images: list[Path] = []
        self.current_index = 0
        self.current_surface: Optional[pygame.Surface] = None
        self.current_meta: str = "Select a folder: Raw / Stacked / Combined"

    def _session_base_dir(self) -> Path:
        return file_manager.BASE_DIR / file_manager.CURRENT_SESSION_SUBDIR if file_manager.CURRENT_SESSION_SUBDIR else file_manager.BASE_DIR

    def _folder_for_view_mode(self, view: str) -> Path:
        return self._session_base_dir() / view

    def _reload_file_list(self):
        if not self.current_view:
            return
        folder = self._folder_for_view_mode(self.current_view)
        if not folder.exists():
            self.images = []
            self.current_index = 0
            self.current_surface = None
            self.current_meta = "No images"
            return

        files = []
        for name in os.listdir(folder):
            p = folder / name
            if p.is_file() and name.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff", ".png")):
                files.append(p)

        files.sort()
        self.images = files
        if not self.images:
            self.current_index = 0
            self.current_surface = None
            self.current_meta = "No images"
        else:
            self.current_index = min(self.current_index, len(self.images) - 1)
            self._load_current_image()

    def _load_current_image(self):
        if not self.current_view:
            self.current_surface = None
            self.current_meta = "Select a folder: Raw / Stacked / Combined"
            return
        if not self.images:
            self.current_surface = None
            self.current_meta = "No images"
            return

        path = self.images[self.current_index]
        try:
            img = pygame.image.load(str(path))
            max_w = WIDTH - 40
            max_h = HEIGHT - 160
            w, h = img.get_size()
            scale = min(max_w / w, max_h / h, 1.0)
            new_size = (int(w * scale), int(h * scale))
            img = pygame.transform.smoothscale(img, new_size)
            self.current_surface = img

            stat = path.stat()
            dt = datetime.fromtimestamp(stat.st_mtime)
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.current_meta = f"{path.name}  |  {dt_str}"
        except Exception as e:
            print(f"[REVIEW] failed to load {path}: {e}")
            self.current_surface = None
            self.current_meta = f"Failed to load: {path.name}"

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.menu_items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.menu_items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()

    def _activate(self):
        item = self.menu_items[self.selected]
        if item in ("Raw", "Stacked", "Combined"):
            self.current_view = item.lower()
            self.current_index = 0
            self._reload_file_list()
            self._load_current_image()
            return

        if item == "Prev" and self.images:
            self.current_index = (self.current_index - 1) % len(self.images)
            self._load_current_image()
        elif item == "Next" and self.images:
            self.current_index = (self.current_index + 1) % len(self.images)
            self._load_current_image()
        elif item == "Delete" and self.images:
            path = self.images[self.current_index]
            try:
                os.remove(path)
                print(f"[REVIEW] deleted {path}")
            except Exception as e:
                print(f"[REVIEW] failed to delete {path}: {e}")
            self._reload_file_list()
        elif item == "Back":
            self.ui.current_screen = HomeScreen(self.ui)

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Image Review", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 24))
        screen.blit(title, title_rect)

        session_text = file_manager.CURRENT_SESSION_SUBDIR if file_manager.CURRENT_SESSION_SUBDIR else "Default"
        session_surf = self.font.render(f"Session: {session_text}", True, (160, 160, 160))
        session_rect = session_surf.get_rect(center=(WIDTH // 2, 44))
        screen.blit(session_surf, session_rect)

        # Menu list (left column)
        start_y = 70
        line_h = 34
        for i, label in enumerate(self.menu_items):
            color = (255, 255, 0) if i == self.selected else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(topleft=(20, start_y + i * line_h))
            screen.blit(text, rect)

        # Image / status area
        area_left = 180
        area_width = WIDTH - area_left - 20
        area_center_x = area_left + area_width // 2
        area_center_y = HEIGHT // 2

        if self.current_surface is not None:
            img_rect = self.current_surface.get_rect(center=(area_center_x, area_center_y))
            screen.blit(self.current_surface, img_rect)
        else:
            msg = self.font.render(self.current_meta, True, (180, 180, 180))
            msg_rect = msg.get_rect(center=(area_center_x, area_center_y))
            screen.blit(msg, msg_rect)

        meta_surf = self.font.render(self.current_meta, True, (180, 180, 180))
        meta_rect = meta_surf.get_rect(center=(area_center_x, HEIGHT - 30))
        screen.blit(meta_surf, meta_rect)


class FilterSelectScreen:
    """
    Compact filter selection screen:
      - F0..F7 on 8 lines
      - Bottom line: Back / Continue
      - No scrolling required
    """
    def __init__(self, ui_system, next_mode: str, selected_filter_ids: Optional[list[int]] = None):
        self.ui = ui_system
        self.font = pygame.font.SysFont(None, 32)
        self.next_mode = next_mode  # 'auto' or 'manual' later

        # 8 filters, all enabled by default; override with provided selection
        if selected_filter_ids is None:
            self.enabled = [True] * 8
        else:
            selected = set(selected_filter_ids)
            self.enabled = [i in selected for i in range(8)]

        # index 0..7 = filters, index 8 = bottom Back/Continue line
        self.selected_row = 0
        self.bottom_choice = 1  # 0 = Back, 1 = Continue (default to Continue)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_row = (self.selected_row - 1) % 9
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_row = (self.selected_row + 1) % 9
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._left_right(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._left_right(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()

    def _left_right(self, delta: int):
        if self.selected_row <= 7:
            # toggle current filter
            idx = self.selected_row
            self.enabled[idx] = not self.enabled[idx]
        else:
            # bottom row: switch Back / Continue
            self.bottom_choice = 1 - self.bottom_choice

    def _activate(self):
        if self.selected_row <= 7:
            # toggle filter
            idx = self.selected_row
            self.enabled[idx] = not self.enabled[idx]
        else:
            # bottom line
            if self.bottom_choice == 0:
                # Back
                self.ui.current_screen = HomeScreen(self.ui)
            else:
                # Continue
                selected_ids = [i for i, en in enumerate(self.enabled) if en]
                if not selected_ids:
                    print("[FILTER SELECT] No filters selected, ignoring Continue")
                    return
                print(f"[FILTER SELECT] Next mode={self.next_mode}, filters={selected_ids}")
                if self.next_mode == "auto":
                    self.ui.current_screen = AutoSetupScreen(self.ui, selected_filter_ids=selected_ids)
                elif self.next_mode == "manual":
                    self.ui.current_screen = ManualModeScreen(self.ui, selected_filter_ids=selected_ids)
                else:
                    self.ui.current_screen = HomeScreen(self.ui)

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((0, 0, 0))

        title = self.font.render("Select Filters", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 40))
        screen.blit(title, title_rect)

        start_y = 90
        line_h = 38

        # F0..F7 rows
        for i in range(8):
            checked = "[X]" if self.enabled[i] else "[ ]"
            label = f"{checked} F{i}"
            color = (255, 255, 0) if self.selected_row == i else (180, 180, 180)
            text = self.font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)

        # Bottom Back / Continue row
        bottom_y = start_y + 8 * line_h + 12
        back_color = (255, 255, 0) if self.selected_row == 8 and self.bottom_choice == 0 else (180, 180, 180)
        cont_color = (255, 255, 0) if self.selected_row == 8 and self.bottom_choice == 1 else (180, 180, 180)

        back_text = self.font.render("Back", True, back_color)
        cont_text = self.font.render("Continue", True, cont_color)

        spacing = 80
        back_rect = back_text.get_rect(center=(WIDTH // 2 - spacing, bottom_y))
        cont_rect = cont_text.get_rect(center=(WIDTH // 2 + spacing, bottom_y))

        screen.blit(back_text, back_rect)
        screen.blit(cont_text, cont_rect)
