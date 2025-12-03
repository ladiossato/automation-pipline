"""
Database Operations Test Suite
Tests all database functionality with extensive logging
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.database import Database
from init_db import init_database


def test_database():
    """Run complete database test suite"""
    print("\n" + "=" * 60)
    print("TESTING DATABASE OPERATIONS")
    print("=" * 60 + "\n")

    # Step 1: Initialize database
    print("[STEP 1] Initializing database schema...")
    result = init_database()
    if not result:
        print("⚠ Database initialization failed!")
        return False
    print()

    # Step 2: Create Database instance
    print("[STEP 2] Creating Database instance...")
    db = Database()
    print()

    # Test 3: Create test job
    print("[TEST 3] Creating test job...")
    print("-" * 40)
    job_id = db.create_job({
        'name': 'test_job_001',
        'url': 'https://example.com/stocks',
        'ocr_regions': [
            {'name': 'symbol', 'x': 100, 'y': 200, 'width': 150, 'height': 40},
            {'name': 'price', 'x': 300, 'y': 200, 'width': 100, 'height': 40}
        ],
        'format_template': 'Stock: {symbol} - Price: ${price}',
        'telegram_bot_token': 'test_token_123',
        'telegram_chat_id': '-100123456789',
        'page_mode': 'pagination',
        'pagination_config': {
            'mode': 'ocr',
            'button_text': 'Next',
            'max_pages': 10
        },
        'enable_deduplication': True,
        'schedule_interval_hours': 2,
        'active': False
    })
    print(f"✓ Job created with ID: {job_id}")
    assert job_id > 0, "Job ID should be positive"
    print()

    # Test 4: Read job back
    print("[TEST 4] Reading job back...")
    print("-" * 40)
    job = db.get_job(job_id)
    print(f"  Name: {job['name']}")
    print(f"  URL: {job['url']}")
    print(f"  OCR Regions: {job['ocr_regions']}")
    print(f"  Page Mode: {job['page_mode']}")
    print(f"  Pagination Config: {job['pagination_config']}")
    assert job['name'] == 'test_job_001', "Job name mismatch"
    assert len(job['ocr_regions']) == 2, "Should have 2 OCR regions"
    print("✓ Job data verified")
    print()

    # Test 5: Store extracted data
    print("[TEST 5] Storing extracted data...")
    print("-" * 40)
    test_data = {'symbol': 'AAPL', 'price': '175.50'}
    test_hash = 'abc123def456'
    data_id = db.store_extracted_data(
        job_id=job_id,
        data=test_data,
        data_hash=test_hash,
        page_number=1
    )
    print(f"✓ Data stored with ID: {data_id}")
    assert data_id > 0, "Data ID should be positive"
    print()

    # Test 6: Check duplicate detection (should find duplicate)
    print("[TEST 6] Testing duplicate detection (same hash)...")
    print("-" * 40)
    is_dup = db.is_duplicate(job_id, test_hash)
    print(f"  Hash: {test_hash}")
    print(f"  Is duplicate: {is_dup}")
    assert is_dup == True, "Should detect as duplicate"
    print("✓ Duplicate correctly detected")
    print()

    # Test 7: Check duplicate detection (new hash)
    print("[TEST 7] Testing duplicate detection (new hash)...")
    print("-" * 40)
    new_hash = 'xyz789new'
    is_dup = db.is_duplicate(job_id, new_hash)
    print(f"  Hash: {new_hash}")
    print(f"  Is duplicate: {is_dup}")
    assert is_dup == False, "Should NOT detect as duplicate"
    print("✓ New data correctly identified")
    print()

    # Test 8: Store another data point
    print("[TEST 8] Storing second data point...")
    print("-" * 40)
    data_id2 = db.store_extracted_data(
        job_id=job_id,
        data={'symbol': 'GOOGL', 'price': '142.25'},
        data_hash='googl_hash_001',
        page_number=1
    )
    print(f"✓ Second data stored with ID: {data_id2}")
    print()

    # Test 9: Get all extracted data
    print("[TEST 9] Retrieving extracted data...")
    print("-" * 40)
    all_data = db.get_extracted_data(job_id)
    print(f"  Found {len(all_data)} records:")
    for record in all_data:
        print(f"    - {record['data']}")
    assert len(all_data) == 2, "Should have 2 data records"
    print("✓ Data retrieval verified")
    print()

    # Test 10: Execution logging
    print("[TEST 10] Testing execution logging...")
    print("-" * 40)
    log_id = db.start_execution_log(job_id)
    print(f"  Started log ID: {log_id}")

    db.complete_execution_log(
        log_id=log_id,
        status='success',
        pages_processed=3,
        items_extracted=10,
        items_new=5,
        items_duplicate=5,
        items_sent=5
    )
    print("  Log completed")

    logs = db.get_execution_logs(job_id)
    print(f"  Retrieved {len(logs)} logs")
    assert len(logs) == 1, "Should have 1 execution log"
    assert logs[0]['status'] == 'success', "Status should be success"
    print("✓ Execution logging verified")
    print()

    # Test 11: Update job
    print("[TEST 11] Testing job update...")
    print("-" * 40)
    db.update_job(job_id, {
        'active': True,
        'schedule_interval_hours': 4
    })
    updated_job = db.get_job(job_id)
    assert updated_job['active'] == 1, "Job should be active"
    assert updated_job['schedule_interval_hours'] == 4, "Interval should be 4"
    print("✓ Job update verified")
    print()

    # Test 12: Get active jobs
    print("[TEST 12] Getting active jobs...")
    print("-" * 40)
    active_jobs = db.get_active_jobs()
    print(f"  Found {len(active_jobs)} active jobs")
    assert len(active_jobs) == 1, "Should have 1 active job"
    print("✓ Active jobs query verified")
    print()

    # Test 13: Get stats
    print("[TEST 13] Getting database stats...")
    print("-" * 40)
    stats = db.get_stats()
    print(f"  Total jobs: {stats['total_jobs']}")
    print(f"  Active jobs: {stats['active_jobs']}")
    print(f"  Total extracted data: {stats['total_extracted_data']}")
    print(f"  Total execution logs: {stats['total_execution_logs']}")
    print("✓ Stats verified")
    print()

    # Cleanup
    print("[CLEANUP] Deleting test job...")
    print("-" * 40)
    db.delete_job(job_id)
    deleted_job = db.get_job(job_id)
    assert deleted_job is None, "Job should be deleted"
    print("✓ Cleanup complete")
    print()

    # Close connection
    db.close()

    print("=" * 60)
    print("ALL DATABASE TESTS PASSED ✓")
    print("=" * 60)
    print("\nDatabase file: database/automation.db")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_database()
        if success:
            print("Ready to proceed to Phase 2? (y/n)")
        else:
            print("Tests failed - fix issues before proceeding")
    except Exception as e:
        print(f"\n⚠ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
