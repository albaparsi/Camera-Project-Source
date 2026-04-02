# tests/test_camera.py
import sys
sys.path.append('/home/albasam/camera_project')

from hardware.camera import Camera
import time

print("Camera Module Test Suite")
print("=" * 40)

# Create camera once and reuse it
camera = Camera()

try:
    print("\n=== Test 1: Auto Exposure ===")
    camera.capture_auto("test_auto.jpg")
    settings = camera.get_current_settings()
    print(f"Auto settings: ISO {settings['iso']}, {settings['exposure_seconds']:.3f}s")
    print("✓ Auto exposure works")
    
    print("\n=== Test 2: Low Manual Exposure ===")
    camera.capture("test_low.jpg", iso=100, shutter_speed=0.01)  # Very short
    print("✓ Low exposure works")
    
    print("\n=== Test 3: Medium Manual Exposure ===")
    camera.capture("test_medium.jpg", iso=400, shutter_speed=0.1)
    print("✓ Medium exposure works")
    
    print("\n=== Test 4: Multiple Captures ===")
    for i in range(3):
        print(f"Capture {i+1}/3...")
        camera.capture(f"test_frame_{i}.jpg", iso=200, shutter_speed=0.05)  # Much lower
        time.sleep(0.5)
    print("✓ Multiple captures work")
    
    print("\n=== Test 5: Exposure Range ===")
    camera.test_exposure_range()
    
    print("\n" + "=" * 40)
    print("✓ ALL TESTS PASSED")
    print("\nReview test images:")
    print("  - test_auto.jpg (best reference)")
    print("  - test_low.jpg")
    print("  - test_medium.jpg")
    print("  - test_frame_*.jpg")
    print("  - test_exposures/")
    
except Exception as e:
    print(f"\n✗ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    camera.stop()
    print("\nCamera stopped and cleaned up")
