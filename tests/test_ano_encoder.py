import time
import board
import busio
from adafruit_seesaw import seesaw, rotaryio, digitalio

i2c = busio.I2C(board.SCL, board.SDA)
ss = seesaw.Seesaw(i2c, addr=0x49)

encoder = rotaryio.IncrementalEncoder(ss)
last_position = encoder.position

# Button on pin 6
ss.pin_mode(6, ss.INPUT_PULLUP)
button = digitalio.DigitalIO(ss, 6)
button_state = button.value  # starting level

print("Reading ANO encoder + button...")

try:
    while True:
        # Rotation
        pos = encoder.position
        if pos != last_position:
            print(f"Encoder position: {pos}")
            last_position = pos

        # Button edge detection
        val = button.value  # True/False
        if not val and button_state:
            print("Button pressed")
        if val and not button_state:
            print("Button released")
        button_state = val

        time.sleep(0.01)
except KeyboardInterrupt:
    print("Stopped by user")
