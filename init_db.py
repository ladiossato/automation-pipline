"""
Database Initialization Script
Creates all tables with proper schema for the Automation Platform
"""

import sqlite3
import logging
from pathlib import Path
from config import DATABASE_PATH, LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)

SCHEMA = """
-- Jobs table: stores all job configurations
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,

    -- OCR configuration: JSON array of regions
    -- Format: [{"name": "field1", "x": 100, "y": 200, "width": 300, "height": 50}, ...]
    ocr_regions TEXT DEFAULT '[]',

    -- Message format template
    -- Use {field_name} placeholders, e.g., "New: {symbol} at ${price}"
    format_template TEXT DEFAULT '',

    -- Telegram configuration
    telegram_bot_token TEXT,
    telegram_chat_id TEXT,

    -- Page handling mode: 'single', 'scroll', or 'pagination'
    page_mode TEXT DEFAULT 'single' CHECK(page_mode IN ('single', 'scroll', 'pagination')),

    -- Scroll configuration (JSON)
    -- Format: {"max_scrolls": 50, "wait_time": 2, "scroll_pixels": 500}
    scroll_config TEXT DEFAULT '{"max_scrolls": 50, "wait_time": 2, "scroll_pixels": 500}',

    -- Pagination configuration (JSON)
    -- Format: {"mode": "ocr", "button_text": "Next", "max_pages": 100, "search_region": {...}}
    -- Or: {"mode": "coordinates", "button_x": 500, "button_y": 600, "max_pages": 100}
    pagination_config TEXT DEFAULT '{"mode": "ocr", "button_text": "Next", "max_pages": 100}',

    -- Pre-extraction actions (JSON array)
    -- Format: [{"type": "click_coordinates", "x": 500, "y": 300, "wait_after": 3}, ...]
    -- Or: [{"type": "click_ocr", "search_text": "View Details", "confidence_threshold": 0.8, "wait_after": 2}]
    -- Or: [{"type": "wait", "duration": 5}]
    pre_extraction_actions TEXT DEFAULT '[]',

    -- Job type: 'ocr_extraction', 'csv_analysis', or 'dom_extraction'
    job_type TEXT DEFAULT 'ocr_extraction' CHECK(job_type IN ('ocr_extraction', 'csv_analysis', 'dom_extraction')),

    -- DOM Extraction configuration (JSON)
    -- Format: {
    --   "selectors": {"container": "div.item", "field1": "span.title", "field2": "span.value"},
    --   "wait_for_selector": ".data-loaded",
    --   "wait_time": 2
    -- }
    dom_config TEXT DEFAULT '{}',

    -- CSV Analysis configuration (JSON)
    -- Format: {
    --   "download_actions": [...],
    --   "csv_filename_pattern": "Order History-*.csv",
    --   "threshold_minutes": 10,
    --   "columns": {"datetime": "Fulfilled", "prep_time": "Prep Time", "items": "Items Quantity"},
    --   "active_start_hour": 10,
    --   "active_end_hour": 23
    -- }
    csv_config TEXT DEFAULT '{}',

    -- Deduplication settings
    enable_deduplication INTEGER DEFAULT 1,
    data_retention_days INTEGER DEFAULT 30,

    -- Scheduling
    schedule_interval_hours INTEGER DEFAULT 1,
    active INTEGER DEFAULT 0,
    last_run TEXT,  -- ISO datetime
    next_run TEXT,  -- ISO datetime

    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Extracted data table: stores all extracted data with hashes for deduplication
CREATE TABLE IF NOT EXISTS extracted_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,

    -- MD5 hash of content for deduplication
    hash TEXT NOT NULL,

    -- Extracted data as JSON
    -- Format: {"field1": "value1", "field2": "value2", ...}
    data TEXT NOT NULL,

    -- Extraction metadata
    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    page_number INTEGER DEFAULT 1,
    scroll_position INTEGER DEFAULT 0,

    -- Telegram delivery status
    sent_to_telegram INTEGER DEFAULT 0,
    telegram_message_id TEXT,
    telegram_sent_at TEXT,

    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(job_id, hash)
);

-- Execution log table: tracks every job execution
CREATE TABLE IF NOT EXISTS execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,

    -- Timing
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_seconds REAL,

    -- Status
    status TEXT CHECK(status IN ('running', 'success', 'partial', 'failed')),

    -- Statistics
    pages_processed INTEGER DEFAULT 0,
    items_extracted INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    items_duplicate INTEGER DEFAULT 0,
    items_sent INTEGER DEFAULT 0,

    -- Debugging
    screenshot_path TEXT,
    error_message TEXT,
    console_log TEXT,  -- Full execution log for debugging

    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_extracted_data_job_hash ON extracted_data(job_id, hash);
CREATE INDEX IF NOT EXISTS idx_extracted_data_job_time ON extracted_data(job_id, extracted_at);
CREATE INDEX IF NOT EXISTS idx_execution_log_job ON execution_log(job_id, started_at);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(active);
"""


def init_database():
    """Initialize the database with schema"""
    logger.info("=" * 60)
    logger.info("DATABASE INITIALIZATION")
    logger.info("=" * 60)

    # Ensure directory exists
    db_dir = DATABASE_PATH.parent
    logger.info(f"Database directory: {db_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info("  ✓ Directory verified")

    # Connect and create tables
    logger.info(f"Database path: {DATABASE_PATH}")

    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()
        logger.info("  ✓ Connection established")

        # Execute schema
        logger.info("Creating tables...")
        cursor.executescript(SCHEMA)
        conn.commit()
        logger.info("  ✓ All tables created")

        # Migration: Add new columns if they don't exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'pre_extraction_actions' not in columns:
            logger.info("  Migrating: Adding pre_extraction_actions column...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN pre_extraction_actions TEXT DEFAULT '[]'")
            conn.commit()
            logger.info("  ✓ Migration complete")

        if 'job_type' not in columns:
            logger.info("  Migrating: Adding job_type column...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT 'ocr_extraction'")
            conn.commit()
            logger.info("  ✓ Migration complete")

        if 'csv_config' not in columns:
            logger.info("  Migrating: Adding csv_config column...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN csv_config TEXT DEFAULT '{}'")
            conn.commit()
            logger.info("  ✓ Migration complete")

        if 'dom_config' not in columns:
            logger.info("  Migrating: Adding dom_config column...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN dom_config TEXT DEFAULT '{}'")
            conn.commit()
            logger.info("  ✓ Migration complete")

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"  Tables: {[t[0] for t in tables]}")

        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()
        logger.info(f"  Indexes: {[i[0] for i in indexes]}")

        conn.close()

        logger.info("=" * 60)
        logger.info("DATABASE INITIALIZED SUCCESSFULLY ✓")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"⚠ DATABASE INITIALIZATION FAILED: {e}")
        logger.exception("Full traceback:")
        return False


if __name__ == "__main__":
    init_database()
