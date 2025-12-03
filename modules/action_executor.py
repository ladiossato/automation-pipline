"""
Action Executor Module
Executes pre-extraction actions (clicks, waits) before OCR extraction
"""

import time
import logging
from typing import List, Dict, Any, Optional

import numpy as np
import pyautogui

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes pre-extraction actions before OCR capture"""

    def __init__(self, browser_controller=None, ocr_handler=None, dom_extractor=None):
        """
        Initialize action executor

        Args:
            browser_controller: BrowserController instance for screenshots
            ocr_handler: OCRHandler instance for text detection
            dom_extractor: DOMExtractor instance for browser-native clicks via CDP
        """
        self.browser = browser_controller
        self.ocr = ocr_handler
        self.dom_extractor = dom_extractor
        logger.info("ActionExecutor initialized")

    def set_browser(self, browser_controller):
        """Set browser controller (for lazy initialization)"""
        self.browser = browser_controller

    def set_ocr(self, ocr_handler):
        """Set OCR handler (for lazy initialization)"""
        self.ocr = ocr_handler

    def set_dom_extractor(self, dom_extractor):
        """Set DOM extractor (for browser-native clicks)"""
        self.dom_extractor = dom_extractor

    def execute_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute all pre-extraction actions in sequence

        Args:
            actions: List of action dictionaries

        Returns:
            Dict with execution status and details
        """
        if not actions:
            logger.info("No pre-extraction actions to execute")
            return {'success': True, 'actions_executed': 0}

        logger.info("=" * 60)
        logger.info("EXECUTING PRE-EXTRACTION ACTIONS")
        logger.info("=" * 60)
        logger.info(f"  Total actions: {len(actions)}")

        results = []
        failed = False

        for i, action in enumerate(actions, 1):
            logger.info(f"\n[ACTION {i}/{len(actions)}]")
            logger.info(f"  Type: {action.get('type', 'unknown')}")

            try:
                result = self._execute_single_action(action)
                results.append({
                    'index': i,
                    'type': action.get('type'),
                    'success': result.get('success', True),
                    'details': result
                })

                if result.get('success', True):
                    logger.info(f"  Action {i} complete")
                else:
                    logger.warning(f"  Action {i} failed: {result.get('error')}")
                    if action.get('stop_on_failure', False):
                        failed = True
                        break

            except Exception as e:
                logger.error(f"  Action {i} error: {e}")
                results.append({
                    'index': i,
                    'type': action.get('type'),
                    'success': False,
                    'error': str(e)
                })
                if action.get('stop_on_failure', False):
                    failed = True
                    break

        logger.info("\n" + "=" * 60)
        if not failed:
            logger.info("ALL PRE-EXTRACTION ACTIONS COMPLETE")
        else:
            logger.warning("PRE-EXTRACTION ACTIONS STOPPED (failure)")
        logger.info("=" * 60 + "\n")

        return {
            'success': not failed,
            'actions_executed': len(results),
            'results': results
        }

    def _execute_single_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single action

        Args:
            action: Action configuration dict

        Returns:
            Result dict with success status
        """
        action_type = action.get('type', '')

        if action_type == 'click_coordinates':
            return self._click_coordinates(action)
        elif action_type == 'click_ocr':
            return self._click_by_text(action)
        elif action_type == 'wait':
            return self._wait(action)
        elif action_type == 'scroll':
            return self._scroll(action)
        elif action_type == 'type_text':
            return self._type_text(action)
        elif action_type == 'press_key':
            return self._press_key(action)
        else:
            logger.warning(f"  Unknown action type: {action_type}")
            return {'success': False, 'error': f'Unknown action type: {action_type}'}

    def _click_coordinates(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Click at specific coordinates using pyautogui (most reliable method).

        pyautogui performs actual physical mouse movement and click which works
        on all websites, unlike CDP/JavaScript clicks which can be blocked.
        """
        x = action.get('x', 0)
        y = action.get('y', 0)
        wait_after = action.get('wait_after', 2)
        clicks = action.get('clicks', 1)

        logger.info(f"  Clicking at ({x}, {y}) using pyautogui...")

        # Use pyautogui for reliable physical click
        # This moves the actual mouse cursor and performs a real click
        pyautogui.click(x, y, clicks=clicks)
        logger.info(f"  ✓ Click executed at ({x}, {y})")

        if wait_after > 0:
            logger.info(f"  Waiting {wait_after}s...")
            time.sleep(wait_after)

        return {
            'success': True,
            'x': x,
            'y': y,
            'clicks': clicks
        }

    def _click_by_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Find element by text using OCR and click it"""
        search_text = action.get('search_text', '')
        confidence_threshold = action.get('confidence_threshold', 0.7)
        wait_after = action.get('wait_after', 2)
        search_region = action.get('search_region', None)

        if not search_text:
            return {'success': False, 'error': 'No search text specified'}

        logger.info(f"  Searching for text: '{search_text}'")

        # Capture screenshot
        if self.browser is None:
            return {'success': False, 'error': 'Browser controller not initialized'}

        screenshot = self.browser.capture_full_screen()

        # Crop to search region if specified
        if search_region:
            x = search_region.get('x', 0)
            y = search_region.get('y', 0)
            w = search_region.get('width', screenshot.width)
            h = search_region.get('height', screenshot.height)
            screenshot = screenshot.crop((x, y, x + w, y + h))
            offset_x, offset_y = x, y
        else:
            offset_x, offset_y = 0, 0

        # Run OCR
        if self.ocr is None:
            return {'success': False, 'error': 'OCR handler not initialized'}

        img_array = np.array(screenshot)
        results = self.ocr.reader.readtext(img_array)

        # Find matching text
        search_lower = search_text.lower()

        for bbox, text, conf in results:
            if search_lower in text.lower() and conf >= confidence_threshold:
                # Calculate center of bounding box
                center_x = int((bbox[0][0] + bbox[2][0]) / 2) + offset_x
                center_y = int((bbox[0][1] + bbox[2][1]) / 2) + offset_y

                logger.info(f"  Found '{text}' at ({center_x}, {center_y}) [conf: {conf*100:.1f}%]")
                logger.info(f"  Clicking using pyautogui...")

                # Use pyautogui for reliable physical click
                pyautogui.click(center_x, center_y)
                logger.info(f"  ✓ Click executed at ({center_x}, {center_y})")

                if wait_after > 0:
                    logger.info(f"  Waiting {wait_after}s...")
                    time.sleep(wait_after)

                return {
                    'success': True,
                    'found_text': text,
                    'x': center_x,
                    'y': center_y,
                    'confidence': conf
                }

        logger.warning(f"  Text '{search_text}' not found on screen")
        return {
            'success': False,
            'error': f"Text '{search_text}' not found"
        }

    def _wait(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for specified duration"""
        duration = action.get('duration', 1)

        logger.info(f"  Waiting {duration}s...")
        time.sleep(duration)

        return {'success': True, 'duration': duration}

    def _scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll the page using browser-native scrolling when available"""
        direction = action.get('direction', 'down')
        amount = action.get('amount', 300)
        wait_after = action.get('wait_after', 1)

        logger.info(f"  Scrolling {direction} by {amount}px")

        # Try browser-native scroll first
        if self.dom_extractor and self.dom_extractor._connected:
            try:
                # Use JavaScript to scroll the page
                scroll_amount = amount if direction == 'down' else -amount
                js_code = f"window.scrollBy(0, {scroll_amount})"
                self.dom_extractor._execute_js(js_code)
                logger.info(f"  ✓ Browser-native scroll executed")
            except Exception as e:
                logger.warning(f"  Browser-native scroll failed, using pyautogui: {e}")
                if direction == 'down':
                    pyautogui.scroll(-amount // 100)
                elif direction == 'up':
                    pyautogui.scroll(amount // 100)
        else:
            # Fallback to pyautogui
            if direction == 'down':
                pyautogui.scroll(-amount // 100)  # pyautogui uses clicks, not pixels
            elif direction == 'up':
                pyautogui.scroll(amount // 100)

        if wait_after > 0:
            logger.info(f"  Waiting {wait_after}s...")
            time.sleep(wait_after)

        return {'success': True, 'direction': direction, 'amount': amount}

    def _type_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Type text at current cursor position"""
        text = action.get('text', '')
        interval = action.get('interval', 0.05)
        wait_after = action.get('wait_after', 1)

        if not text:
            return {'success': False, 'error': 'No text to type'}

        logger.info(f"  Typing text: '{text[:30]}...'")

        pyautogui.typewrite(text, interval=interval)

        if wait_after > 0:
            logger.info(f"  Waiting {wait_after}s...")
            time.sleep(wait_after)

        return {'success': True, 'text_length': len(text)}

    def _press_key(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Press a keyboard key"""
        key = action.get('key', '')
        wait_after = action.get('wait_after', 0.5)

        if not key:
            return {'success': False, 'error': 'No key specified'}

        logger.info(f"  Pressing key: {key}")

        pyautogui.press(key)

        if wait_after > 0:
            logger.info(f"  Waiting {wait_after}s...")
            time.sleep(wait_after)

        return {'success': True, 'key': key}

    def test_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single action immediately

        Args:
            action: Action configuration to test

        Returns:
            Result dict with success status and details
        """
        logger.info("=" * 60)
        logger.info("TESTING SINGLE ACTION")
        logger.info("=" * 60)
        logger.info(f"  Action type: {action.get('type')}")

        result = self._execute_single_action(action)

        logger.info("=" * 60)
        if result.get('success'):
            logger.info("ACTION TEST SUCCESSFUL")
        else:
            logger.warning(f"ACTION TEST FAILED: {result.get('error')}")
        logger.info("=" * 60)

        return result
