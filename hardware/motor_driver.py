"""Basic stepper motor runner using RPi.GPIO."""

import time

import RPi.GPIO as GPIO

# IN1--IN4 pin numbers
PINS = [17, 18, 27, 22]

SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]

STEP_DELAY = 0.01


def setup() -> None:
    GPIO.setmode(GPIO.BCM)
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)


def run() -> None:
    """Spin the motor continuously until interrupted."""

    setup()
    try:
        while True:
            for step in SEQUENCE:
                for pin, val in zip(PINS, step):
                    GPIO.output(pin, val)
                time.sleep(STEP_DELAY)
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    run()
