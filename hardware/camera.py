# hardware/camera.py
from picamera2 import Picamera2
import time
import os


class Camera:
    _instance = None
    _picam = None
    
    def __new__(cls, resolution=(1920, 1080)):
        """Ensure only one Camera instance exists"""
        if cls._instance is None:
            cls._instance = super(Camera, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, resolution=(1920, 1080)):
        """Initialize camera with default resolution"""
        if self._initialized:
            return
            
        self.picam = Picamera2()
        self.resolution = resolution
        self.is_started = False
        
        # Configure camera
        config = self.picam.create_still_configuration(
            main={"size": resolution}
        )
        self.picam.configure(config)
        self._initialized = True
        
    def start(self):
        """Start camera preview/capture mode"""
        if not self.is_started:
            self.picam.start()
            self.is_started = True
            time.sleep(2)  # Let camera warm up
    
    def capture(self, filename, iso=None, shutter_speed=None, format='jpg'):
        """
        Capture image with optional manual exposure settings
        
        Args:
            filename: Output file path
            iso: ISO sensitivity (None for auto)
            shutter_speed: Exposure time in seconds (None for auto)
            format: Image format (jpg, png, dng for raw)
        """
        if not self.is_started:
            self.start()
        
        if iso is not None and shutter_speed is not None:
            # Manual mode
            exposure_us = int(shutter_speed * 1000000)
            exposure_us = max(1, min(exposure_us, 200000000))  # Clamp
            
            gain = iso / 100.0
            gain = max(1.0, min(gain, 16.0))
            
            self.picam.set_controls({
                "AeEnable": False,
                "ExposureTime": exposure_us,
                "AnalogueGain": gain
            })
            time.sleep(0.5)
        else:
            # Auto mode
            self.picam.set_controls({"AeEnable": True})
            time.sleep(1)
        
        # Capture
        self.picam.capture_file(filename)
        
        if iso and shutter_speed:
            print(f"✓ Captured: {filename} (ISO {iso}, {shutter_speed}s)")
        else:
            print(f"✓ Captured (auto): {filename}")
        
        return filename
    
    def capture_auto(self, filename):
        """Capture with auto exposure"""
        return self.capture(filename, iso=None, shutter_speed=None)

    def capture_frame(self):
        """Capture a single preview frame as a NumPy array."""
        if not self.is_started:
            self.start()

        return self.picam.capture_array()
    
    def get_current_settings(self):
        """Get current exposure settings"""
        metadata = self.picam.capture_metadata()
        exposure_us = metadata.get("ExposureTime", 0)
        gain = metadata.get("AnalogueGain", 0)
        
        return {
            "exposure_seconds": exposure_us / 1000000,
            "iso": int(gain * 100),
            "gain": gain
        }
    
    def test_exposure_range(self, output_dir="test_exposures"):
        """Test different ISO/exposure combinations"""
        os.makedirs(output_dir, exist_ok=True)
        
        test_configs = [
            (100, 0.01),   # Very short
            (100, 0.1),
            (400, 0.5),
            (800, 1.0),
        ]
        
        print("\n=== Testing Exposure Range ===")
        for iso, shutter in test_configs:
            filename = f"{output_dir}/test_iso{iso}_s{shutter}.jpg"
            print(f"Testing ISO {iso}, {shutter}s...")
            try:
                self.capture(filename, iso=iso, shutter_speed=shutter)
            except Exception as e:
                print(f"  ✗ Failed: {e}")
        
        print("✓ Test complete! Check images in", output_dir)
    
    def stop(self):
        """Stop camera"""
        if self.is_started:
            self.picam.stop()
            self.is_started = False
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'is_started'):
            self.stop()

    def get_auto_baseline(self, temp_filename="/tmp/auto_baseline.jpg"):
        """
        Take one auto-exposed frame, return the ISO and shutter time it used.
        """
        self.capture_auto(temp_filename)
        settings = self.get_current_settings()
        return {
            "iso": settings["iso"],
            "shutter_speed": settings["exposure_seconds"]
        }
