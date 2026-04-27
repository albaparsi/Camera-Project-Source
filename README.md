# Kromico

Kromico is an integrated multispectral camera designed to capture high-quality images across multiple wavelengths without relying on bulky external hardware, loose cabling, or a separate laptop during normal use.

The project was developed to make multispectral imaging more compact, practical, and easier to use outside of traditional lab-style setups.

## Overview

Traditional multispectral imaging systems can be large, expensive, and inconvenient to deploy. Kromico addresses this by combining embedded control, filter switching, and on-device interaction into a single self-contained platform.

The software runs on a Raspberry Pi and uses a Pygame-based graphical interface, with `menu_system.py` serving as the main application entry point. The device also uses an attached display so the system can be operated directly on the camera itself.

## Features

- Integrated multispectral imaging workflow for high-quality multi-wavelength capture.
- High-resolution monochrome sensor for collecting image data across different light bands.
- Motorized filter wheel for switching between filters and capturing both visible and non-visible light.
- Raspberry Pi-based embedded control system with a local display.
- Windowed GUI built with Pygame for on-device control and navigation.
- Python virtual environment setup for running the software.
- Support for launching automatically on boot with `systemd`.

## Applications

Kromico was designed to make multispectral imaging more accessible in a compact form factor. By integrating sensing, control, and interaction into one device, the system reduces the need for larger and more complicated external setups.

Potential application areas include astronomy, environmental monitoring, materials science, and forensic imaging.

## Hardware

The imaging system uses a high-resolution monochrome sensor paired with a motorized filter wheel. This design allows the camera to switch filters mechanically and capture wavelength-specific image information within one integrated system.

The control platform runs on a Raspberry Pi with a physical display attached directly to the device for local interaction.

## Software

The main interface is written in Python using Pygame, and `menu_system.py` is the primary file that launches the application. The project is run inside a Python virtual environment using:

```bash
source .venv/bin/activate
python menu_system.py
```

The system can also be configured to launch automatically at boot using a `systemd` service.

Example service file:

```ini
[Unit]
Description=Smart Camera Station
After=graphical.target
Wants=graphical.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Camera-Project-Source
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/home/pi/Camera-Project-Source/.venv/bin/python /home/pi/Camera-Project-Source/menu_system.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

To enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable camera-app.service
sudo systemctl start camera-app.service
```

## Development

Kromico is both a hardware and software project. In addition to the embedded software stack, the system required fabrication of structural components and physical integration of the imaging hardware.

Development also included Python-based image-processing work, including research related to coordinate handling in NumPy and OpenCV. This supports future calibration, image analysis, and expansion of the multispectral processing pipeline.

## Awards

- 1819 Innovation Award, CEAS EXPO 2026
- Second Place, Innovation Challenge

## Team

Kromico was developed by Alba Samsami, Nate Bolin, Jon Scheckel, and Alex Smith.

