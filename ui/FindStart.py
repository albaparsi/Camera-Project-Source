# FindStart.py
import time
import board
import busio
import adafruit_tsl2591
import RPi.GPIO as GPIO
from ui import testlight  # your light module
def run_find_start():
	print("FindStart logic running...")
    # Put whatever initialization/startup code you need here


	# ----------------------- LIGHT SETUP -----------------------
	testlight.light_on()  # turn on light at start

	# ----------------------- MOTOR SETUP -----------------------
	pins = [17, 18, 27, 22]
	GPIO.setmode(GPIO.BCM)
	for p in pins:
		GPIO.setup(p, GPIO.OUT)
		GPIO.output(p, 0)

	sequence = [
		[1, 0, 0, 0],
		[1, 1, 0, 0],
		[0, 1, 0, 0],
		[0, 1, 1, 0],
		[0, 0, 1, 0],
		[0, 0, 1, 1],
		[0, 0, 0, 1],
		[1, 0, 0, 1],
	]

	def step_once(step_pattern):
		for pin, val in zip(pins, step_pattern):
			GPIO.output(pin, val)

	# ----------------------- SENSOR SETUP -----------------------
	i2c = busio.I2C(board.SCL, board.SDA)
	sensor = adafruit_tsl2591.TSL2591(i2c)
	sensor.gain = adafruit_tsl2591.GAIN_MED
	sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

	# ----------------------- PARAMETERS -----------------------
	STEPS_PER_REV = 4096
	RPM = 10
	STEP_DELAY = 60 / (STEPS_PER_REV * RPM)

	LIGHT_THRESHOLD = 2
	MIN_INTERVAL_FOR_BASELINE = 0.005  # ignore very short intervals
	BASELINE_CROSSES = 3
	STOP_FACTOR = 0.7
	OVERSHOOT_FACTOR = 1.3
	MAX_BACKTRACK = 500  # safety limit

	print(f"Starting scan at {RPM} RPM (step delay = {STEP_DELAY:.6f}s)")

	# ----------------------- MAIN LOOP -----------------------
	try:
		step_index = 0
		last_state = False
		timestamps = []
		valid_intervals = []  # intervals used for baseline
		previous_interval = None

		while step_index < STEPS_PER_REV:
			# Step motor
			step_pattern = sequence[step_index % len(sequence)]
			step_once(step_pattern)
			time.sleep(STEP_DELAY)

			# Read sensor
			try:
				lux = sensor.lux
				avg_lux = lux if lux is not None else 0.0
			except Exception:
				avg_lux = 0.0

			current_state = avg_lux >= LIGHT_THRESHOLD

			if current_state and not last_state:
				timestamp = time.time()
				print(f"Rising edge detected at step {step_index}, lux={avg_lux:.1f}")

				if timestamps:
					interval = timestamp - timestamps[-1]
					print(f"Measured interval: {interval:.6f}s")

					# Collect intervals above minimum threshold
					if interval >= MIN_INTERVAL_FOR_BASELINE:
						valid_intervals.append(interval)
						print(f"Added to baseline samples ({len(valid_intervals)} total)")
					else:
						print(f"Ignored interval below baseline minimum ({MIN_INTERVAL_FOR_BASELINE:.6f}s)")

					# Safe baseline calculation
					num_intervals_for_baseline = min(BASELINE_CROSSES, len(valid_intervals))
					if num_intervals_for_baseline > 0:
						baseline = sum(valid_intervals[-num_intervals_for_baseline:]) / num_intervals_for_baseline
						print(f"Baseline from last {num_intervals_for_baseline} samples: {baseline:.6f}s")
					else:
						baseline = interval  # fallback if no valid interval yet
						print(f"Baseline fallback to current interval: {baseline:.6f}s")

					print(f"Step {step_index}, Lux={avg_lux:.1f}, Interval={interval:.6f}s, Baseline={baseline:.6f}s")

					# SHORT INTERVAL STOP - detects short-distance pinhole
					if interval < STOP_FACTOR * baseline:
						print(f"Short distance pinhole detected at step {step_index}. Stopping.")
						break

					# OVERSHOOT DETECTION
					if previous_interval and interval > previous_interval * OVERSHOOT_FACTOR:
						print("Overshoot detected, backtracking...")
						back_steps = 0
						back_last_state = False
						back_last_time = None

						while back_steps < MAX_BACKTRACK:
							step_index -= 1
							step_pattern = sequence[step_index % len(sequence)]
							step_once(step_pattern)
							time.sleep(STEP_DELAY)

							try:
								lux = sensor.lux
								avg_lux = lux if lux is not None else 0.0
							except Exception:
								avg_lux = 0.0

							back_state = avg_lux >= LIGHT_THRESHOLD

							# Stop at first rising edge with interval shorter than baseline
							if back_state and not back_last_state:
								t = time.time()
								if back_last_time is not None:
									back_interval = t - back_last_time
									if back_interval < baseline:
										print(f"Correct short pinhole found at step {step_index}")
										break
								back_last_time = t

							back_last_state = back_state
							back_steps += 1

						break  # exit main loop after backtracking

					previous_interval = interval
					print(f"Previous interval updated to {previous_interval:.6f}s")

				timestamps.append(timestamp)
				print(f"Timestamp count is now {len(timestamps)}")

			last_state = current_state
			step_index += 1

		print("\nDetected timestamps:")
		for i, t in enumerate(timestamps):
			print(f"{i}: {t:.6f}s")

	finally:
		for p in pins:
			GPIO.output(p, 0)
		testlight.light_off()
		GPIO.cleanup()
		print("Motor stopped and light off.")
