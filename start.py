"""
Startup Script
Launches both the web UI and automation engine
"""

import sys
import io
import subprocess
import webbrowser
import time
import logging
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import FLASK_HOST, FLASK_PORT, LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


def start_application():
    """Start the automation platform"""
    logger.info("=" * 60)
    logger.info("STARTING AUTOMATION PLATFORM")
    logger.info("=" * 60)

    base_path = Path(__file__).parent

    # Start Flask web UI
    logger.info("Starting web UI...")
    flask_process = subprocess.Popen(
        [sys.executable, str(base_path / 'app.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(base_path)
    )
    logger.info(f"  Web UI PID: {flask_process.pid}")

    # Wait for Flask to start
    time.sleep(2)

    # Check if Flask started successfully
    if flask_process.poll() is not None:
        logger.error("Web UI failed to start!")
        output = flask_process.stdout.read().decode('utf-8', errors='replace')
        logger.error(output)
        return

    # Open browser to web UI
    url = f"http://{FLASK_HOST}:{FLASK_PORT}"
    logger.info(f"Opening browser to {url}")
    webbrowser.open(url)

    logger.info("\n" + "=" * 60)
    logger.info("AUTOMATION PLATFORM RUNNING")
    logger.info("=" * 60)
    logger.info(f"  Web UI: {url}")
    logger.info(f"  Logs: logs/engine.log")
    logger.info("")
    logger.info("To run the automation engine in background:")
    logger.info("  python engine.py")
    logger.info("")
    logger.info("Press Ctrl+C to stop the web UI")
    logger.info("=" * 60 + "\n")

    try:
        # Stream Flask output
        while True:
            if flask_process.poll() is not None:
                break

            line = flask_process.stdout.readline()
            if line:
                print(line.decode('utf-8', errors='replace'), end='')

            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        flask_process.terminate()
        flask_process.wait(timeout=5)
        logger.info("Stopped")


def start_web_only():
    """Start only the web UI"""
    logger.info("Starting web UI only...")
    import app
    app.app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)


def start_engine_only():
    """Start only the automation engine"""
    logger.info("Starting automation engine only...")
    from engine import AutomationEngine
    engine = AutomationEngine()
    engine.run_forever()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'web':
            start_web_only()
        elif sys.argv[1] == 'engine':
            start_engine_only()
        else:
            print("Usage:")
            print("  python start.py        - Start web UI with browser")
            print("  python start.py web    - Start web UI only")
            print("  python start.py engine - Start automation engine only")
    else:
        start_application()
