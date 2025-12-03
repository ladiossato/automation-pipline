"""
Database Utility Module
Provides all database operations with extensive logging
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_PATH, LOG_FORMAT, LOG_DATE_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


class Database:
    """Database wrapper with extensive logging for all operations"""

    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        logger.info(f"Initializing Database connection")
        logger.info(f"  Path: {self.db_path}")

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect with row factory for dict-like access
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        logger.info("  ✓ Database connection established")

    def _log_query(self, operation: str, query: str, params: tuple = None):
        """Log database queries at debug level"""
        logger.debug(f"  SQL [{operation}]: {query[:100]}...")
        if params:
            logger.debug(f"  Params: {params}")

    # ==================== JOB OPERATIONS ====================

    def create_job(self, job_data: Dict[str, Any]) -> int:
        """
        Create a new job configuration

        Args:
            job_data: dict with job configuration

        Returns:
            int: new job ID
        """
        logger.info("=" * 50)
        logger.info("CREATE JOB")
        logger.info("=" * 50)
        logger.info(f"  Name: {job_data.get('name')}")
        logger.info(f"  URL: {job_data.get('url')}")

        cursor = self.conn.cursor()

        # Serialize JSON fields
        ocr_regions = json.dumps(job_data.get('ocr_regions', []))
        scroll_config = json.dumps(job_data.get('scroll_config', {}))
        pagination_config = json.dumps(job_data.get('pagination_config', {}))
        pre_extraction_actions = json.dumps(job_data.get('pre_extraction_actions', []))
        csv_config = json.dumps(job_data.get('csv_config', {}))
        dom_config = json.dumps(job_data.get('dom_config', {}))

        query = """
            INSERT INTO jobs (
                name, url, ocr_regions, format_template,
                telegram_bot_token, telegram_chat_id,
                page_mode, scroll_config, pagination_config,
                pre_extraction_actions, job_type, csv_config, dom_config,
                enable_deduplication, data_retention_days,
                schedule_interval_hours, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            job_data.get('name'),
            job_data.get('url'),
            ocr_regions,
            job_data.get('format_template', ''),
            job_data.get('telegram_bot_token'),
            job_data.get('telegram_chat_id'),
            job_data.get('page_mode', 'single'),
            scroll_config,
            pagination_config,
            pre_extraction_actions,
            job_data.get('job_type', 'ocr_extraction'),
            csv_config,
            dom_config,
            job_data.get('enable_deduplication', True),
            job_data.get('data_retention_days', 30),
            job_data.get('schedule_interval_hours', 1),
            job_data.get('active', False)
        )

        try:
            cursor.execute(query, params)
            self.conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"  ✓ Job created with ID: {job_id}")
            logger.info("=" * 50)
            return job_id
        except sqlite3.IntegrityError as e:
            logger.error(f"  ⚠ Job creation failed: {e}")
            raise

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job by ID with parsed JSON fields"""
        logger.info(f"Getting job ID: {job_id}")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"  ⚠ Job {job_id} not found")
            return None

        job = dict(row)
        # Parse JSON fields
        job['ocr_regions'] = json.loads(job['ocr_regions'] or '[]')
        job['scroll_config'] = json.loads(job['scroll_config'] or '{}')
        job['pagination_config'] = json.loads(job['pagination_config'] or '{}')
        job['pre_extraction_actions'] = json.loads(job.get('pre_extraction_actions') or '[]')
        job['csv_config'] = json.loads(job.get('csv_config') or '{}')
        job['dom_config'] = json.loads(job.get('dom_config') or '{}')

        logger.info(f"  ✓ Found: {job['name']}")
        return job

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs"""
        logger.info("Getting all jobs")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = cursor.fetchall()

        jobs = []
        for row in rows:
            job = dict(row)
            job['ocr_regions'] = json.loads(job['ocr_regions'] or '[]')
            job['scroll_config'] = json.loads(job['scroll_config'] or '{}')
            job['pagination_config'] = json.loads(job['pagination_config'] or '{}')
            job['pre_extraction_actions'] = json.loads(job.get('pre_extraction_actions') or '[]')
            job['csv_config'] = json.loads(job.get('csv_config') or '{}')
            job['dom_config'] = json.loads(job.get('dom_config') or '{}')
            jobs.append(job)

        logger.info(f"  ✓ Found {len(jobs)} jobs")
        return jobs

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active jobs for scheduling"""
        logger.info("Getting active jobs")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE active = 1 ORDER BY id")
        rows = cursor.fetchall()

        jobs = []
        for row in rows:
            job = dict(row)
            job['ocr_regions'] = json.loads(job['ocr_regions'] or '[]')
            job['scroll_config'] = json.loads(job['scroll_config'] or '{}')
            job['pagination_config'] = json.loads(job['pagination_config'] or '{}')
            job['pre_extraction_actions'] = json.loads(job.get('pre_extraction_actions') or '[]')
            job['csv_config'] = json.loads(job.get('csv_config') or '{}')
            job['dom_config'] = json.loads(job.get('dom_config') or '{}')
            jobs.append(job)

        logger.info(f"  ✓ Found {len(jobs)} active jobs")
        return jobs

    def update_job(self, job_id: int, job_data: Dict[str, Any]) -> bool:
        """Update job configuration"""
        logger.info(f"Updating job ID: {job_id}")

        # Build dynamic update query
        fields = []
        params = []

        for key, value in job_data.items():
            if key in ['ocr_regions', 'scroll_config', 'pagination_config', 'pre_extraction_actions', 'csv_config', 'dom_config']:
                value = json.dumps(value)
            fields.append(f"{key} = ?")
            params.append(value)

        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(job_id)

        query = f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?"

        cursor = self.conn.cursor()
        cursor.execute(query, tuple(params))
        self.conn.commit()

        logger.info(f"  ✓ Job {job_id} updated ({cursor.rowcount} rows)")
        return cursor.rowcount > 0

    def delete_job(self, job_id: int) -> bool:
        """Delete job and all related data"""
        logger.info(f"Deleting job ID: {job_id}")

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self.conn.commit()

        logger.info(f"  ✓ Job {job_id} deleted ({cursor.rowcount} rows)")
        return cursor.rowcount > 0

    def update_job_last_run(self, job_id: int, next_run: datetime = None):
        """Update job's last_run and next_run timestamps"""
        logger.info(f"Updating last_run for job {job_id}")

        now = datetime.now().isoformat()
        next_run_str = next_run.isoformat() if next_run else None

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE jobs SET last_run = ?, next_run = ? WHERE id = ?",
            (now, next_run_str, job_id)
        )
        self.conn.commit()
        logger.info(f"  ✓ Timestamps updated")

    # ==================== EXTRACTED DATA OPERATIONS ====================

    def store_extracted_data(
        self,
        job_id: int,
        data: Dict[str, Any],
        data_hash: str,
        page_number: int = 1,
        scroll_position: int = 0
    ) -> int:
        """
        Store extracted data with hash for deduplication

        Returns:
            int: new record ID
        """
        logger.info("Storing extracted data")
        logger.info(f"  Job ID: {job_id}")
        logger.info(f"  Hash: {data_hash}")
        logger.info(f"  Data: {data}")

        cursor = self.conn.cursor()

        query = """
            INSERT INTO extracted_data (
                job_id, hash, data, page_number, scroll_position
            ) VALUES (?, ?, ?, ?, ?)
        """

        try:
            cursor.execute(query, (
                job_id,
                data_hash,
                json.dumps(data),
                page_number,
                scroll_position
            ))
            self.conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"  ✓ Data stored with ID: {record_id}")
            return record_id
        except sqlite3.IntegrityError:
            logger.warning(f"  ⚠ Duplicate hash - data already exists")
            return -1

    def is_duplicate(self, job_id: int, data_hash: str) -> bool:
        """Check if hash exists for this job"""
        logger.debug(f"Checking duplicate: job={job_id}, hash={data_hash}")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM extracted_data WHERE job_id = ? AND hash = ? LIMIT 1",
            (job_id, data_hash)
        )
        exists = cursor.fetchone() is not None

        logger.debug(f"  Result: {'DUPLICATE' if exists else 'NEW'}")
        return exists

    def mark_sent_to_telegram(self, record_id: int, message_id: str):
        """Mark record as sent to Telegram"""
        logger.info(f"Marking record {record_id} as sent to Telegram")

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE extracted_data
            SET sent_to_telegram = 1, telegram_message_id = ?, telegram_sent_at = ?
            WHERE id = ?
        """, (message_id, datetime.now().isoformat(), record_id))
        self.conn.commit()
        logger.info(f"  ✓ Marked as sent")

    def get_extracted_data(
        self,
        job_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get extracted data for a job"""
        logger.info(f"Getting extracted data for job {job_id}")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM extracted_data
            WHERE job_id = ?
            ORDER BY extracted_at DESC
            LIMIT ? OFFSET ?
        """, (job_id, limit, offset))

        rows = cursor.fetchall()
        data = []
        for row in rows:
            record = dict(row)
            record['data'] = json.loads(record['data'])
            data.append(record)

        logger.info(f"  ✓ Found {len(data)} records")
        return data

    def cleanup_old_data(self, job_id: int, retention_days: int) -> int:
        """Delete data older than retention period"""
        logger.info(f"Cleaning up old data for job {job_id}")
        logger.info(f"  Retention: {retention_days} days")

        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM extracted_data
            WHERE job_id = ? AND extracted_at < ?
        """, (job_id, cutoff))
        self.conn.commit()

        deleted = cursor.rowcount
        logger.info(f"  ✓ Deleted {deleted} old records")
        return deleted

    # ==================== EXECUTION LOG OPERATIONS ====================

    def start_execution_log(self, job_id: int) -> int:
        """Create new execution log entry"""
        logger.info(f"Starting execution log for job {job_id}")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO execution_log (job_id, started_at, status)
            VALUES (?, ?, 'running')
        """, (job_id, datetime.now().isoformat()))
        self.conn.commit()

        log_id = cursor.lastrowid
        logger.info(f"  ✓ Execution log started: ID {log_id}")
        return log_id

    def complete_execution_log(
        self,
        log_id: int,
        status: str,
        pages_processed: int = 0,
        items_extracted: int = 0,
        items_new: int = 0,
        items_duplicate: int = 0,
        items_sent: int = 0,
        screenshot_path: str = None,
        error_message: str = None,
        console_log: str = None
    ):
        """Complete execution log with results"""
        logger.info(f"Completing execution log {log_id}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Items: extracted={items_extracted}, new={items_new}, dup={items_duplicate}")

        cursor = self.conn.cursor()

        # Calculate duration
        cursor.execute("SELECT started_at FROM execution_log WHERE id = ?", (log_id,))
        row = cursor.fetchone()
        started_at = datetime.fromisoformat(row['started_at'])
        duration = (datetime.now() - started_at).total_seconds()

        cursor.execute("""
            UPDATE execution_log SET
                completed_at = ?,
                duration_seconds = ?,
                status = ?,
                pages_processed = ?,
                items_extracted = ?,
                items_new = ?,
                items_duplicate = ?,
                items_sent = ?,
                screenshot_path = ?,
                error_message = ?,
                console_log = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            duration,
            status,
            pages_processed,
            items_extracted,
            items_new,
            items_duplicate,
            items_sent,
            screenshot_path,
            error_message,
            console_log,
            log_id
        ))
        self.conn.commit()
        logger.info(f"  ✓ Execution log completed (duration: {duration:.1f}s)")

    def store_execution_log(
        self,
        job_id: int,
        status: str,
        items_extracted: int = 0,
        items_new: int = 0,
        items_duplicate: int = 0,
        duration: float = 0,
        error_message: str = None
    ):
        """Quick method to store complete execution log"""
        logger.info(f"Storing execution log for job {job_id}")

        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO execution_log (
                job_id, started_at, completed_at, duration_seconds,
                status, items_extracted, items_new, items_duplicate,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, now, now, duration,
            status, items_extracted, items_new, items_duplicate,
            error_message
        ))
        self.conn.commit()
        logger.info(f"  ✓ Execution log stored")

    def get_execution_logs(
        self,
        job_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution logs for a job"""
        logger.info(f"Getting execution logs for job {job_id}")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM execution_log
            WHERE job_id = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (job_id, limit))

        logs = [dict(row) for row in cursor.fetchall()]
        logger.info(f"  ✓ Found {len(logs)} logs")
        return logs

    # ==================== UTILITY METHODS ====================

    def close(self):
        """Close database connection"""
        logger.info("Closing database connection")
        self.conn.close()
        logger.info("  ✓ Connection closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        logger.info("Getting database statistics")

        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE active = 1")
        active_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM extracted_data")
        total_data = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM execution_log")
        total_logs = cursor.fetchone()[0]

        stats = {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'total_extracted_data': total_data,
            'total_execution_logs': total_logs
        }

        logger.info(f"  Stats: {stats}")
        return stats
