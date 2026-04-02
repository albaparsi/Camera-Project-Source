pip install adafruit-blinka adafruit-circuitpython-tsl2591 adafruit-circuitpython-seesaw
sudo apt install -y python3-libcamera python3-picamera2 libcamera-dev
python - <<'PY'\nimport libcamera, picamera2\nimport pygame, PIL, board\nprint("imports OK")\nPY

i2cdetect -y 1