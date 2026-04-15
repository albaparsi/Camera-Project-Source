import RPi.GPIO as GPIO
import time

# Pins (IN1–IN4)
pins = [17, 18, 27, 22]

GPIO.setmode(GPIO.BCM)
for p in pins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, 0)

# Half-step sequence (8 steps per cycle)
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

def step_motor(steps, delay=0.001, direction=1):
    """
    steps: number of steps to move
    delay: time between steps (seconds)
    direction: 1 for forward, -1 for reverse
    """
    seq = sequence if direction == 1 else sequence[::-1]

    for i in range(steps):
        for step in seq:
            for pin, val in zip(pins, step):
                GPIO.output(pin, val)
            time.sleep(delay)

try:
    # === TEST PARAMETERS ===
    steps_per_rev = 4096   # adjust for your motor (common: 512 or 2048)
    num_revolutions = 1   # change this for testing

    total_steps = steps_per_rev * num_revolutions

    print(f"Running {total_steps} steps...")

    step_motor(total_steps, delay=0.001, direction=1)

    print("Done.")

finally:
    GPIO.cleanup()
