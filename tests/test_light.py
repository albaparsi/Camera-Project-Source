import time
import board
import busio
import adafruit_tsl2591

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_tsl2591.TSL2591(i2c)

print("Reading TSL2591 lux values... (Ctrl+C to stop)")
try:
    while True:
        lux = sensor.lux
        if lux is not None:
            print(f"Lux: {lux:.2f}")
        else:
            print("Lux: None")
        time.sleep(0.2)
except KeyboardInterrupt:
    print("Stopped by user")
