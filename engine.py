"""
Automation Engine
Main execution engine that orchestrates all components
"""

import sys
import io
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from apscheduler.schedulers.background import BackgroundScheduler

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import LOG_FORMAT, LOG_DATE_FORMAT, LOGS_DIR
from modules.database import Database
from modules.browser_control import BrowserController
from modules.ocr_handler import OCRHandler
from modules.deduplicator import Deduplicator
from modules.paginator import Paginator
from modules.telegram_sender import TelegramSender, MessageFormatter
from modules.action_executor import ActionExecutor
from modules.csv_analyzer import CSVAnalyzer
from modules.dom_extractor import DOMExtractor
from init_db import init_database

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / 'engine.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AutomationEngine:
    """Main automation engine that executes jobs"""

    def __init__(self):
        """Initialize all components"""
        logger.info("=" * 70)
        logger.info("AUTOMATION ENGINE STARTING")
        logger.info("=" * 70)

        # Initialize database
        init_database()
        self.db = Database()
        logger.info("  Database initialized")

        # Initialize components (lazy loading for heavy ones)
        self._browser = None
        self._ocr = None
        self._action_executor = None
        self.dedup = Deduplicator(self.db)
        self._paginator = None
        self._csv_analyzer = None
        self._dom_extractor = None
        self.formatter = MessageFormatter()

        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("  Scheduler started")

        logger.info("  Engine ready")
        logger.info("=" * 70)

    @property
    def browser(self):
        """Lazy initialization of browser controller"""
        if self._browser is None:
            self._browser = BrowserController()
        return self._browser

    @property
    def ocr(self):
        """Lazy initialization of OCR handler"""
        if self._ocr is None:
            self._ocr = OCRHandler()
        return self._ocr

    @property
    def paginator(self):
        """Lazy initialization of paginator"""
        if self._paginator is None:
            self._paginator = Paginator(self.browser, self.ocr)
        return self._paginator

    @property
    def action_executor(self):
        """Lazy initialization of action executor"""
        if self._action_executor is None:
            self._action_executor = ActionExecutor(self.browser, self.ocr)
        return self._action_executor

    @property
    def csv_analyzer(self):
        """Lazy initialization of CSV analyzer"""
        if self._csv_analyzer is None:
            self._csv_analyzer = CSVAnalyzer()
        return self._csv_analyzer

    @property
    def dom_extractor(self):
        """Lazy initialization of DOM extractor"""
        if self._dom_extractor is None:
            self._dom_extractor = DOMExtractor()
            # Connect to browser with Edge profile
            import os
            edge_profile = os.path.join(
                os.path.expanduser('~'),
                'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'
            )
            self._dom_extractor.connect_to_browser(edge_profile)
        return self._dom_extractor

    def execute_job(self, job_id: int):
        """
        Execute a single job with full logging

        Args:
            job_id: ID of job to execute
        """
        # Load job to check type
        job = self.db.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Route to appropriate executor based on job type
        job_type = job.get('job_type', 'ocr_extraction')
        if job_type == 'csv_analysis':
            self._execute_csv_job(job_id, job)
        elif job_type == 'dom_extraction':
            self._execute_dom_job(job_id, job)
        else:
            self._execute_ocr_job(job_id, job)

    def _execute_ocr_job(self, job_id: int, job: dict):
        """
        Execute an OCR extraction job

        Args:
            job_id: ID of job to execute
            job: Job configuration dict
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"EXECUTING OCR JOB ID: {job_id}")
        logger.info("=" * 70)

        start_time = datetime.now()
        log_id = self.db.start_execution_log(job_id)

        try:
            logger.info(f"Job: {job['name']}")
            logger.info(f"URL: {job['url']}")
            logger.info(f"Mode: {job['page_mode']}")
            logger.info(f"Regions: {len(job['ocr_regions'])}")
            logger.info(f"Pre-extraction actions: {len(job.get('pre_extraction_actions', []))}")

            # Initialize Telegram if configured
            telegram = None
            if job['telegram_bot_token'] and job['telegram_chat_id']:
                telegram = TelegramSender(job['telegram_bot_token'])
                logger.info("  Telegram configured")

            # Focus browser
            logger.info("\n[STEP 1] Focusing Edge browser")
            self.browser.focus_edge_browser()
            time.sleep(1)

            # Execute pre-extraction actions if any
            pre_actions = job.get('pre_extraction_actions', [])
            if pre_actions:
                logger.info(f"\n[STEP 2] Executing {len(pre_actions)} pre-extraction actions")
                action_result = self.action_executor.execute_actions(pre_actions)
                if not action_result.get('success', True):
                    logger.warning("Some pre-extraction actions failed, continuing anyway...")
                logger.info("Pre-extraction actions complete")

            # Extract data based on mode
            logger.info(f"\n[STEP 3] Extracting data ({job['page_mode']} mode)")

            if job['page_mode'] == 'single':
                all_data = [self.paginator.extract_single_page(job['ocr_regions'])]
            elif job['page_mode'] == 'scroll':
                all_data = self.paginator.scroll_and_extract(
                    job['ocr_regions'],
                    job['scroll_config']
                )
            elif job['page_mode'] == 'pagination':
                all_data = self.paginator.paginate_and_extract(
                    job['ocr_regions'],
                    job['pagination_config']
                )
            else:
                all_data = [self.paginator.extract_single_page(job['ocr_regions'])]

            logger.info(f"Extracted {len(all_data)} data points")

            # Process each data point
            logger.info(f"\n[STEP 4] Processing data (deduplication + Telegram)")
            new_count = 0
            dup_count = 0
            sent_count = 0

            for i, data in enumerate(all_data, 1):
                logger.info(f"\n[Data point {i}/{len(all_data)}]")

                # Remove metadata fields for hashing
                clean_data = {k: v for k, v in data.items() if not k.startswith('_')}

                if not clean_data or all(not v for v in clean_data.values()):
                    logger.warning("  Skipping empty data point")
                    continue

                # Check deduplication if enabled
                if job['enable_deduplication']:
                    result = self.dedup.process_item(job_id, clean_data)

                    if not result['is_new']:
                        dup_count += 1
                        continue

                    # Store new data
                    record_id = self.dedup.store_and_mark(
                        job_id,
                        result,
                        page_number=data.get('_page_number', 1),
                        scroll_position=data.get('_scroll_position', 0)
                    )
                else:
                    # Store without dedup check
                    data_hash = self.dedup.generate_hash(clean_data)
                    record_id = self.db.store_extracted_data(
                        job_id, clean_data, data_hash
                    )

                new_count += 1

                # Send to Telegram
                if telegram and job['format_template']:
                    message = self.formatter.format_message(clean_data, job['format_template'])

                    send_result = telegram.send_message(
                        job['telegram_chat_id'],
                        message
                    )

                    if send_result['success']:
                        sent_count += 1
                        self.db.mark_sent_to_telegram(record_id, send_result['message_id'])
                    else:
                        logger.error(f"  Telegram error: {send_result['error']}")

            # Update job last run
            next_run = datetime.now() + timedelta(hours=job['schedule_interval_hours'])
            self.db.update_job_last_run(job_id, next_run)

            # Complete execution log
            duration = (datetime.now() - start_time).total_seconds()

            self.db.complete_execution_log(
                log_id=log_id,
                status='success',
                pages_processed=len(all_data),
                items_extracted=len(all_data),
                items_new=new_count,
                items_duplicate=dup_count,
                items_sent=sent_count
            )

            logger.info("\n" + "=" * 70)
            logger.info("JOB EXECUTION COMPLETE")
            logger.info("=" * 70)
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info(f"  Total items: {len(all_data)}")
            logger.info(f"  New items: {new_count}")
            logger.info(f"  Duplicates: {dup_count}")
            logger.info(f"  Sent to Telegram: {sent_count}")
            logger.info("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"\nJOB FAILED: {e}")
            logger.exception("Full traceback:")

            # Complete log with error
            self.db.complete_execution_log(
                log_id=log_id,
                status='failed',
                error_message=str(e)
            )

    def _execute_csv_job(self, job_id: int, job: dict):
        """
        Execute a CSV analysis job

        Args:
            job_id: ID of job to execute
            job: Job configuration dict
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"EXECUTING CSV ANALYSIS JOB ID: {job_id}")
        logger.info("=" * 70)

        start_time = datetime.now()
        log_id = self.db.start_execution_log(job_id)

        try:
            csv_config = job.get('csv_config', {})
            logger.info(f"Job: {job['name']}")
            logger.info(f"URL: {job['url']}")
            logger.info(f"CSV Pattern: {csv_config.get('csv_filename_pattern', '*.csv')}")
            logger.info(f"Threshold: {csv_config.get('threshold_minutes', 10)} minutes")

            # Check active hours
            current_hour = datetime.now().hour
            active_start = csv_config.get('active_start_hour', 0)
            active_end = csv_config.get('active_end_hour', 23)

            if not (active_start <= current_hour <= active_end):
                logger.info(f"Outside active hours ({active_start}:00 - {active_end}:00). Skipping.")
                self.db.complete_execution_log(
                    log_id=log_id,
                    status='skipped',
                    error_message=f"Outside active hours ({active_start}:00 - {active_end}:00)"
                )
                return

            # Initialize Telegram if configured
            telegram = None
            if job.get('telegram_bot_token') and job.get('telegram_chat_id'):
                telegram = TelegramSender(job['telegram_bot_token'])
                logger.info("  Telegram configured")

            # Step 1: Focus browser and execute download actions
            download_actions = csv_config.get('download_actions', [])
            if download_actions:
                logger.info(f"\n[STEP 1] Executing {len(download_actions)} download actions")
                self.browser.focus_edge_browser()
                time.sleep(1)

                action_result = self.action_executor.execute_actions(download_actions)
                if not action_result.get('success', True):
                    logger.warning("Some download actions failed, continuing anyway...")

                # Wait for download to complete
                logger.info("Waiting for download to complete...")
                time.sleep(5)

            # Step 2: Find and analyze CSV
            logger.info("\n[STEP 2] Finding and analyzing CSV file")
            csv_pattern = csv_config.get('csv_filename_pattern', '*.csv')
            csv_path = self.csv_analyzer.find_latest_csv(csv_pattern)

            if not csv_path:
                raise ValueError(f"CSV file not found matching pattern: {csv_pattern}")

            logger.info(f"Found CSV: {csv_path}")

            # Analyze prep times
            alerts, date_str = self.csv_analyzer.analyze_prep_times(csv_path, csv_config)
            logger.info(f"Date: {date_str}")
            logger.info(f"Alerts: {len(alerts)} hours exceeded threshold")

            # Step 3: Send alerts if any
            sent_count = 0
            if alerts and telegram:
                logger.info("\n[STEP 3] Sending Telegram alerts")
                threshold = csv_config.get('threshold_minutes', 10)
                message = self.csv_analyzer.format_alert_message(alerts, date_str, threshold)

                send_result = telegram.send_message(
                    job['telegram_chat_id'],
                    message,
                    parse_mode='HTML'
                )

                if send_result['success']:
                    sent_count = 1
                    logger.info("Alert sent to Telegram")
                else:
                    logger.error(f"Telegram error: {send_result['error']}")
            elif not alerts:
                logger.info("\n[STEP 3] No alerts - all hours within threshold")

            # Step 4: Archive CSV
            logger.info("\n[STEP 4] Archiving CSV file")
            archived_path = self.csv_analyzer.archive_csv(csv_path)
            if archived_path:
                logger.info(f"Archived to: {archived_path}")

            # Update job last run
            next_run = datetime.now() + timedelta(hours=job['schedule_interval_hours'])
            self.db.update_job_last_run(job_id, next_run)

            # Complete execution log
            duration = (datetime.now() - start_time).total_seconds()

            self.db.complete_execution_log(
                log_id=log_id,
                status='success',
                pages_processed=1,
                items_extracted=len(alerts),
                items_new=len(alerts),
                items_duplicate=0,
                items_sent=sent_count
            )

            logger.info("\n" + "=" * 70)
            logger.info("CSV JOB EXECUTION COMPLETE")
            logger.info("=" * 70)
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info(f"  Date analyzed: {date_str}")
            logger.info(f"  Alerts generated: {len(alerts)}")
            logger.info(f"  Sent to Telegram: {sent_count}")
            logger.info("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"\nCSV JOB FAILED: {e}")
            logger.exception("Full traceback:")

            # Complete log with error
            self.db.complete_execution_log(
                log_id=log_id,
                status='failed',
                error_message=str(e)
            )

    def _execute_dom_job(self, job_id: int, job: dict):
        """
        Execute a DOM extraction job

        Args:
            job_id: ID of job to execute
            job: Job configuration dict
        """
        logger.info("\n" + "=" * 70)
        logger.info(f"EXECUTING DOM EXTRACTION JOB ID: {job_id}")
        logger.info("=" * 70)

        start_time = datetime.now()
        log_id = self.db.start_execution_log(job_id)

        try:
            dom_config = job.get('dom_config', {})
            logger.info(f"Job: {job['name']}")
            logger.info(f"URL: {dom_config.get('url', job.get('url'))}")
            logger.info(f"Selectors: {list(dom_config.get('selectors', {}).keys())}")
            logger.info(f"Pre-extraction actions: {len(job.get('pre_extraction_actions', []))}")

            # Initialize Telegram if configured
            telegram = None
            if job.get('telegram_bot_token') and job.get('telegram_chat_id'):
                telegram = TelegramSender(job['telegram_bot_token'])
                logger.info("  Telegram configured")

            # Step 1: Execute pre-extraction actions if any
            pre_actions = job.get('pre_extraction_actions', [])
            if pre_actions:
                logger.info(f"\n[STEP 1] Executing {len(pre_actions)} pre-extraction actions")
                self.browser.focus_edge_browser()
                time.sleep(1)
                action_result = self.action_executor.execute_actions(pre_actions)
                if not action_result.get('success', True):
                    logger.warning("Some pre-extraction actions failed, continuing anyway...")
                logger.info("Pre-extraction actions complete")

            # Step 2: Extract data from DOM
            logger.info("\n[STEP 2] Extracting data from DOM")
            url = dom_config.get('url', job.get('url'))
            selectors = dom_config.get('selectors', {})

            if url:
                extracted_data = self.dom_extractor.extract_data(
                    url=url,
                    selectors=selectors,
                    wait_for_selector=dom_config.get('wait_for_selector'),
                    wait_time=dom_config.get('wait_time', 2)
                )
            else:
                extracted_data = self.dom_extractor.extract_from_current_page(
                    selectors=selectors,
                    wait_time=dom_config.get('wait_time', 2)
                )

            logger.info(f"Extracted {len(extracted_data)} items")

            # Step 3: Process each item (deduplication + Telegram)
            logger.info(f"\n[STEP 3] Processing data (deduplication + Telegram)")
            new_count = 0
            dup_count = 0
            sent_count = 0

            for i, data in enumerate(extracted_data, 1):
                logger.info(f"\n[Item {i}/{len(extracted_data)}]")

                if not data or all(not v for v in data.values()):
                    logger.warning("  Skipping empty data point")
                    continue

                # Check deduplication if enabled
                if job.get('enable_deduplication', True):
                    result = self.dedup.process_item(job_id, data)

                    if not result['is_new']:
                        dup_count += 1
                        logger.info("  Duplicate - skipping")
                        continue

                    # Store new data
                    record_id = self.dedup.store_and_mark(job_id, result)
                else:
                    # Store without dedup check
                    data_hash = self.dedup.generate_hash(data)
                    record_id = self.db.store_extracted_data(job_id, data, data_hash)

                new_count += 1
                logger.info("  NEW - stored")

                # Send to Telegram
                if telegram and job.get('format_template'):
                    message = self.formatter.format_message(data, job['format_template'])

                    send_result = telegram.send_message(
                        job['telegram_chat_id'],
                        message
                    )

                    if send_result['success']:
                        sent_count += 1
                        self.db.mark_sent_to_telegram(record_id, send_result['message_id'])
                        logger.info("  Sent to Telegram")
                    else:
                        logger.error(f"  Telegram error: {send_result['error']}")

            # Update job last run
            next_run = datetime.now() + timedelta(hours=job['schedule_interval_hours'])
            self.db.update_job_last_run(job_id, next_run)

            # Complete execution log
            duration = (datetime.now() - start_time).total_seconds()

            self.db.complete_execution_log(
                log_id=log_id,
                status='success',
                pages_processed=1,
                items_extracted=len(extracted_data),
                items_new=new_count,
                items_duplicate=dup_count,
                items_sent=sent_count
            )

            logger.info("\n" + "=" * 70)
            logger.info("DOM JOB EXECUTION COMPLETE")
            logger.info("=" * 70)
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info(f"  Total items: {len(extracted_data)}")
            logger.info(f"  New items: {new_count}")
            logger.info(f"  Duplicates: {dup_count}")
            logger.info(f"  Sent to Telegram: {sent_count}")
            logger.info("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"\nDOM JOB FAILED: {e}")
            logger.exception("Full traceback:")

            # Complete log with error
            self.db.complete_execution_log(
                log_id=log_id,
                status='failed',
                error_message=str(e)
            )

    def schedule_job(self, job_id: int, interval_hours: int):
        """
        Schedule a job for periodic execution

        Args:
            job_id: Job ID
            interval_hours: Hours between executions
        """
        job_key = f"job_{job_id}"

        # Remove existing schedule if any
        try:
            self.scheduler.remove_job(job_key)
        except:
            pass

        # Add new schedule
        self.scheduler.add_job(
            self.execute_job,
            'interval',
            hours=interval_hours,
            args=[job_id],
            id=job_key,
            replace_existing=True
        )

        logger.info(f"Scheduled job {job_id} to run every {interval_hours} hours")

    def unschedule_job(self, job_id: int):
        """Remove job from schedule"""
        job_key = f"job_{job_id}"
        try:
            self.scheduler.remove_job(job_key)
            logger.info(f"Unscheduled job {job_id}")
        except:
            pass

    def schedule_all_active_jobs(self):
        """Schedule all active jobs from database"""
        logger.info("Scheduling all active jobs...")

        jobs = self.db.get_active_jobs()

        for job in jobs:
            self.schedule_job(job['id'], job['schedule_interval_hours'])

        logger.info(f"Total jobs scheduled: {len(jobs)}")

    def run_forever(self):
        """Run the engine indefinitely"""
        logger.info("\n" + "=" * 70)
        logger.info("ENGINE RUNNING")
        logger.info("=" * 70)
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70 + "\n")

        self.schedule_all_active_jobs()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.scheduler.shutdown()
            self.db.close()
            logger.info("Engine stopped")

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down engine...")
        self.scheduler.shutdown()
        self.db.close()
        logger.info("Engine stopped")


def main():
    """Main entry point"""
    engine = AutomationEngine()

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'run' and len(sys.argv) > 2:
            # Run specific job
            job_id = int(sys.argv[2])
            engine.execute_job(job_id)
        else:
            print("Usage:")
            print("  python engine.py          - Run engine with scheduler")
            print("  python engine.py run <id> - Run specific job once")
    else:
        # Run with scheduler
        engine.run_forever()


if __name__ == '__main__':
    main()
