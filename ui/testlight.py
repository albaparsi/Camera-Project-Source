# light_control.py
import RPi.GPIO as GPIO

LED_PIN = 23

def light_on():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, 1)

def light_off():
    GPIO.output(LED_PIN, 0)
    GPIO.cleanup()
