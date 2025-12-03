"""
Configuration settings for Automation Platform
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.resolve()
DATABASE_DIR = BASE_DIR / "database"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
LOGS_DIR = BASE_DIR / "logs"

# Database
DATABASE_PATH = DATABASE_DIR / "automation.db"

# Flask settings
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# OCR settings
OCR_LANGUAGES = ['en']
OCR_GPU = False
MIN_CONFIDENCE = 0.85

# Pagination/Scrolling defaults
DEFAULT_SCROLL_PIXELS = 500
DEFAULT_SCROLL_WAIT = 2.0
DEFAULT_MAX_SCROLLS = 50
DEFAULT_MAX_PAGES = 100
DEFAULT_PAGE_WAIT = 3.0

# Data retention
DEFAULT_RETENTION_DAYS = 30

# Logging
LOG_FORMAT = '[%(asctime)s] %(levelname)s [%(name)s]: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
