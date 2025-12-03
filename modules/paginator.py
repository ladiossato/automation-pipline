"""
Paginator Module
Handles scrolling and pagination for multi-page data extraction
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import numpy as np
from PIL import Image, ImageChops

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCREENSHOTS_DIR, LOG_FORMAT, LOG_DATE_FORMAT,
    DEFAULT_SCROLL_PIXELS, DEFAULT_SCROLL_WAIT, DEFAULT_MAX_SCROLLS,
    DEFAULT_MAX_PAGES, DEFAULT_PAGE_WAIT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class Paginator:
    """Handles scrolling and pagination for data extraction"""

    def __init__(self, browser, ocr):
        """
        Initialize paginator with browser and OCR handlers

        Args:
            browser: BrowserController instance
            ocr: OCRHandler instance
        """
        logger.info("Initializing Paginator")
        self.browser = browser
        self.ocr = ocr
        logger.info("  Paginator ready")

    def scroll_and_extract(
        self,
        regions: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Scroll through page and extract data from all scroll positions

        Args:
            regions: List of OCR region definitions
            config: Scroll configuration {
                max_scrolls: int,
                wait_time: float,
                scroll_pixels: int
            }

        Returns:
            List of extracted data dicts from all scroll positions
        """
        logger.info("=" * 60)
        logger.info("SCROLL MODE: Extracting with scrolling")
        logger.info("=" * 60)

        max_scrolls = config.get('max_scrolls', DEFAULT_MAX_SCROLLS)
        wait_time = config.get('wait_time', DEFAULT_SCROLL_WAIT)
        scroll_pixels = config.get('scroll_pixels', DEFAULT_SCROLL_PIXELS)

        logger.info(f"  Max scrolls: {max_scrolls}")
        logger.info(f"  Wait time: {wait_time}s")
        logger.info(f"  Scroll pixels: {scroll_pixels}")

        all_data = []
        scroll_count = 0
        previous_screenshot = None
        consecutive_same = 0

        # Scroll to top first
        logger.info("\nScrolling to top of page...")
        self.browser.scroll_to_top()
        time.sleep(1)

        while scroll_count < max_scrolls:
            logger.info(f"\n[SCROLL {scroll_count + 1}/{max_scrolls}]")

            # Capture current view
            screenshot = self.browser.capture_full_screen()
            screenshot_path = SCREENSHOTS_DIR / f"scroll_{scroll_count:03d}.png"
            screenshot.save(str(screenshot_path))
            logger.info(f"  Screenshot: {screenshot_path.name}")

            # Extract data from regions
            extracted = self.ocr.extract_all_regions(screenshot, regions)
            data_dict = self.ocr.get_data_as_dict(extracted)

            # Add metadata
            data_dict['_scroll_position'] = scroll_count
            data_dict['_timestamp'] = datetime.now().isoformat()

            all_data.append(data_dict)
            logger.info(f"  Extracted {len(extracted)} fields")

            # Check if content has changed (reached bottom)
            if previous_screenshot is not None:
                if self._images_similar(previous_screenshot, screenshot):
                    consecutive_same += 1
                    logger.info(f"  Content unchanged ({consecutive_same}/3)")

                    if consecutive_same >= 3:
                        logger.info("  Reached bottom (no new content)")
                        break
                else:
                    consecutive_same = 0

            previous_screenshot = screenshot

            # Scroll down
            self.browser.scroll_down(scroll_pixels)
            logger.info(f"  Waiting {wait_time}s for content to load...")
            time.sleep(wait_time)

            scroll_count += 1

        logger.info("\n" + "=" * 60)
        logger.info("SCROLL EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Total scrolls: {scroll_count}")
        logger.info(f"  Data points collected: {len(all_data)}")
        logger.info("=" * 60)

        return all_data

    def paginate_and_extract(
        self,
        regions: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Click through pagination and extract from all pages

        Args:
            regions: List of OCR region definitions
            config: Pagination configuration {
                mode: 'ocr' or 'coordinates',
                button_text: str (for OCR mode),
                button_x: int (for coordinates mode),
                button_y: int (for coordinates mode),
                search_region: dict (optional, for OCR mode),
                max_pages: int
            }

        Returns:
            List of extracted data dicts from all pages
        """
        logger.info("=" * 60)
        logger.info("PAGINATION MODE: Extracting from multiple pages")
        logger.info("=" * 60)

        max_pages = config.get('max_pages', DEFAULT_MAX_PAGES)
        button_text = config.get('button_text', 'Next')
        mode = config.get('mode', 'ocr')
        page_wait = config.get('wait_time', DEFAULT_PAGE_WAIT)

        logger.info(f"  Mode: {mode}")
        logger.info(f"  Button text: '{button_text}' (for OCR mode)")
        logger.info(f"  Max pages: {max_pages}")
        logger.info(f"  Page wait: {page_wait}s")

        all_data = []
        page_num = 1
        consecutive_same = 0

        while page_num <= max_pages:
            logger.info(f"\n[PAGE {page_num}/{max_pages}]")

            # Capture current page
            screenshot = self.browser.capture_full_screen()
            screenshot_path = SCREENSHOTS_DIR / f"page_{page_num:03d}.png"
            screenshot.save(str(screenshot_path))
            logger.info(f"  Screenshot: {screenshot_path.name}")

            # Extract data from regions
            extracted = self.ocr.extract_all_regions(screenshot, regions)
            data_dict = self.ocr.get_data_as_dict(extracted)

            # Add metadata
            data_dict['_page_number'] = page_num
            data_dict['_timestamp'] = datetime.now().isoformat()

            all_data.append(data_dict)
            logger.info(f"  Extracted {len(extracted)} fields")

            # Find and click Next button
            logger.info(f"  Looking for '{button_text}' button...")
            next_button = self._find_next_button(screenshot, button_text, config)

            if not next_button:
                logger.info("  No more pages (button not found)")
                break

            logger.info(f"  Found button at ({next_button['x']}, {next_button['y']})")

            # Click the button
            self.browser.click(next_button['x'], next_button['y'])

            # Wait for page load
            logger.info(f"  Waiting {page_wait}s for page load...")
            time.sleep(page_wait)

            # Check if page actually changed
            new_screenshot = self.browser.capture_full_screen()

            if self._images_similar(screenshot, new_screenshot):
                consecutive_same += 1
                logger.warning(f"  Page unchanged after click ({consecutive_same}/3)")

                if consecutive_same >= 3:
                    logger.info("  Reached last page (no change after clicks)")
                    break
            else:
                consecutive_same = 0

            page_num += 1

        logger.info("\n" + "=" * 60)
        logger.info("PAGINATION EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Total pages: {page_num}")
        logger.info(f"  Data points collected: {len(all_data)}")
        logger.info("=" * 60)

        return all_data

    def _find_next_button(
        self,
        screenshot: Image.Image,
        button_text: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, int]]:
        """
        Find Next button location using OCR or fixed coordinates

        Args:
            screenshot: Current page screenshot
            button_text: Text to search for
            config: Pagination config

        Returns:
            Dict with {x, y} coordinates, or None if not found
        """
        mode = config.get('mode', 'ocr')

        if mode == 'coordinates':
            # Use fixed coordinates
            x = config.get('button_x')
            y = config.get('button_y')

            if x is not None and y is not None:
                logger.info(f"  Using fixed coordinates: ({x}, {y})")
                return {'x': x, 'y': y}
            else:
                logger.error("  Coordinates mode but no button_x/button_y specified!")
                return None

        elif mode == 'ocr':
            # Search for button text using OCR
            logger.info(f"  Searching for '{button_text}' via OCR...")

            # Define search region (bottom of screen by default)
            search_region = config.get('search_region')

            if search_region:
                # Crop to search region
                cropped = screenshot.crop((
                    search_region['x'],
                    search_region['y'],
                    search_region['x'] + search_region['width'],
                    search_region['y'] + search_region['height']
                ))
                offset_x = search_region['x']
                offset_y = search_region['y']
            else:
                # Search bottom 200px of screen
                width, height = screenshot.size
                cropped = screenshot.crop((0, height - 200, width, height))
                offset_x = 0
                offset_y = height - 200

            # Run OCR on search region
            img_array = np.array(cropped)
            results = self.ocr.reader.readtext(img_array)

            # Find matching text
            for bbox, text, conf in results:
                if button_text.lower() in text.lower() and conf > 0.6:
                    # Calculate center of bounding box
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    center_x = int(sum(x_coords) / len(x_coords)) + offset_x
                    center_y = int(sum(y_coords) / len(y_coords)) + offset_y

                    logger.info(f"  Found '{text}' at ({center_x}, {center_y}) conf={conf*100:.1f}%")
                    return {'x': center_x, 'y': center_y}

            logger.warning(f"  Button '{button_text}' not found in OCR results")
            return None

        else:
            logger.error(f"  Unknown pagination mode: {mode}")
            return None

    def _images_similar(
        self,
        img1: Image.Image,
        img2: Image.Image,
        threshold: float = 0.98
    ) -> bool:
        """
        Check if two images are nearly identical

        Args:
            img1: First image
            img2: Second image
            threshold: Similarity threshold (0-1)

        Returns:
            bool: True if images are similar above threshold
        """
        try:
            # Ensure same size
            if img1.size != img2.size:
                return False

            # Convert to grayscale for comparison
            gray1 = img1.convert('L')
            gray2 = img2.convert('L')

            # Calculate difference
            diff = ImageChops.difference(gray1, gray2)

            # Get histogram of differences
            hist = diff.histogram()

            # Calculate percentage of pixels that are very similar
            total_pixels = img1.size[0] * img1.size[1]
            similar_pixels = sum(hist[:10])  # Pixels with diff < 10

            similarity = similar_pixels / total_pixels
            logger.debug(f"  Image similarity: {similarity*100:.1f}%")

            return similarity > threshold

        except Exception as e:
            logger.error(f"  Error comparing images: {e}")
            return False

    def extract_single_page(
        self,
        regions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract data from current page without scrolling/pagination

        Args:
            regions: List of OCR region definitions

        Returns:
            Dict of extracted field values
        """
        logger.info("=" * 60)
        logger.info("SINGLE PAGE EXTRACTION")
        logger.info("=" * 60)

        # Capture current view
        screenshot = self.browser.capture_full_screen()
        screenshot_path = SCREENSHOTS_DIR / f"single_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        screenshot.save(str(screenshot_path))
        logger.info(f"  Screenshot: {screenshot_path}")

        # Extract data
        extracted = self.ocr.extract_all_regions(screenshot, regions)
        data_dict = self.ocr.get_data_as_dict(extracted)

        # Add metadata
        data_dict['_page_number'] = 1
        data_dict['_timestamp'] = datetime.now().isoformat()

        logger.info(f"  Extracted {len(extracted)} fields")
        logger.info("=" * 60)

        return data_dict
