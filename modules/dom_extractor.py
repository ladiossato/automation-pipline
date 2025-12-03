"""
DOM Extractor Module
Extracts data directly from HTML DOM using CSS selectors
Uses Edge DevTools Protocol to connect to existing browser (no Playwright/Chromium needed)
"""

import os
import json
import logging
import time
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LOG_FORMAT, LOG_DATE_FORMAT

# Try to import websocket
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("WARNING: websocket-client not installed. Run: pip install websocket-client")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class DOMExtractor:
    """
    Extracts data from web pages using CSS selectors.
    Connects to your existing Edge browser via DevTools Protocol.
    No Chromium installation required!
    """

    def __init__(self):
        """Initialize DOM extractor"""
        logger.info("Initializing DOMExtractor")
        self.debugger_url = None
        self.ws_url = None
        self._connected = False
        self._page_id = None
        logger.info("  DOMExtractor ready (not connected)")

    def _find_edge_debug_port(self) -> Optional[int]:
        """
        Find if Edge is running with remote debugging enabled.
        Returns the debug port if found.
        """
        # Common debug ports
        for port in [9222, 9223, 9224, 9225]:
            try:
                response = requests.get(f'http://localhost:{port}/json/version', timeout=1)
                if response.status_code == 200:
                    logger.info(f"  Found Edge debugging on port {port}")
                    return port
            except:
                continue
        return None

    def _kill_existing_edge(self) -> bool:
        """
        Kill all existing Edge processes to allow restart with debugging.

        Returns:
            True if Edge processes were killed or none were running
        """
        logger.info("  Checking for existing Edge processes...")

        try:
            # Check if Edge is running
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq msedge.exe'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if 'msedge.exe' in result.stdout:
                logger.info("  Found existing Edge processes, killing them...")

                # Kill all Edge processes
                kill_result = subprocess.run(
                    ['taskkill', '/F', '/IM', 'msedge.exe'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if kill_result.returncode == 0:
                    logger.info("  ✓ All Edge processes killed")
                    time.sleep(2)  # Wait for processes to fully terminate
                    return True
                else:
                    logger.warning(f"  Could not kill all Edge processes: {kill_result.stderr}")
                    return False
            else:
                logger.info("  No existing Edge processes found")
                return True

        except subprocess.TimeoutExpired:
            logger.error("  Timeout while trying to kill Edge processes")
            return False
        except Exception as e:
            logger.error(f"  Error killing Edge processes: {e}")
            return False

    def _start_edge_with_debugging(self, port: int = 9222, url: str = None) -> bool:
        """
        Start Edge with remote debugging enabled.
        This allows us to connect to the browser and run JavaScript.
        Will kill existing Edge processes if needed.

        Args:
            port: Debug port (default 9222)
            url: Optional URL to open when launching Edge
        """
        logger.info(f"Starting Edge with remote debugging on port {port}...")
        if url:
            logger.info(f"  Will open URL: {url[:60]}...")

        # Edge executable paths
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]

        edge_exe = None
        for path in edge_paths:
            if os.path.exists(path):
                edge_exe = path
                break

        if not edge_exe:
            logger.error("  Microsoft Edge not found!")
            return False

        # Kill existing Edge processes first - this is required because
        # Edge cannot enable debugging on an already-running instance
        logger.info("")
        logger.info("  IMPORTANT: Edge must be restarted with debugging flag")
        if not self._kill_existing_edge():
            logger.error("  Could not kill existing Edge processes")
            logger.error("  Please close Edge manually and try again")
            return False

        # User data directory (use existing profile)
        user_data_dir = os.path.join(
            os.path.expanduser('~'),
            'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'
        )

        try:
            # Start Edge with debugging flag
            # IMPORTANT: --remote-allow-origins=* is required for WebSocket connections
            cmd = [
                edge_exe,
                f'--remote-debugging-port={port}',
                '--remote-allow-origins=*',  # Allow WebSocket connections from any origin
                f'--user-data-dir={user_data_dir}',
                '--no-first-run',
                '--start-maximized',
            ]

            # Add URL if provided - Edge will open directly to this page
            if url:
                cmd.append(url)
                logger.info(f"  Launching Edge with URL: {url[:60]}...")

            logger.info(f"  Command: {' '.join(cmd[:3])}...")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for Edge to start (longer if navigating to URL)
            wait_time = 5 if url else 3
            logger.info(f"  Waiting {wait_time}s for Edge to start...")
            time.sleep(wait_time)

            # Verify it's running
            if self._find_edge_debug_port():
                logger.info("  ✓ Edge started with debugging enabled!")
                return True
            else:
                logger.error("  Edge started but debugging not available")
                return False

        except Exception as e:
            logger.error(f"  Failed to start Edge: {e}")
            return False

    def connect_to_browser(self, port: int = 9222, url: str = None) -> bool:
        """
        Connect to existing Edge browser via DevTools Protocol.
        If Edge isn't running with debugging, starts it with the provided URL.

        Args:
            port: Debug port (default 9222)
            url: URL to open if launching new Edge instance

        Returns:
            True if connected successfully
        """
        logger.info("=" * 60)
        logger.info("CONNECTING TO EDGE BROWSER")
        logger.info("=" * 60)
        if url:
            logger.info(f"  Target URL: {url[:60]}...")

        # Check websocket availability
        if not WEBSOCKET_AVAILABLE:
            logger.error("CRITICAL: websocket-client not installed!")
            logger.error("Run: pip install websocket-client")
            return False

        if self._connected:
            logger.info("Already connected to browser")
            return True

        logger.info("Checking if Edge is running with debugging enabled...")

        # Check if Edge is already running with debugging
        debug_port = self._find_edge_debug_port()

        if not debug_port:
            logger.warning("  Edge not running with debugging enabled")
            logger.info("  Attempting to start Edge with debugging...")

            # Pass URL so Edge opens directly to the target page
            if not self._start_edge_with_debugging(port, url=url):
                logger.error("=" * 60)
                logger.error("COULD NOT CONNECT TO EDGE BROWSER")
                logger.error("=" * 60)
                logger.error("Please do ONE of the following:")
                logger.error("")
                logger.error("OPTION 1: Close ALL Edge windows, then try again")
                logger.error("          (This allows Edge to restart with debugging)")
                logger.error("")
                logger.error("OPTION 2: Start Edge manually with debugging:")
                logger.error('          1. Open Command Prompt')
                logger.error('          2. Run: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222')
                logger.error("")
                logger.error("OPTION 3: Create a shortcut with debugging flag")
                logger.error("=" * 60)
                return False

            debug_port = port

        self.debugger_url = f'http://localhost:{debug_port}'

        # Get browser version info
        try:
            version_response = requests.get(f'{self.debugger_url}/json/version', timeout=5)
            version_info = version_response.json()
            logger.info(f"  Browser: {version_info.get('Browser', 'Unknown')}")
            logger.info(f"  Protocol: {version_info.get('Protocol-Version', 'Unknown')}")
        except Exception as e:
            logger.warning(f"  Could not get browser version: {e}")

        try:
            # Get list of pages/tabs
            logger.info("")
            logger.info("[STEP 1] Getting browser tabs...")
            response = requests.get(f'{self.debugger_url}/json', timeout=5)
            pages = response.json()

            logger.info(f"  Found {len(pages)} tabs/pages")

            # Log all pages for debugging
            for i, page in enumerate(pages):
                page_type = page.get('type', 'unknown')
                page_title = page.get('title', 'No title')[:40]
                page_url = page.get('url', 'No URL')[:60]
                logger.info(f"    Tab {i+1}: [{page_type}] {page_title}")
                logger.info(f"            URL: {page_url}")

            # Find a suitable page (not DevTools, not extension)
            for page in pages:
                if page.get('type') == 'page' and not page.get('url', '').startswith('devtools://'):
                    self._page_id = page['id']
                    self.ws_url = page['webSocketDebuggerUrl']
                    logger.info("")
                    logger.info(f"  Selected tab: {page.get('title', 'Unknown')[:50]}")
                    logger.info(f"  WebSocket URL: {self.ws_url[:80]}...")
                    self._connected = True
                    logger.info("")
                    logger.info("  CONNECTED SUCCESSFULLY!")
                    logger.info("=" * 60)
                    return True

            # No suitable page found, create one
            logger.info("")
            logger.info("  No suitable page found, creating new tab...")
            response = requests.get(f'{self.debugger_url}/json/new?about:blank', timeout=5)
            page = response.json()
            self._page_id = page['id']
            self.ws_url = page['webSocketDebuggerUrl']
            self._connected = True
            logger.info("  Created new tab and connected")
            logger.info("=" * 60)
            return True

        except requests.exceptions.ConnectionError as e:
            logger.error(f"  Connection refused - Edge debugging not available")
            logger.error(f"  Error: {e}")
            return False
        except Exception as e:
            logger.error(f"  Failed to connect: {e}")
            logger.exception("Full traceback:")
            return False

    def _execute_js(self, js_code: str) -> Any:
        """
        Execute JavaScript in the connected browser page.
        Uses CDP (Chrome DevTools Protocol) via WebSocket.
        """
        if not self._connected:
            raise RuntimeError("Not connected to browser. Call connect_to_browser() first.")

        if not WEBSOCKET_AVAILABLE:
            raise RuntimeError("websocket-client not installed. Run: pip install websocket-client")

        logger.info("[JS] Connecting to WebSocket...")

        try:
            ws = websocket.create_connection(self.ws_url, timeout=30)
            logger.info("[JS] WebSocket connected")

            # Send evaluate command
            command = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_code,
                    "returnByValue": True,
                    "awaitPromise": True
                }
            }

            logger.info(f"[JS] Sending command (code length: {len(js_code)} chars)...")
            ws.send(json.dumps(command))

            # Get response
            logger.info("[JS] Waiting for response...")
            while True:
                response = ws.recv()
                result = json.loads(response)

                if result.get('id') == 1:
                    ws.close()
                    logger.info("[JS] WebSocket closed")

                    if 'error' in result:
                        error_msg = result['error'].get('message', 'Unknown error')
                        logger.error(f"[JS] Error from browser: {error_msg}")
                        raise Exception(error_msg)

                    # Extract result value
                    result_obj = result.get('result', {}).get('result', {})
                    value = result_obj.get('value')

                    if result_obj.get('type') == 'undefined':
                        logger.warning("[JS] Result is undefined")
                        return None

                    logger.info(f"[JS] Got result (type: {result_obj.get('type', 'unknown')})")
                    return value

        except websocket.WebSocketTimeoutException:
            logger.error("[JS] WebSocket timeout - browser not responding")
            raise RuntimeError("Browser not responding (timeout)")
        except websocket.WebSocketConnectionClosedException:
            logger.error("[JS] WebSocket connection closed unexpectedly")
            self._connected = False
            raise RuntimeError("Browser connection lost")
        except Exception as e:
            logger.error(f"[JS] JavaScript execution failed: {e}")
            logger.exception("Full traceback:")
            raise

    def _send_cdp_command(self, method: str, params: dict = None) -> Any:
        """
        Send a Chrome DevTools Protocol command via WebSocket.

        Args:
            method: CDP method name (e.g., "Input.dispatchMouseEvent")
            params: Parameters for the command

        Returns:
            Result from the command
        """
        logger.info(f"[CDP] Sending command: {method}")

        if not self._connected:
            logger.error("[CDP] Not connected to browser")
            raise RuntimeError("Not connected to browser")

        if not WEBSOCKET_AVAILABLE:
            logger.error("[CDP] websocket-client not installed")
            raise RuntimeError("websocket-client not installed")

        ws = None
        try:
            logger.info(f"[CDP] Creating WebSocket connection to {self.ws_url[:60]}...")
            ws = websocket.create_connection(self.ws_url, timeout=5)
            logger.info("[CDP] WebSocket connected")

            command = {
                "id": 1,
                "method": method,
                "params": params or {}
            }

            logger.info(f"[CDP] Sending: {method}")
            ws.send(json.dumps(command))

            logger.info("[CDP] Waiting for response...")
            response = ws.recv()
            result = json.loads(response)

            logger.info(f"[CDP] Got response, closing WebSocket")
            ws.close()
            ws = None

            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"[CDP] Command error: {error_msg}")
                raise Exception(error_msg)

            logger.info(f"[CDP] Command {method} successful")
            return result.get('result', {})

        except websocket.WebSocketTimeoutException:
            logger.error(f"[CDP] Timeout waiting for {method}")
            if ws:
                try:
                    ws.close()
                except:
                    pass
            raise RuntimeError(f"CDP timeout: {method}")
        except Exception as e:
            logger.error(f"[CDP] Command {method} failed: {e}")
            if ws:
                try:
                    ws.close()
                except:
                    pass
            raise

    def execute_pre_extraction_actions(self, actions: List[Dict[str, Any]]) -> bool:
        """
        Execute pre-extraction actions before data extraction.
        Supports click_coordinates, wait, scroll, etc.
        Uses pyautogui for reliable physical mouse clicks.

        Args:
            actions: List of action dictionaries

        Returns:
            True if all actions executed successfully
        """
        if not actions:
            logger.info("[PRE-ACTIONS] No pre-extraction actions to execute")
            return True

        logger.info("")
        logger.info(f"[PRE-ACTIONS] Executing {len(actions)} pre-extraction action(s)...")

        # Import pyautogui for reliable clicking
        try:
            import pyautogui
            pyautogui.FAILSAFE = False  # Disable fail-safe for automation
            USE_PYAUTOGUI = True
            logger.info("  Using pyautogui for mouse actions")
        except ImportError:
            USE_PYAUTOGUI = False
            logger.warning("  pyautogui not available, using CDP commands")

        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            logger.info(f"  Action {i}/{len(actions)}: {action_type}")

            try:
                if action_type == 'click_coordinates':
                    x = action.get('x', 0)
                    y = action.get('y', 0)
                    logger.info(f"    🖱️ Clicking at coordinates ({x}, {y})...")

                    if USE_PYAUTOGUI:
                        # Use pyautogui for reliable physical click
                        # Move to position first, then click with explicit down/up
                        logger.info(f"    Moving mouse to ({x}, {y})...")
                        pyautogui.moveTo(x, y, duration=0.1)
                        time.sleep(0.1)  # Small delay after move

                        logger.info(f"    Performing click...")
                        pyautogui.mouseDown(button='left')
                        time.sleep(0.05)  # Brief hold
                        pyautogui.mouseUp(button='left')

                        logger.info(f"    ✓ Click executed via pyautogui at ({x}, {y})")
                    else:
                        # Fallback to CDP commands
                        self._send_cdp_command("Input.dispatchMouseEvent", {
                            "type": "mousePressed",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1
                        })
                        self._send_cdp_command("Input.dispatchMouseEvent", {
                            "type": "mouseReleased",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1
                        })
                        logger.info(f"    ✓ Click executed via CDP at ({x}, {y})")

                    # Wait after click if specified
                    wait_after = action.get('wait_after', 0)
                    if wait_after > 0:
                        logger.info(f"    ⏳ Waiting {wait_after}s after click...")
                        time.sleep(wait_after)
                        logger.info(f"    ✓ Wait complete")

                elif action_type == 'click_selector':
                    selector = action.get('selector', '')
                    logger.info(f"    Clicking element: {selector}")

                    # Use JavaScript to click element
                    js_code = f"""
                    (() => {{
                        const element = document.querySelector("{selector}");
                        if (element) {{
                            element.click();
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    result = self._execute_js(js_code)
                    if result:
                        logger.info(f"    Clicked element: {selector}")
                    else:
                        logger.warning(f"    Element not found: {selector}")

                    wait_after = action.get('wait_after', 0)
                    if wait_after > 0:
                        logger.info(f"    Waiting {wait_after}s after click...")
                        time.sleep(wait_after)

                elif action_type == 'wait':
                    wait_time = action.get('seconds', action.get('wait_after', 1))
                    logger.info(f"    Waiting {wait_time}s...")
                    time.sleep(wait_time)

                elif action_type == 'scroll':
                    direction = action.get('direction', 'down')
                    amount = action.get('amount', 300)
                    logger.info(f"    Scrolling {direction} by {amount}px...")

                    scroll_y = amount if direction == 'down' else -amount
                    js_code = f"window.scrollBy(0, {scroll_y})"
                    self._execute_js(js_code)

                    wait_after = action.get('wait_after', 0)
                    if wait_after > 0:
                        time.sleep(wait_after)

                elif action_type == 'type_text':
                    selector = action.get('selector', '')
                    text = action.get('text', '')
                    logger.info(f"    Typing into {selector}: {text[:20]}...")

                    js_code = f"""
                    (() => {{
                        const element = document.querySelector("{selector}");
                        if (element) {{
                            element.value = "{text}";
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    self._execute_js(js_code)

                    wait_after = action.get('wait_after', 0)
                    if wait_after > 0:
                        time.sleep(wait_after)

                else:
                    logger.warning(f"    Unknown action type: {action_type}")

            except Exception as e:
                logger.error(f"    Action {i} failed: {e}")
                # Continue with other actions instead of failing completely
                continue

        logger.info("[PRE-ACTIONS] All actions completed")
        return True

    def navigate_to(self, url: str, wait_time: int = 2) -> bool:
        """
        Navigate current page to URL.

        Args:
            url: URL to navigate to
            wait_time: Seconds to wait after navigation

        Returns:
            True if navigation successful
        """
        logger.info(f"[NAV] Navigating to: {url}")

        if not WEBSOCKET_AVAILABLE:
            logger.error("[NAV] websocket-client not installed!")
            return False

        try:
            ws = websocket.create_connection(self.ws_url, timeout=30)

            # Send navigate command
            command = {
                "id": 1,
                "method": "Page.navigate",
                "params": {
                    "url": url
                }
            }

            ws.send(json.dumps(command))

            # Wait for response
            response = ws.recv()
            result = json.loads(response)
            ws.close()

            if 'error' in result:
                logger.error(f"[NAV] Navigation failed: {result['error']}")
                return False

            # Wait for page to load - use at least 5 seconds for complex pages
            actual_wait = max(wait_time, 5)
            logger.info(f"[NAV] Waiting {actual_wait}s for page to fully load...")
            time.sleep(actual_wait)

            logger.info("[NAV] Navigation complete")
            return True

        except Exception as e:
            logger.error(f"[NAV] Navigation failed: {e}")
            return False

    def get_current_url(self) -> str:
        """Get current page URL"""
        try:
            return self._execute_js("window.location.href")
        except:
            return "Unknown"

    def extract_data(
        self,
        url: str,
        selectors: Dict[str, str],
        wait_for_selector: str = None,
        wait_time: int = 2,
        pre_extraction_actions: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract data from page using CSS selectors.

        Args:
            url: Page URL to navigate to
            selectors: Dict of {field_name: css_selector}
                      Must include 'container' selector for item wrapper
            wait_for_selector: Optional selector to wait for before extraction
            wait_time: Additional seconds to wait for dynamic content
            pre_extraction_actions: List of actions to execute before extraction

        Returns:
            List of extracted data dictionaries
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("DOM EXTRACTION")
        logger.info("=" * 60)
        logger.info(f"URL: {url or 'Current page'}")
        logger.info(f"Container selector: {selectors.get('container', 'NOT SET')}")
        logger.info(f"Field selectors: {[k for k in selectors.keys() if k != 'container']}")
        logger.info(f"Wait time: {wait_time}s")
        logger.info(f"Wait for selector: {wait_for_selector or 'None'}")
        logger.info(f"Pre-extraction actions: {len(pre_extraction_actions or [])} action(s)")

        # Connect if not connected - pass URL so Edge opens to correct page if launching
        logger.info("")
        logger.info("[STEP 1] Checking browser connection...")
        if not self._connected:
            logger.info("  Not connected, attempting to connect...")
            if not self.connect_to_browser(url=url):
                raise RuntimeError("Could not connect to browser")
        else:
            logger.info("  Already connected")

        try:
            # Navigate to URL if needed
            logger.info("")
            logger.info("[STEP 2] Checking current page...")
            current_url = self.get_current_url()
            logger.info(f"  Current URL: {current_url[:80] if current_url else 'Unknown'}...")

            if url and url != current_url:
                logger.info(f"  Need to navigate to target URL")
                self.navigate_to(url, wait_time)
            else:
                logger.info("  Already on target page")

            # Execute pre-extraction actions
            logger.info("")
            logger.info("[STEP 3] Pre-extraction actions...")
            if pre_extraction_actions:
                self.execute_pre_extraction_actions(pre_extraction_actions)
            else:
                logger.info("  No pre-extraction actions configured")

            # Wait for specific element if provided
            if wait_for_selector:
                logger.info("")
                logger.info(f"[STEP 4] Waiting for selector: {wait_for_selector}")
                wait_js = f"""
                new Promise((resolve) => {{
                    const checkElement = () => {{
                        if (document.querySelector("{wait_for_selector}")) {{
                            resolve(true);
                        }} else {{
                            setTimeout(checkElement, 100);
                        }}
                    }};
                    setTimeout(() => resolve(false), 10000);  // 10s timeout
                    checkElement();
                }})
                """
                result = self._execute_js(wait_js)
                logger.info(f"  Wait result: {result}")

            # Additional wait for dynamic content
            if wait_time > 0:
                logger.info("")
                logger.info(f"[STEP 5] Waiting {wait_time}s for dynamic content...")
                time.sleep(wait_time)

            # Extract data using JavaScript
            logger.info("")
            logger.info("[STEP 6] Extracting data with JavaScript...")
            extracted_data = self._extract_with_selectors(selectors)

            logger.info("")
            logger.info(f"EXTRACTION COMPLETE: {len(extracted_data)} items found")
            logger.info("=" * 60)
            logger.info("")

            return extracted_data

        except Exception as e:
            logger.error("")
            logger.error("=" * 60)
            logger.error("DOM EXTRACTION FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {e}")
            logger.exception("Full traceback:")
            raise

    def extract_from_current_page(
        self,
        selectors: Dict[str, str],
        wait_time: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Extract data from current page without navigation.

        Args:
            selectors: Dict of {field_name: css_selector}
            wait_time: Additional seconds to wait

        Returns:
            List of extracted data dictionaries
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("DOM EXTRACTION (Current Page)")
        logger.info("=" * 60)
        logger.info(f"Container selector: {selectors.get('container', 'NOT SET')}")
        logger.info(f"Field selectors: {[k for k in selectors.keys() if k != 'container']}")

        # Connect if not connected
        logger.info("")
        logger.info("[STEP 1] Checking browser connection...")
        if not self._connected:
            logger.info("  Not connected, attempting to connect...")
            if not self.connect_to_browser():
                raise RuntimeError("Could not connect to browser")
        else:
            logger.info("  Already connected")

        try:
            logger.info("")
            logger.info("[STEP 2] Getting current page URL...")
            current_url = self.get_current_url()
            logger.info(f"  Current URL: {current_url[:80] if current_url else 'Unknown'}...")

            if wait_time > 0:
                logger.info("")
                logger.info(f"[STEP 3] Waiting {wait_time}s for dynamic content...")
                time.sleep(wait_time)

            # Extract data
            logger.info("")
            logger.info("[STEP 4] Extracting data with JavaScript...")
            extracted_data = self._extract_with_selectors(selectors)

            logger.info("")
            logger.info(f"EXTRACTION COMPLETE: {len(extracted_data)} items found")
            logger.info("=" * 60)
            logger.info("")

            return extracted_data

        except Exception as e:
            logger.error("")
            logger.error("=" * 60)
            logger.error("DOM EXTRACTION FAILED")
            logger.error("=" * 60)
            logger.error(f"Error: {e}")
            logger.exception("Full traceback:")
            raise

    def _extract_with_selectors(self, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Execute JavaScript to extract data from page.

        Args:
            selectors: Dict with 'container' and field selectors

        Returns:
            List of data dictionaries
        """
        # Build JavaScript extraction function
        selectors_json = json.dumps(selectors)

        js_code = f"""
        (() => {{
            const selectors = {selectors_json};
            const results = [];

            // Find container elements (each data item/row)
            const containers = document.querySelectorAll(selectors.container);

            console.log('Found', containers.length, 'containers matching:', selectors.container);

            containers.forEach((container, index) => {{
                const item = {{}};
                console.log(`Processing container ${{index + 1}}/${{containers.length}}`);

                // Extract each field from the container
                for (const [fieldName, selector] of Object.entries(selectors)) {{
                    if (fieldName === 'container') continue;

                    const element = container.querySelector(selector);
                    if (element) {{
                        // Get text content, handle different element types
                        let value = '';
                        if (element.tagName === 'INPUT') {{
                            value = element.value;
                        }} else if (element.tagName === 'IMG') {{
                            value = element.src || element.alt;
                        }} else {{
                            // Try to get ONLY direct text nodes first (avoids nested duplicates)
                            let directText = '';
                            for (let node of element.childNodes) {{
                                if (node.nodeType === Node.TEXT_NODE) {{
                                    const text = node.textContent.trim();
                                    if (text) directText += text + ' ';
                                }}
                            }}

                            if (directText.trim()) {{
                                // Use direct text only
                                value = directText.trim();
                            }} else {{
                                // Fallback: get all text but deduplicate
                                value = element.textContent.trim();

                                // Check if the value appears to be duplicated (same text twice)
                                const halfLen = Math.floor(value.length / 2);
                                if (halfLen > 10) {{
                                    const firstHalf = value.substring(0, halfLen).trim();
                                    const secondHalf = value.substring(halfLen).trim();

                                    // If first and second half are very similar, use just the first half
                                    if (firstHalf === secondHalf) {{
                                        value = firstHalf;
                                        console.log(`  Deduplicated ${{fieldName}}: "${{value.substring(0,30)}}..."`);
                                    }}
                                }}
                            }}
                        }}
                        item[fieldName] = value;
                        console.log(`  ${{fieldName}}: "${{value.substring(0, 50)}}${{value.length > 50 ? '...' : ''}}"`);
                    }} else {{
                        item[fieldName] = '';
                        console.log(`  ${{fieldName}}: (not found with selector "${{selector}}")`);
                    }}
                }}

                // Only add item if it has at least one non-empty field
                const hasData = Object.values(item).some(v => v && v.trim && v.trim());
                if (hasData) {{
                    results.push(item);
                    console.log(`  ✓ Added item ${{results.length}}`);
                }} else {{
                    console.log(`  ✗ Skipped (empty item)`);
                }}
            }});

            console.log(`Total extracted: ${{results.length}} items`);
            return results;
        }})()
        """

        # Execute extraction
        logger.info("  Executing JavaScript extraction...")
        extracted_data = self._execute_js(js_code)

        if extracted_data is None:
            extracted_data = []

        # Post-process extracted data to clean up common issues
        extracted_data = self._post_process_data(extracted_data)

        # Log results
        for i, item in enumerate(extracted_data[:5], 1):  # Log first 5
            logger.info(f"\n  Item {i}:")
            for key, value in item.items():
                # Truncate long values for logging
                display_value = str(value)[:50] + '...' if len(str(value)) > 50 else value
                logger.info(f"    {key}: {display_value}")

        if len(extracted_data) > 5:
            logger.info(f"\n  ... and {len(extracted_data) - 5} more items")

        return extracted_data

    def _post_process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post-process extracted data to clean up common issues.

        Handles:
        - Timestamp fields with "Name • time" pattern → extracts just the time
        - Removes duplicate data between fields
        - Deduplicates text that appears twice in the same field

        Args:
            data: List of extracted data dictionaries

        Returns:
            Cleaned data list
        """
        import re

        if not data:
            return data

        logger.info("[POST-PROCESS] Cleaning extracted data...")

        # Fields that typically contain timestamps
        timestamp_fields = ['date', 'time', 'timestamp', 'datetime', 'created', 'updated']

        for item in data:
            # Get customer/name value if it exists (to detect duplicates in other fields)
            customer_value = None
            for key in ['customer', 'name', 'user', 'author']:
                if key in item and item[key]:
                    customer_value = item[key].strip()
                    break

            # Clean ALL fields for duplicated text
            for field, value in item.items():
                if not value or not isinstance(value, str):
                    continue

                original_value = value
                cleaned_value = self._deduplicate_text(value)

                if cleaned_value != original_value:
                    logger.info(f"  Deduplicated {field}: '{original_value[:40]}...' -> '{cleaned_value[:40]}...'")
                    item[field] = cleaned_value

            # Clean timestamp fields (after deduplication)
            for field in timestamp_fields:
                if field in item and item[field]:
                    original_value = item[field]
                    cleaned_value = self._clean_timestamp_field(original_value, customer_value)
                    if cleaned_value != original_value:
                        logger.info(f"  Cleaned {field}: '{original_value[:40]}...' -> '{cleaned_value}'")
                        item[field] = cleaned_value

        logger.info("[POST-PROCESS] Data cleaning complete")
        return data

    def _deduplicate_text(self, value: str) -> str:
        """
        Remove duplicated text from a string.

        Handles cases where text appears twice, like:
        "Some description text Some description text" -> "Some description text"

        Args:
            value: The text to deduplicate

        Returns:
            Deduplicated text
        """
        import re

        if not value or len(value) < 10:
            return value

        value = value.strip()

        # Method 1: Check if the text is exactly duplicated (same text twice)
        half_len = len(value) // 2
        first_half = value[:half_len].strip()
        second_half = value[half_len:].strip()

        if first_half == second_half:
            return first_half

        # Method 2: Split by multiple spaces or newlines and check for duplicates
        parts = re.split(r'\s{2,}|\n', value)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) == 2 and parts[0] == parts[1]:
            return parts[0]

        # Method 3: Check if second half starts with first half (off-by-one errors)
        if len(first_half) > 10 and second_half.startswith(first_half[:20]):
            return first_half

        # Method 4: Find repeating substring pattern
        # Try different split points around the middle
        for offset in range(-5, 6):
            split_point = half_len + offset
            if split_point < 5 or split_point >= len(value) - 5:
                continue
            left = value[:split_point].strip()
            right = value[split_point:].strip()
            if left == right:
                return left

        # Method 5: Check if string contains itself (substring match)
        # Find if there's a repeating pattern
        for i in range(10, len(value) // 2 + 1):
            pattern = value[:i]
            # Check if rest of string starts with this pattern
            remaining = value[i:].strip()
            if remaining == pattern or remaining.startswith(pattern + ' ') or remaining.startswith(pattern):
                # Verify it's actually a full repeat
                if pattern.strip() == remaining.strip()[:len(pattern)].strip():
                    return pattern.strip()

        return value

    def _clean_timestamp_field(self, value: str, customer_name: str = None) -> str:
        """
        Clean a timestamp field by removing name prefixes.

        Patterns handled:
        - "Name • 12:05pm Dec 1, 2025" -> "12:05pm Dec 1, 2025"
        - "Name · timestamp" -> "timestamp"
        - "Name - timestamp" -> "timestamp"

        Args:
            value: The raw timestamp value
            customer_name: Optional customer name to strip

        Returns:
            Cleaned timestamp string
        """
        import re

        if not value:
            return value

        original = value.strip()

        # Pattern 1: Remove "Name • " prefix (bullet point separator)
        # Matches: "Georgia K. • 12:05pm Dec 1, 2025"
        bullet_pattern = r'^[^•·\-]+[•·]\s*(.+)$'
        match = re.match(bullet_pattern, original)
        if match:
            return match.group(1).strip()

        # Pattern 2: Remove "Name - " prefix (dash separator)
        # Only if it looks like there's a timestamp after
        dash_pattern = r'^[^-]+ - (\d{1,2}:\d{2}.*)$'
        match = re.match(dash_pattern, original)
        if match:
            return match.group(1).strip()

        # Pattern 3: If customer name provided, try to strip it directly
        if customer_name and original.startswith(customer_name):
            remainder = original[len(customer_name):].strip()
            # Remove leading separators
            remainder = re.sub(r'^[•·\-\s]+', '', remainder)
            if remainder:
                return remainder

        return original

    def test_selector(self, selector: str) -> Dict[str, Any]:
        """
        Test a CSS selector on current page.

        Args:
            selector: CSS selector to test

        Returns:
            Dict with count and sample text
        """
        logger.info(f"Testing selector: {selector}")

        # Connect if not connected
        if not self._connected:
            if not self.connect_to_browser():
                return {'success': False, 'error': 'Could not connect to browser'}

        try:
            js_code = f"""
            (() => {{
                const elements = document.querySelectorAll("{selector}");
                const samples = [];

                for (let i = 0; i < Math.min(elements.length, 3); i++) {{
                    samples.push(elements[i].textContent.trim().substring(0, 100));
                }}

                return {{
                    count: elements.length,
                    samples: samples
                }};
            }})()
            """

            result = self._execute_js(js_code)

            if result is None:
                return {'success': False, 'error': 'No result from browser'}

            logger.info(f"  Found {result['count']} elements")
            for i, sample in enumerate(result['samples'], 1):
                logger.info(f"  Sample {i}: {sample}")

            return {
                'success': True,
                'count': result['count'],
                'samples': result['samples']
            }

        except Exception as e:
            logger.error(f"  Selector test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def test_field_selector(
        self,
        container_selector: str,
        field_selector: str,
        field_name: str
    ) -> Dict[str, Any]:
        """
        Test a field selector within containers.

        Args:
            container_selector: CSS selector for containers
            field_selector: CSS selector for field (relative to container)
            field_name: Name of the field

        Returns:
            Dict with results
        """
        logger.info(f"Testing field '{field_name}': {field_selector}")

        if not self._connected:
            if not self.connect_to_browser():
                return {'success': False, 'error': 'Could not connect to browser'}

        try:
            js_code = f"""
            (() => {{
                const containers = document.querySelectorAll("{container_selector}");
                const samples = [];
                let foundCount = 0;

                containers.forEach((container, i) => {{
                    const element = container.querySelector("{field_selector}");
                    if (element) {{
                        foundCount++;
                        if (samples.length < 5) {{
                            samples.push(element.textContent.trim().substring(0, 100));
                        }}
                    }}
                }});

                return {{
                    container_count: containers.length,
                    found_count: foundCount,
                    samples: samples
                }};
            }})()
            """

            result = self._execute_js(js_code)

            if result is None:
                return {'success': False, 'error': 'No result from browser'}

            logger.info(f"  Found in {result['found_count']}/{result['container_count']} containers")

            return {
                'success': True,
                'container_count': result['container_count'],
                'found_count': result['found_count'],
                'samples': result['samples']
            }

        except Exception as e:
            logger.error(f"  Field test failed: {e}")
            return {'success': False, 'error': str(e)}

    def get_page_info(self) -> Dict[str, Any]:
        """Get information about current page"""
        try:
            if not self._connected:
                return {'url': 'Not connected', 'title': 'Not connected'}

            url = self._execute_js("window.location.href")
            title = self._execute_js("document.title")

            return {
                'url': url or 'Unknown',
                'title': title or 'Unknown'
            }
        except Exception as e:
            return {
                'url': 'Error',
                'title': str(e)
            }

    def close(self):
        """Close connection (but not the browser)"""
        logger.info("Closing DOMExtractor connection...")
        self._connected = False
        self.ws_url = None
        self._page_id = None
        logger.info("  DOMExtractor closed (browser still running)")
