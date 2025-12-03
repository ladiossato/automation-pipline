"""
Browser Control Module
Handles screen capture and browser interaction via pyautogui
"""

import time
import logging
from pathlib import Path
from datetime import datetime

import pyautogui
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SCREENSHOTS_DIR, LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class BrowserController:
    """Controls browser interaction and screen capture"""

    def __init__(self):
        """Initialize browser controller with safety features"""
        logger.info("Initializing BrowserController")

        # Enable fail-safe (move mouse to corner to abort)
        pyautogui.FAILSAFE = True
        logger.info("  Fail-safe enabled (move mouse to top-left corner to abort)")

        # Set default pause between actions
        pyautogui.PAUSE = 0.1

        # Get screen dimensions
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"  Screen size: {self.screen_width}x{self.screen_height}")

        # Ensure screenshots directory exists
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"  Screenshots dir: {SCREENSHOTS_DIR}")

        logger.info("  BrowserController ready")

    def capture_full_screen(self, save_path: str = None) -> Image.Image:
        """
        Capture the entire screen

        Args:
            save_path: Optional path to save screenshot

        Returns:
            PIL Image object
        """
        logger.info("Capturing full screen")
        start_time = time.time()

        screenshot = pyautogui.screenshot()

        duration = time.time() - start_time
        logger.info(f"  Size: {screenshot.size}")
        logger.info(f"  Duration: {duration*1000:.0f}ms")

        if save_path:
            screenshot.save(save_path)
            logger.info(f"  Saved to: {save_path}")

        return screenshot

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        save_path: str = None
    ) -> Image.Image:
        """
        Capture a specific region of the screen

        Args:
            x: Left coordinate
            y: Top coordinate
            width: Region width
            height: Region height
            save_path: Optional path to save screenshot

        Returns:
            PIL Image object
        """
        logger.info(f"Capturing region: ({x}, {y}, {width}x{height})")

        # Validate bounds
        if x < 0 or y < 0:
            logger.warning(f"  Adjusting negative coordinates")
            x = max(0, x)
            y = max(0, y)

        if x + width > self.screen_width:
            width = self.screen_width - x
            logger.warning(f"  Adjusted width to {width}")

        if y + height > self.screen_height:
            height = self.screen_height - y
            logger.warning(f"  Adjusted height to {height}")

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        logger.info(f"  Captured: {screenshot.size}")

        if save_path:
            screenshot.save(save_path)
            logger.info(f"  Saved to: {save_path}")

        return screenshot

    def save_screenshot(self, image: Image.Image, prefix: str = "screenshot") -> str:
        """
        Save screenshot with timestamp

        Args:
            image: PIL Image to save
            prefix: Filename prefix

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename

        image.save(str(filepath))
        logger.info(f"Screenshot saved: {filepath}")

        return str(filepath)

    def focus_edge_browser(self, timeout: float = 5.0, max_retries: int = 3) -> bool:
        """
        Attempt to focus Microsoft Edge browser window using pygetwindow

        Args:
            timeout: Max time to wait for focus per attempt
            max_retries: Number of retry attempts if Edge not found

        Returns:
            bool: True if focused successfully
        """
        logger.info("Focusing Microsoft Edge browser (using pygetwindow)")

        import pygetwindow as gw

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"  Retry attempt {attempt + 1}/{max_retries}...")
                    time.sleep(1)

                # Find Edge windows by title (Edge windows contain "Edge" or specific page titles)
                edge_windows = []
                all_windows = gw.getAllWindows()

                for win in all_windows:
                    title = win.title.lower()
                    # Edge windows typically have "edge" in title or are from msedge process
                    if 'edge' in title or 'microsoft' in title:
                        edge_windows.append(win)

                # If no "edge" in title, look for any browser-like window
                if not edge_windows:
                    for win in all_windows:
                        # Look for windows with common web page indicators
                        if win.title and len(win.title) > 5:
                            title = win.title.lower()
                            if any(x in title for x in ['http', 'www', '.com', '.net', '.org', 'doordash', 'uber', 'grubhub']):
                                edge_windows.append(win)

                logger.info(f"  Found {len(edge_windows)} potential Edge window(s)")

                if edge_windows:
                    # Use the first (most recent) Edge window
                    edge_win = edge_windows[0]
                    logger.info(f"  Activating window: '{edge_win.title[:50]}...'")

                    # Restore if minimized
                    if edge_win.isMinimized:
                        logger.info("  Window was minimized, restoring...")
                        edge_win.restore()
                        time.sleep(0.3)

                    # Bring to front and activate
                    try:
                        edge_win.activate()
                        time.sleep(0.5)  # Wait for activation
                        logger.info("  ✓ Edge browser focused successfully")
                        return True
                    except Exception as e:
                        # Sometimes activate() fails but window is still brought to front
                        logger.warning(f"  activate() raised: {e}, but continuing...")
                        # Try clicking on the window to ensure focus
                        try:
                            # Click on center of window
                            center_x = edge_win.left + edge_win.width // 2
                            center_y = edge_win.top + 100  # Click near top (toolbar area)
                            pyautogui.click(center_x, center_y)
                            time.sleep(0.3)
                            logger.info("  ✓ Clicked on window to ensure focus")
                            return True
                        except:
                            pass
                else:
                    logger.warning("  No Edge windows found")
                    # List available windows for debugging
                    visible_windows = [w.title for w in all_windows if w.title and w.visible]
                    logger.info(f"  Available windows: {visible_windows[:5]}")

            except Exception as e:
                logger.error(f"  Error focusing Edge: {e}")
                import traceback
                traceback.print_exc()

        # Fallback: Try Alt+Tab as last resort
        logger.info("  Trying Alt+Tab as fallback...")
        try:
            pyautogui.hotkey('alt', 'tab')
            time.sleep(0.5)
            logger.info("  Alt+Tab executed")
            return True  # Can't verify but assume it worked
        except Exception as e:
            logger.error(f"  Alt+Tab failed: {e}")

        return False

    def scroll_down(self, pixels: int = 500, smooth: bool = False):
        """
        Scroll down the current window

        Args:
            pixels: Number of pixels to scroll (approximate)
            smooth: Use smooth scrolling animation
        """
        logger.info(f"Scrolling down {pixels}px")

        # pyautogui.scroll uses "clicks" - roughly 100px per click
        clicks = -(pixels // 100)  # Negative for scrolling down

        if smooth:
            # Smooth scroll in smaller increments
            for _ in range(abs(clicks)):
                pyautogui.scroll(-1 if clicks < 0 else 1)
                time.sleep(0.05)
        else:
            pyautogui.scroll(clicks)

        logger.info("  Scroll complete")

    def scroll_up(self, pixels: int = 500):
        """Scroll up the current window"""
        logger.info(f"Scrolling up {pixels}px")
        clicks = pixels // 100
        pyautogui.scroll(clicks)
        logger.info("  Scroll complete")

    def scroll_to_top(self):
        """Scroll to top of page using Ctrl+Home"""
        logger.info("Scrolling to top of page")
        pyautogui.hotkey('ctrl', 'Home')
        time.sleep(0.3)
        logger.info("  At top of page")

    def scroll_to_bottom(self):
        """Scroll to bottom of page using Ctrl+End"""
        logger.info("Scrolling to bottom of page")
        pyautogui.hotkey('ctrl', 'End')
        time.sleep(0.3)
        logger.info("  At bottom of page")

    def click(self, x: int, y: int, button: str = 'left'):
        """
        Click at specified coordinates

        Args:
            x: X coordinate
            y: Y coordinate
            button: 'left', 'right', or 'middle'
        """
        logger.info(f"Clicking at ({x}, {y}) with {button} button")

        # Validate coordinates
        if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
            logger.error(f"  Coordinates out of screen bounds!")
            return

        pyautogui.click(x, y, button=button)
        logger.info("  Click complete")

    def double_click(self, x: int, y: int):
        """Double-click at specified coordinates"""
        logger.info(f"Double-clicking at ({x}, {y})")
        pyautogui.doubleClick(x, y)
        logger.info("  Double-click complete")

    def move_to(self, x: int, y: int, duration: float = 0.25):
        """
        Move mouse to coordinates

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration in seconds
        """
        logger.info(f"Moving mouse to ({x}, {y})")
        pyautogui.moveTo(x, y, duration=duration)
        logger.info("  Move complete")

    def get_mouse_position(self) -> tuple:
        """Get current mouse position"""
        pos = pyautogui.position()
        logger.info(f"Mouse position: ({pos.x}, {pos.y})")
        return (pos.x, pos.y)

    def type_text(self, text: str, interval: float = 0.05):
        """
        Type text at current cursor position

        Args:
            text: Text to type
            interval: Delay between keystrokes
        """
        logger.info(f"Typing text: '{text[:50]}...' ({len(text)} chars)")
        pyautogui.write(text, interval=interval)
        logger.info("  Typing complete")

    def press_key(self, key: str):
        """Press a single key"""
        logger.info(f"Pressing key: {key}")
        pyautogui.press(key)
        logger.info("  Key press complete")

    def hotkey(self, *keys):
        """Press key combination (e.g., hotkey('ctrl', 'c'))"""
        logger.info(f"Pressing hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)
        logger.info("  Hotkey complete")

    def wait(self, seconds: float):
        """Wait for specified duration"""
        logger.info(f"Waiting {seconds}s...")
        time.sleep(seconds)
        logger.info("  Wait complete")
