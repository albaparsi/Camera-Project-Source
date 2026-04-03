"""Helpers for moving the stepper motor by raw steps or filter positions."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Optional

import RPi.GPIO as GPIO  # type: ignore[import-not-found]

from .motor_driver import PINS, SEQUENCE, STEP_DELAY, STEPS_PER_REV


POSITIONS_PER_REV = 9
STEPS_PER_POSITION = STEPS_PER_REV // POSITIONS_PER_REV

# Backward-compatible aliases used by older imports.
FILTERS_PER_REV = POSITIONS_PER_REV
STEPS_PER_FILTER = STEPS_PER_POSITION


def setup_motor(pins: Sequence[int] = PINS) -> None:
	"""Initialize the GPIO pins used by the stepper motor."""

	GPIO.setmode(GPIO.BCM)
	for pin in pins:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, 0)


def cleanup_motor() -> None:
	"""Release all GPIO resources used by the motor."""

	GPIO.cleanup()


def _step_once(step_pattern: Sequence[int], pins: Sequence[int] = PINS) -> None:
	for pin, value in zip(pins, step_pattern):
		GPIO.output(pin, bool(value))


def move_steps(
	step_count: int,
	*,
	pins: Sequence[int] = PINS,
	sequence: Sequence[Sequence[int]] = SEQUENCE,
	step_delay: float = STEP_DELAY,
	setup_gpio: bool = True,
	cleanup_gpio: bool = True,
) -> None:
	"""Move the motor a fixed number of microsteps."""

	if step_count < 0:
		raise ValueError("step_count must be >= 0")

	if setup_gpio:
		setup_motor(pins)

	try:
		for step_index in range(step_count):
			_step_once(sequence[step_index % len(sequence)], pins)
			time.sleep(step_delay)
	finally:
		if cleanup_gpio:
			cleanup_motor()


def move_filters(
	filter_count: int,
	*,
	pins: Sequence[int] = PINS,
	sequence: Sequence[Sequence[int]] = SEQUENCE,
	step_delay: float = STEP_DELAY,
	steps_per_filter: int = STEPS_PER_POSITION,
	on_filter_step: Optional[Callable[[int], None]] = None,
	setup_gpio: bool = True,
	cleanup_gpio: bool = True,
) -> None:
	"""Move the wheel by a number of wheel positions.

	The default wheel layout assumes nine positions per full revolution
	(8 filters + 1 empty reference position).

	If ``on_filter_step`` is provided, it is called after each filter move with
	the 1-based filter step number.
	"""

	if filter_count < 0:
		raise ValueError("filter_count must be >= 0")

	if steps_per_filter <= 0:
		raise ValueError("steps_per_filter must be > 0")

	if setup_gpio:
		setup_motor(pins)

	try:
		for filter_index in range(filter_count):
			move_steps(
				steps_per_filter,
				pins=pins,
				sequence=sequence,
				step_delay=step_delay,
				setup_gpio=False,
				cleanup_gpio=False,
			)

			if on_filter_step is not None:
				on_filter_step(filter_index + 1)
	finally:
		if cleanup_gpio:
			cleanup_motor()
