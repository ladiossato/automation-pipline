"""
CSV Analyzer Module
Analyzes CSV files for prep time statistics and generates alerts
"""

import os
import glob
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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


class CSVAnalyzer:
    """Analyzes CSV files for prep time statistics"""

    def __init__(self, downloads_folder: str = None):
        """
        Initialize CSV analyzer

        Args:
            downloads_folder: Path to downloads folder (defaults to user's Downloads)
        """
        if downloads_folder is None:
            downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')

        self.downloads_folder = Path(downloads_folder)
        logger.info("CSVAnalyzer initialized")
        logger.info(f"  Downloads folder: {self.downloads_folder}")

    def find_latest_csv(self, pattern: str) -> Optional[str]:
        """
        Find most recently downloaded CSV matching pattern

        Args:
            pattern: Glob pattern to match (e.g., "Order History-*.csv")

        Returns:
            Path to most recent matching file, or None if not found
        """
        logger.info(f"Searching for CSV matching: {pattern}")

        search_pattern = self.downloads_folder / pattern
        files = glob.glob(str(search_pattern))

        if not files:
            logger.warning(f"  No files found matching: {pattern}")
            return None

        # Get most recent file by creation time
        latest_file = max(files, key=os.path.getctime)
        logger.info(f"  Found: {os.path.basename(latest_file)}")

        return latest_file

    def analyze_prep_times(
        self,
        csv_path: str,
        config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Analyze prep times by hour and identify hours exceeding threshold

        Args:
            csv_path: Path to CSV file
            config: Configuration with columns and threshold settings

        Returns:
            Tuple of (alerts list, date string)
        """
        # Import pandas here to avoid startup delay
        import pandas as pd

        logger.info("=" * 60)
        logger.info("ANALYZING CSV: PREP TIME BY HOUR")
        logger.info("=" * 60)
        logger.info(f"File: {os.path.basename(csv_path)}")

        # Read CSV
        df = pd.read_csv(csv_path)
        logger.info(f"  Rows: {len(df)}")
        logger.info(f"  Columns: {list(df.columns)}")

        # Extract column names from config
        columns = config.get('columns', {})
        datetime_col = columns.get('datetime', 'Fulfilled')
        prep_time_col = columns.get('prep_time', 'Prep Time')
        items_col = columns.get('items', 'Items Quantity')
        threshold = config.get('threshold_minutes', 10)

        logger.info(f"\nConfiguration:")
        logger.info(f"  Datetime column: {datetime_col}")
        logger.info(f"  Prep time column: {prep_time_col}")
        logger.info(f"  Items column: {items_col}")
        logger.info(f"  Threshold: {threshold} minutes")

        # Validate columns exist
        missing_cols = []
        for col in [datetime_col, prep_time_col, items_col]:
            if col not in df.columns:
                missing_cols.append(col)

        if missing_cols:
            raise ValueError(f"Missing columns in CSV: {missing_cols}")

        # Parse datetime - handle multiple formats
        try:
            # Try common datetime formats
            df['parsed_datetime'] = pd.to_datetime(
                df[datetime_col],
                format='%m/%d/%Y, %I:%M:%S %p',
                errors='coerce'
            )

            # Try alternative format if first failed
            if df['parsed_datetime'].isna().all():
                df['parsed_datetime'] = pd.to_datetime(
                    df[datetime_col],
                    errors='coerce'
                )
        except Exception as e:
            logger.error(f"  Error parsing datetime: {e}")
            raise

        # Extract prep time minutes
        # Handle formats like "8m", "12m", "8 min", etc.
        def extract_minutes(val):
            if pd.isna(val):
                return None
            val_str = str(val)
            match = re.search(r'(\d+)', val_str)
            if match:
                return float(match.group(1))
            return None

        df['prep_minutes'] = df[prep_time_col].apply(extract_minutes)

        # Extract items quantity
        def extract_items(val):
            if pd.isna(val):
                return 0
            try:
                return int(val)
            except (ValueError, TypeError):
                match = re.search(r'(\d+)', str(val))
                return int(match.group(1)) if match else 0

        df['item_count'] = df[items_col].apply(extract_items)

        # Extract hour
        df['hour'] = df['parsed_datetime'].dt.hour

        # Filter out rows with missing data
        valid_df = df.dropna(subset=['parsed_datetime', 'prep_minutes', 'hour'])
        logger.info(f"  Valid rows for analysis: {len(valid_df)}")

        if len(valid_df) == 0:
            logger.warning("  No valid data for analysis")
            return [], datetime.now().strftime('%b %d, %Y')

        # Group by hour
        hourly_stats = valid_df.groupby('hour').agg({
            'prep_minutes': 'mean',
            datetime_col: 'count',  # Order count
            'item_count': 'sum'  # Total items
        }).reset_index()

        hourly_stats.columns = ['hour', 'avg_prep_time', 'order_count', 'total_items']

        logger.info(f"\nHourly Statistics:")
        for _, row in hourly_stats.iterrows():
            hour = int(row['hour'])
            avg_time = row['avg_prep_time']
            orders = int(row['order_count'])
            items = int(row['total_items'])

            status = "!!!" if avg_time > threshold else "OK"
            logger.info(f"  [{status}] {hour:02d}:00 - Avg: {avg_time:.1f}m | Orders: {orders} | Items: {items}")

        # Find hours exceeding threshold
        alerts = hourly_stats[hourly_stats['avg_prep_time'] > threshold].to_dict('records')

        # Get date from data
        date_str = valid_df['parsed_datetime'].min().strftime('%b %d, %Y')

        logger.info(f"\n{'=' * 60}")
        logger.info(f"ALERTS: {len(alerts)} hours exceed {threshold} minute threshold")
        logger.info(f"{'=' * 60}\n")

        return alerts, date_str

    def archive_csv(self, csv_path: str, archive_folder: str = 'archive') -> str:
        """
        Move processed CSV to archive folder

        Args:
            csv_path: Path to CSV file
            archive_folder: Name of archive subfolder

        Returns:
            Path to archived file
        """
        archive_dir = self.downloads_folder / archive_folder
        archive_dir.mkdir(parents=True, exist_ok=True)

        filename = os.path.basename(csv_path)
        # Add timestamp to prevent overwriting
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        archive_filename = f"{name}_{timestamp}{ext}"
        archive_path = archive_dir / archive_filename

        os.rename(csv_path, str(archive_path))
        logger.info(f"CSV archived to: {archive_path}")

        return str(archive_path)

    def format_alert_message(
        self,
        alerts: List[Dict[str, Any]],
        date_str: str,
        threshold: int
    ) -> str:
        """
        Format Telegram message for CSV alerts

        Args:
            alerts: List of alert dictionaries
            date_str: Date string for the report
            threshold: Threshold in minutes

        Returns:
            Formatted HTML message for Telegram
        """
        if not alerts:
            return f"All hours within threshold ({threshold} min) for {date_str}"

        message = f"<b>PREP TIME ALERT</b> - {date_str}\n\n"

        for alert in alerts:
            hour = int(alert['hour'])
            avg_time = alert['avg_prep_time']
            orders = int(alert['order_count'])
            items = int(alert['total_items'])

            # Format hour range (12-hour format)
            hour_12 = hour % 12 or 12
            am_pm = 'PM' if hour >= 12 else 'AM'
            next_hour = (hour + 1) % 12 or 12
            next_am_pm = 'PM' if (hour + 1) >= 12 else 'AM'

            hour_start = f"{hour_12}:00 {am_pm}"
            hour_end = f"{next_hour}:00 {next_am_pm}"

            message += f"<b>{hour_start} - {hour_end}</b>\n"
            message += f"  Avg: <b>{avg_time:.1f} min</b> (threshold: {threshold} min)\n"
            message += f"  Orders: {orders} | Items: {items}\n\n"

        return message

    def get_csv_preview(self, csv_path: str, num_rows: int = 5) -> Dict[str, Any]:
        """
        Get preview of CSV file contents

        Args:
            csv_path: Path to CSV file
            num_rows: Number of rows to preview

        Returns:
            Dictionary with columns and sample data
        """
        import pandas as pd

        df = pd.read_csv(csv_path, nrows=num_rows)

        return {
            'columns': list(df.columns),
            'row_count': len(df),
            'sample_data': df.to_dict('records')
        }
