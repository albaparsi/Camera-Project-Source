"""Light-triggered motor control using TSL2591 readings."""

import sys
import time
import subprocess
from pathlib import Path

import board
import busio
import adafruit_tsl2591


LIGHT_THRESHOLD = 1000
CHECK_INTERVAL = 0.05
MOTOR_SCRIPT = Path(__file__).resolve().parent / "motor_driver.py"


def start_motor(script_path: Path) -> subprocess.Popen:
	"""Launch the motor runner script using the current Python interpreter."""

	return subprocess.Popen([sys.executable, str(script_path)])


def stop_motor(proc: subprocess.Popen | None) -> None:
	"""Terminate the motor process if it is running."""

	if proc is None:
		return

	if proc.poll() is None:
		proc.terminate()
		try:
			proc.wait(timeout=2)
		except subprocess.TimeoutExpired:
			proc.kill()


def monitor_light(threshold: float = LIGHT_THRESHOLD, interval: float = CHECK_INTERVAL) -> None:
	"""Start/stop the motor script based on light level crossings."""

	i2c = busio.I2C(board.SCL, board.SDA)
	sensor = adafruit_tsl2591.TSL2591(i2c)

	action_process: subprocess.Popen | None = None
	previous_state = False
	light_count = 0

	print("Monitoring light levels...")

	try:
		while True:
			lux = sensor.lux
			if lux is None:
				time.sleep(interval)
				continue

			current_state = lux >= threshold
			if current_state and not previous_state:
				light_count += 1
				print(f"Light detected ({lux:.2f} lux), count={light_count}")
			elif not current_state and previous_state:
				print(f"Light fell below threshold ({lux:.2f} lux)")

			if not current_state and action_process is None:
				action_process = start_motor(MOTOR_SCRIPT)
				print("Motor started")
			elif current_state and action_process is not None:
				stop_motor(action_process)
				action_process = None
				print("Motor stopped")

			previous_state = current_state
			time.sleep(interval)
	except KeyboardInterrupt:
		print("Stopped by user")
	finally:
		stop_motor(action_process)


def main() -> None:
	monitor_light()


if __name__ == "__main__":
	main()
