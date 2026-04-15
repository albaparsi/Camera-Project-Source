import time
import board
import busio
import adafruit_tsl2591
import RPi.GPIO as GPIO
import matplotlib.pyplot as plt


# -----------------------
# MOTOR SETUP
# -----------------------
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

# -----------------------
# SENSOR SETUP
# -----------------------
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_tsl2591.TSL2591(i2c)

sensor.gain = adafruit_tsl2591.GAIN_MED
sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS

# -----------------------
# PARAMETERS
# -----------------------
STEPS_PER_REV = 4096
STEP_DELAY = 0.005
SETTLE_EXTRA = 0.002
SAMPLES = 3

print("Running scan...")

try:
    steps = []
    lux_values = []
    seq_len = len(sequence)
    last_valid_lux = 0

    for step_index in range(STEPS_PER_REV):
        # Step motor
        step_pattern = sequence[step_index % seq_len]
        step_once(step_pattern)

        # Let motor + sensor settle
        time.sleep(STEP_DELAY + SETTLE_EXTRA)

        # Read sensor safely
        samples = []
        for _ in range(SAMPLES):
            try:
                lux = sensor.lux
                if lux is not None:
                    samples.append(lux)
            except Exception:
                pass
            time.sleep(0.005)

        # Average or fallback
        if samples:
            avg_lux = sum(samples) / len(samples)
            last_valid_lux = avg_lux
        else:
            avg_lux = last_valid_lux

        steps.append(step_index)
        lux_values.append(avg_lux)

    # -----------------------
    # PLOT RESULTS
    # -----------------------
    plt.figure(figsize=(12, 5))
    plt.plot(steps, lux_values, '.', linestyle='-', color='blue')
    plt.xlabel("Step (0–4095)")
    plt.ylabel("Lux")
    plt.title("Light vs Step Position (Full Rotation)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

finally:
    for p in pins:
        GPIO.output(p, 0)

    GPIO.cleanup()
