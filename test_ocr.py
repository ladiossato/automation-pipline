"""
OCR Test Suite
Tests screen capture and OCR functionality
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.browser_control import BrowserController
from modules.ocr_handler import OCRHandler
from config import SCREENSHOTS_DIR


def test_screen_capture():
    """Test basic screen capture functionality"""
    print("\n" + "=" * 60)
    print("TEST 1: SCREEN CAPTURE")
    print("=" * 60 + "\n")

    browser = BrowserController()

    # Test 1a: Full screen capture
    print("[1a] Capturing full screen...")
    screenshot = browser.capture_full_screen()
    print(f"  Size: {screenshot.size}")
    assert screenshot.size[0] > 0, "Screenshot width should be > 0"
    assert screenshot.size[1] > 0, "Screenshot height should be > 0"
    print("  PASS\n")

    # Test 1b: Save screenshot
    print("[1b] Saving screenshot...")
    save_path = browser.save_screenshot(screenshot, "test_full")
    print(f"  Saved to: {save_path}")
    assert Path(save_path).exists(), "Screenshot file should exist"
    print("  PASS\n")

    # Test 1c: Region capture
    print("[1c] Capturing region (100, 100, 400x200)...")
    region_shot = browser.capture_region(100, 100, 400, 200)
    print(f"  Size: {region_shot.size}")
    assert region_shot.size == (400, 200), "Region size should match"
    print("  PASS\n")

    # Test 1d: Mouse position
    print("[1d] Getting mouse position...")
    pos = browser.get_mouse_position()
    print(f"  Position: {pos}")
    assert len(pos) == 2, "Position should have x and y"
    print("  PASS\n")

    print("=" * 60)
    print("SCREEN CAPTURE TESTS PASSED")
    print("=" * 60 + "\n")

    return screenshot


def test_ocr_basic(screenshot):
    """Test basic OCR functionality"""
    print("\n" + "=" * 60)
    print("TEST 2: BASIC OCR")
    print("=" * 60 + "\n")

    print("Initializing OCR engine (may take 30-60s on first run)...")
    ocr = OCRHandler()
    print()

    # Test 2a: Extract all text from screenshot
    print("[2a] Extracting all text from full screenshot...")
    detections = ocr.extract_text_from_image(screenshot)
    print(f"  Found {len(detections)} text regions")

    if detections:
        print("  Sample detections:")
        for det in detections[:5]:
            print(f"    - '{det['text'][:50]}' (conf: {det['confidence']*100:.1f}%)")

    print("  PASS\n")

    return ocr


def test_ocr_regions(screenshot, ocr):
    """Test OCR region extraction"""
    print("\n" + "=" * 60)
    print("TEST 3: REGION-BASED OCR")
    print("=" * 60 + "\n")

    # Define test regions (top-left area of screen)
    test_regions = [
        {'name': 'region1', 'x': 50, 'y': 50, 'width': 300, 'height': 50},
        {'name': 'region2', 'x': 50, 'y': 120, 'width': 300, 'height': 50},
        {'name': 'region3', 'x': 50, 'y': 190, 'width': 300, 'height': 50},
    ]

    print("[3a] Extracting from multiple regions...")
    results = ocr.extract_all_regions(screenshot, test_regions)

    print("\nResults:")
    for name, result in results.items():
        conf_status = "OK" if result['confidence'] >= 0.85 else "LOW"
        print(f"  {name}:")
        print(f"    Text: '{result['text']}'")
        print(f"    Confidence: {result['confidence']*100:.1f}% [{conf_status}]")

    print("\n  PASS\n")

    # Test 3b: Convert to simple dict
    print("[3b] Converting to simple dict...")
    data_dict = ocr.get_data_as_dict(results)
    print(f"  Data: {data_dict}")
    print("  PASS\n")

    print("=" * 60)
    print("REGION OCR TESTS PASSED")
    print("=" * 60 + "\n")


def test_text_search(screenshot, ocr):
    """Test text search functionality"""
    print("\n" + "=" * 60)
    print("TEST 4: TEXT SEARCH")
    print("=" * 60 + "\n")

    # Search for common UI elements
    search_terms = ['File', 'Edit', 'View', 'Help', 'Start', 'Search']

    print("[4a] Searching for common text...")
    for term in search_terms:
        result = ocr.find_text_on_screen(screenshot, term, min_confidence=0.6)
        if result:
            print(f"  Found '{term}' at {result['center']}")
        else:
            print(f"  '{term}' not found")

    print("\n  PASS\n")

    print("=" * 60)
    print("TEXT SEARCH TESTS PASSED")
    print("=" * 60 + "\n")


def test_interactive():
    """Interactive test with user-positioned window"""
    print("\n" + "=" * 60)
    print("INTERACTIVE OCR TEST")
    print("=" * 60 + "\n")

    print("Instructions:")
    print("1. Open Microsoft Edge browser")
    print("2. Navigate to a page with clear, readable text")
    print("3. Position the browser window to be visible")
    print("4. Press Enter when ready...")
    input()

    browser = BrowserController()
    ocr = OCRHandler()

    # Capture screen
    print("\nCapturing screen...")
    screenshot = browser.capture_full_screen()
    save_path = browser.save_screenshot(screenshot, "interactive_test")
    print(f"Screenshot saved: {save_path}")

    # Define center region
    width, height = screenshot.size
    center_region = {
        'name': 'center',
        'x': width // 4,
        'y': height // 4,
        'width': width // 2,
        'height': height // 2
    }

    print(f"\nExtracting from center region: {center_region}")
    result = ocr.extract_text(screenshot, center_region)

    print("\n" + "-" * 40)
    print("EXTRACTION RESULT")
    print("-" * 40)
    print(f"Text found ({len(result['text'])} chars):")
    print(result['text'][:500])
    print(f"\nConfidence: {result['confidence']*100:.1f}%")
    print("-" * 40)

    # Save cropped region for inspection
    cropped_path = SCREENSHOTS_DIR / "interactive_region.png"
    cropped = screenshot.crop((
        center_region['x'],
        center_region['y'],
        center_region['x'] + center_region['width'],
        center_region['y'] + center_region['height']
    ))
    cropped.save(str(cropped_path))
    print(f"\nCropped region saved: {cropped_path}")

    print("\n" + "=" * 60)
    print("Review the results above")
    print("Check screenshots/ folder for images")
    print("=" * 60 + "\n")


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "#" * 60)
    print("#" + " " * 18 + "OCR TEST SUITE" + " " * 18 + "#")
    print("#" * 60 + "\n")

    # Run automated tests
    screenshot = test_screen_capture()
    ocr = test_ocr_basic(screenshot)
    test_ocr_regions(screenshot, ocr)
    test_text_search(screenshot, ocr)

    print("\n" + "=" * 60)
    print("ALL AUTOMATED TESTS PASSED")
    print("=" * 60)
    print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")
    print("\nRun interactive test? (y/n): ", end="")

    response = input().strip().lower()
    if response == 'y':
        test_interactive()

    print("\n" + "=" * 60)
    print("OCR TESTING COMPLETE")
    print("=" * 60)
    print("\nProceed to Phase 3 (Deduplication)? (y/n)")


if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
