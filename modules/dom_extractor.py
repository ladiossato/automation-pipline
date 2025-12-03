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

    def _start_edge_with_debugging(self, port: int = 9222) -> bool:
        """
        Start Edge with remote debugging enabled.
        This allows us to connect to the browser and run JavaScript.
        """
        logger.info(f"Starting Edge with remote debugging on port {port}...")

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

        # User data directory (use existing profile)
        user_data_dir = os.path.join(
            os.path.expanduser('~'),
            'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'
        )

        try:
            # Start Edge with debugging flag
            cmd = [
                edge_exe,
                f'--remote-debugging-port={port}',
                f'--user-data-dir={user_data_dir}',
                '--no-first-run',
            ]

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for Edge to start
            time.sleep(2)

            # Verify it's running
            if self._find_edge_debug_port():
                logger.info("  Edge started with debugging enabled")
                return True
            else:
                logger.error("  Edge started but debugging not available")
                return False

        except Exception as e:
            logger.error(f"  Failed to start Edge: {e}")
            return False

    def connect_to_browser(self, port: int = 9222) -> bool:
        """
        Connect to existing Edge browser via DevTools Protocol.
        If Edge isn't running with debugging, offers to start it.

        Args:
            port: Debug port (default 9222)

        Returns:
            True if connected successfully
        """
        if self._connected:
            logger.info("Already connected to browser")
            return True

        logger.info("Connecting to Edge browser...")

        # Check if Edge is already running with debugging
        debug_port = self._find_edge_debug_port()

        if not debug_port:
            logger.warning("  Edge not running with debugging enabled")
            logger.info("  Starting Edge with debugging...")

            if not self._start_edge_with_debugging(port):
                logger.error("  Could not start Edge with debugging")
                logger.error("  Please close all Edge windows and try again,")
                logger.error("  or start Edge manually with: msedge --remote-debugging-port=9222")
                return False

            debug_port = port

        self.debugger_url = f'http://localhost:{debug_port}'

        try:
            # Get list of pages/tabs
            response = requests.get(f'{self.debugger_url}/json', timeout=5)
            pages = response.json()

            # Find a suitable page (not DevTools, not extension)
            for page in pages:
                if page.get('type') == 'page' and not page.get('url', '').startswith('devtools://'):
                    self._page_id = page['id']
                    self.ws_url = page['webSocketDebuggerUrl']
                    logger.info(f"  Connected to page: {page.get('title', 'Unknown')[:50]}")
                    logger.info(f"  URL: {page.get('url', 'Unknown')[:60]}")
                    self._connected = True
                    return True

            # No suitable page found, create one
            logger.info("  No suitable page found, creating new tab...")
            response = requests.get(f'{self.debugger_url}/json/new?about:blank', timeout=5)
            page = response.json()
            self._page_id = page['id']
            self.ws_url = page['webSocketDebuggerUrl']
            self._connected = True
            logger.info("  Created new tab and connected")
            return True

        except Exception as e:
            logger.error(f"  Failed to connect: {e}")
            return False

    def _execute_js(self, js_code: str) -> Any:
        """
        Execute JavaScript in the connected browser page.
        Uses CDP (Chrome DevTools Protocol) via HTTP.
        """
        if not self._connected:
            raise RuntimeError("Not connected to browser. Call connect_to_browser() first.")

        try:
            # Use the evaluate endpoint
            payload = {
                "expression": js_code,
                "returnByValue": True,
                "awaitPromise": True
            }

            # We need to use WebSocket for this, but for simplicity let's use
            # a different approach - inject via bookmarklet-style

            # Actually, let's use the simpler approach with pychrome or websocket-client
            import websocket
            import json as json_module

            ws = websocket.create_connection(self.ws_url, timeout=30)

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

            ws.send(json_module.dumps(command))

            # Get response
            while True:
                response = ws.recv()
                result = json_module.loads(response)

                if result.get('id') == 1:
                    ws.close()

                    if 'error' in result:
                        raise Exception(result['error'].get('message', 'Unknown error'))

                    return result.get('result', {}).get('result', {}).get('value')

        except ImportError:
            logger.error("websocket-client not installed. Run: pip install websocket-client")
            raise
        except Exception as e:
            logger.error(f"JavaScript execution failed: {e}")
            raise

    def navigate_to(self, url: str, wait_time: int = 2) -> bool:
        """
        Navigate current page to URL.

        Args:
            url: URL to navigate to
            wait_time: Seconds to wait after navigation

        Returns:
            True if navigation successful
        """
        logger.info(f"Navigating to: {url}")

        try:
            import websocket
            import json as json_module

            ws = websocket.create_connection(self.ws_url, timeout=30)

            # Send navigate command
            command = {
                "id": 1,
                "method": "Page.navigate",
                "params": {
                    "url": url
                }
            }

            ws.send(json_module.dumps(command))

            # Wait for response
            response = ws.recv()
            result = json_module.loads(response)
            ws.close()

            if 'error' in result:
                logger.error(f"  Navigation failed: {result['error']}")
                return False

            # Wait for page to load
            logger.info(f"  Waiting {wait_time}s for page load...")
            time.sleep(wait_time)

            logger.info("  Navigation complete")
            return True

        except Exception as e:
            logger.error(f"  Navigation failed: {e}")
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
        wait_time: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extract data from page using CSS selectors.

        Args:
            url: Page URL to navigate to
            selectors: Dict of {field_name: css_selector}
                      Must include 'container' selector for item wrapper
            wait_for_selector: Optional selector to wait for before extraction
            wait_time: Additional seconds to wait for dynamic content

        Returns:
            List of extracted data dictionaries
        """
        logger.info("=" * 60)
        logger.info("DOM EXTRACTION")
        logger.info("=" * 60)
        logger.info(f"URL: {url}")
        logger.info(f"Selectors: {list(selectors.keys())}")

        # Connect if not connected
        if not self._connected:
            if not self.connect_to_browser():
                raise RuntimeError("Could not connect to browser")

        try:
            # Navigate to URL
            if url and url != self.get_current_url():
                self.navigate_to(url, wait_time)
            else:
                logger.info("  Already on target page")

            # Wait for specific element if provided
            if wait_for_selector:
                logger.info(f"  Waiting for selector: {wait_for_selector}")
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
                self._execute_js(wait_js)

            # Additional wait for dynamic content
            if wait_time > 0:
                logger.info(f"  Waiting {wait_time}s for dynamic content...")
                time.sleep(wait_time)

            # Extract data using JavaScript
            logger.info("  Extracting data...")
            extracted_data = self._extract_with_selectors(selectors)

            logger.info(f"\n  Extraction complete: {len(extracted_data)} items")
            logger.info("=" * 60 + "\n")

            return extracted_data

        except Exception as e:
            logger.error(f"DOM extraction failed: {e}")
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
        logger.info("=" * 60)
        logger.info("DOM EXTRACTION (Current Page)")
        logger.info("=" * 60)
        logger.info(f"Selectors: {list(selectors.keys())}")

        # Connect if not connected
        if not self._connected:
            if not self.connect_to_browser():
                raise RuntimeError("Could not connect to browser")

        try:
            current_url = self.get_current_url()
            logger.info(f"  Current URL: {current_url}")

            if wait_time > 0:
                logger.info(f"  Waiting {wait_time}s...")
                time.sleep(wait_time)

            # Extract data
            extracted_data = self._extract_with_selectors(selectors)

            logger.info(f"\n  Extraction complete: {len(extracted_data)} items")
            logger.info("=" * 60 + "\n")

            return extracted_data

        except Exception as e:
            logger.error(f"DOM extraction failed: {e}")
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

            console.log('Found', containers.length, 'containers');

            containers.forEach((container, index) => {{
                const item = {{}};

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
                            value = element.textContent.trim();
                        }}
                        item[fieldName] = value;
                    }} else {{
                        item[fieldName] = '';
                    }}
                }}

                // Only add item if it has at least one non-empty field
                const hasData = Object.values(item).some(v => v && v.trim && v.trim());
                if (hasData) {{
                    results.push(item);
                }}
            }});

            return results;
        }})()
        """

        # Execute extraction
        logger.info("  Executing JavaScript extraction...")
        extracted_data = self._execute_js(js_code)

        if extracted_data is None:
            extracted_data = []

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
