"""
Deduplicator Module
Handles content-based hashing and duplicate detection
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

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


class Deduplicator:
    """Handles content-based deduplication using MD5 hashing"""

    def __init__(self, db):
        """
        Initialize deduplicator with database connection

        Args:
            db: Database instance for storing/checking hashes
        """
        logger.info("Initializing Deduplicator")
        self.db = db
        logger.info("  Deduplicator ready")

    def generate_hash(self, data: Dict[str, Any]) -> str:
        """
        Generate MD5 hash from extracted data

        The hash is generated from sorted key-value pairs to ensure
        consistent hashing regardless of dict ordering.

        Args:
            data: Dict of extracted fields {field_name: value}

        Returns:
            str: MD5 hash (32 character hex string)
        """
        logger.info("Generating content hash")
        logger.debug(f"  Input data: {data}")

        # Filter out empty/None values and metadata fields
        clean_data = {
            k: str(v).strip()
            for k, v in data.items()
            if v is not None and str(v).strip() and not k.startswith('_')
        }

        if not clean_data:
            logger.warning("  No valid data for hashing!")
            return hashlib.md5(b"empty").hexdigest()

        # Sort keys for consistent hashing
        sorted_items = sorted(clean_data.items())

        # Create content string
        content_parts = []
        for k, v in sorted_items:
            content_parts.append(f"{k}:{v}")

        content = "|".join(content_parts)
        logger.debug(f"  Content string: {content}")

        # Generate hash
        hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()
        logger.info(f"  Hash: {hash_value}")

        return hash_value

    def is_duplicate(self, job_id: int, data_hash: str) -> bool:
        """
        Check if hash exists in database for this job

        Args:
            job_id: Job ID to check against
            data_hash: MD5 hash to check

        Returns:
            bool: True if duplicate, False if new
        """
        logger.info(f"Checking duplicate: job_id={job_id}")
        logger.info(f"  Hash: {data_hash}")

        exists = self.db.is_duplicate(job_id, data_hash)

        if exists:
            logger.info("  Result: DUPLICATE (already exists)")
        else:
            logger.info("  Result: NEW (not seen before)")

        return exists

    def process_item(
        self,
        job_id: int,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single extracted data item with deduplication

        Args:
            job_id: Job ID for database lookup
            extracted_data: Dict of extracted field values

        Returns:
            Dict with:
                - is_new: bool - True if this is new data
                - hash: str - MD5 hash of the content
                - should_send: bool - True if should send to Telegram
                - data: Dict - The original extracted data
        """
        logger.info("=" * 50)
        logger.info("PROCESSING ITEM FOR DEDUPLICATION")
        logger.info("=" * 50)
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Data: {extracted_data}")

        # Generate hash
        data_hash = self.generate_hash(extracted_data)

        # Check if duplicate
        is_dup = self.is_duplicate(job_id, data_hash)

        result = {
            'is_new': not is_dup,
            'hash': data_hash,
            'should_send': not is_dup,
            'data': extracted_data
        }

        logger.info("-" * 50)
        logger.info(f"Result: {'NEW - will send' if result['is_new'] else 'DUPLICATE - skip'}")
        logger.info("=" * 50)

        return result

    def process_batch(
        self,
        job_id: int,
        items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process multiple items and separate new from duplicates

        Args:
            job_id: Job ID for database lookup
            items: List of extracted data dicts

        Returns:
            Tuple of (new_items, duplicate_items)
        """
        logger.info("=" * 50)
        logger.info(f"BATCH DEDUPLICATION: {len(items)} items")
        logger.info("=" * 50)

        new_items = []
        duplicate_items = []

        for i, item in enumerate(items, 1):
            logger.info(f"\n[Item {i}/{len(items)}]")

            result = self.process_item(job_id, item)

            if result['is_new']:
                new_items.append(result)
            else:
                duplicate_items.append(result)

        logger.info("\n" + "=" * 50)
        logger.info("BATCH SUMMARY")
        logger.info("=" * 50)
        logger.info(f"  Total items: {len(items)}")
        logger.info(f"  New items: {len(new_items)}")
        logger.info(f"  Duplicates: {len(duplicate_items)}")
        logger.info("=" * 50)

        return new_items, duplicate_items

    def store_and_mark(
        self,
        job_id: int,
        result: Dict[str, Any],
        page_number: int = 1,
        scroll_position: int = 0
    ) -> int:
        """
        Store new item in database after deduplication check

        Args:
            job_id: Job ID
            result: Result from process_item()
            page_number: Page number where found
            scroll_position: Scroll position where found

        Returns:
            int: Database record ID, or -1 if duplicate/failed
        """
        if not result['is_new']:
            logger.info("Skipping storage - duplicate item")
            return -1

        logger.info("Storing new item in database")

        record_id = self.db.store_extracted_data(
            job_id=job_id,
            data=result['data'],
            data_hash=result['hash'],
            page_number=page_number,
            scroll_position=scroll_position
        )

        logger.info(f"  Stored with ID: {record_id}")
        return record_id

    def get_stats(self, job_id: int) -> Dict[str, Any]:
        """
        Get deduplication statistics for a job

        Args:
            job_id: Job ID

        Returns:
            Dict with stats
        """
        logger.info(f"Getting dedup stats for job {job_id}")

        # Get recent data
        all_data = self.db.get_extracted_data(job_id, limit=1000)

        total = len(all_data)
        sent = sum(1 for d in all_data if d.get('sent_to_telegram'))
        pending = total - sent

        stats = {
            'total_items': total,
            'sent_to_telegram': sent,
            'pending': pending
        }

        logger.info(f"  Stats: {stats}")
        return stats
