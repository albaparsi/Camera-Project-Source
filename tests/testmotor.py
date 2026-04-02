# testmotor.py
import RPi.GPIO as GPIO
import time

pins = [17, 18, 27, 22]  # IN1--IN4

GPIO.setmode(GPIO.BCM)
for p in pins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, 0)

sequence = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1],
]

try:
    while True:
        for step in sequence:
            for pin, val in zip(pins, step):
                GPIO.output(pin, val)
            time.sleep(0.01)
finally:
    GPIO.cleanup()
