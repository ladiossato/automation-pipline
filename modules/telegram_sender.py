"""
Telegram Sender Module
Handles sending messages to Telegram chats/channels using direct HTTP requests
Includes AI-powered data transformation using Claude API
"""

import logging
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

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


class TelegramSender:
    """Handles Telegram message sending with direct HTTP requests (no async issues)"""

    def __init__(self, bot_token: str):
        """
        Initialize Telegram bot

        Args:
            bot_token: Telegram Bot API token from @BotFather
        """
        logger.info("Initializing Telegram bot")
        logger.info(f"  Token: {bot_token[:15]}...{bot_token[-5:]}")

        self.token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        logger.info("  Telegram bot initialized (using direct HTTP)")

    def send_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = 'HTML'
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat/channel using direct HTTP request

        Args:
            chat_id: Telegram chat/channel ID (e.g., '-100123456789')
            message: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            Dict with {success, message_id, error}
        """
        logger.info("=" * 50)
        logger.info("SENDING TELEGRAM MESSAGE")
        logger.info("=" * 50)
        logger.info(f"  Chat ID: {chat_id}")
        logger.info(f"  Message length: {len(message)} chars")
        logger.info(f"  Parse mode: {parse_mode}")
        logger.info(f"  Preview: {message[:100]}...")

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            response = requests.post(url, json=payload, timeout=30)
            data = response.json()

            if data.get('ok'):
                message_id = str(data['result']['message_id'])
                logger.info(f"  Message sent successfully")
                logger.info(f"  Message ID: {message_id}")
                logger.info("=" * 50)
                return {
                    'success': True,
                    'message_id': message_id,
                    'error': None
                }
            else:
                error_msg = data.get('description', 'Unknown error')
                logger.error(f"  Telegram API error: {error_msg}")
                logger.info("=" * 50)
                return {
                    'success': False,
                    'message_id': None,
                    'error': error_msg
                }

        except requests.exceptions.Timeout:
            logger.error(f"  Request timeout")
            logger.info("=" * 50)
            return {
                'success': False,
                'message_id': None,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"  Request error: {e}")
            logger.info("=" * 50)
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"  Unexpected error: {e}")
            logger.info("=" * 50)
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test bot connection by getting bot info

        Returns:
            Dict with {success, username, name, error}
        """
        logger.info("Testing Telegram bot connection...")

        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('ok'):
                bot_info = data['result']
                username = bot_info.get('username', 'unknown')
                name = bot_info.get('first_name', 'unknown')
                logger.info(f"  Connected as @{username} ({name})")
                return {
                    'success': True,
                    'username': username,
                    'name': name,
                    'error': None
                }
            else:
                error_msg = data.get('description', 'Unknown error')
                logger.error(f"  Connection failed: {error_msg}")
                return {
                    'success': False,
                    'username': None,
                    'name': None,
                    'error': error_msg
                }

        except Exception as e:
            logger.error(f"  Connection failed: {e}")
            return {
                'success': False,
                'username': None,
                'name': None,
                'error': str(e)
            }

    def test_send(self, chat_id: str) -> Dict[str, Any]:
        """
        Send a test message to verify chat access

        Args:
            chat_id: Telegram chat/channel ID

        Returns:
            Dict with send result
        """
        logger.info(f"Sending test message to {chat_id}")

        message = (
            "<b>Automation Platform Test</b>\n\n"
            "This is a test message from the OCR automation platform.\n"
            "If you see this, the bot is configured correctly.\n\n"
            "<i>Connection verified successfully.</i>"
        )

        return self.send_message(chat_id, message)

    def transform_data_with_ai(
        self,
        raw_data: Dict[str, Any],
        api_key: str,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use Claude API to intelligently transform raw extracted data into clean format

        Args:
            raw_data: Dictionary of extracted field values
            api_key: Anthropic API key
            custom_prompt: Optional custom transformation prompt

        Returns:
            Dict with {success, transformed_text, error}
        """
        logger.info("=" * 50)
        logger.info("AI DATA TRANSFORMATION")
        logger.info("=" * 50)
        logger.info(f"  Raw data fields: {list(raw_data.keys())}")

        if not api_key:
            logger.error("  No Anthropic API key provided")
            return {
                'success': False,
                'transformed_text': None,
                'error': 'No API key provided'
            }

        # Build the transformation prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = """Transform this raw extracted data into a clean, concise one-liner for a Telegram notification.

Format: MM/DD HH:MMam/pm | Error Type | Item Name (shortened) | Amount

Rules:
- Extract date and format as MM/DD HH:MMam/pm
- Use the error_type field as-is
- Shorten long item names (e.g., "1 x Sweet Shoyu Tofu Rice Bowl" → "Sweet Shoyu Tofu Bowl")
- Keep the amount with $ sign
- Use | as separator
- NO extra text, just the formatted line

Example input:
{"amount": "-$8.96", "customer": "Shikha G.", "date": "10:46pm Dec 2, 2025", "description": "No salad...", "error_type": "Missing item", "order_item": "1 x Sweet Shoyu Tofu Rice Bowl"}

Example output:
12/02 10:46pm | Missing item | Sweet Shoyu Tofu Bowl | -$8.96"""

        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 150,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nData to transform:\n{json.dumps(raw_data, indent=2)}"
                    }
                ]
            }

            logger.info("  Calling Claude API...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()

            if response.status_code == 200 and data.get('content'):
                transformed = data['content'][0]['text'].strip()
                logger.info(f"  Transformed: {transformed}")
                logger.info("=" * 50)
                return {
                    'success': True,
                    'transformed_text': transformed,
                    'error': None
                }
            else:
                error_msg = data.get('error', {}).get('message', f'API error: {response.status_code}')
                logger.error(f"  API error: {error_msg}")
                logger.info("=" * 50)
                return {
                    'success': False,
                    'transformed_text': None,
                    'error': error_msg
                }

        except requests.exceptions.Timeout:
            logger.error("  API request timeout")
            logger.info("=" * 50)
            return {
                'success': False,
                'transformed_text': None,
                'error': 'API request timeout'
            }
        except Exception as e:
            logger.error(f"  Transformation error: {e}")
            logger.info("=" * 50)
            return {
                'success': False,
                'transformed_text': None,
                'error': str(e)
            }


class MessageFormatter:
    """Formats extracted data into Telegram messages"""

    def __init__(self):
        logger.info("Initializing MessageFormatter")

    def format_message(
        self,
        data: Dict[str, Any],
        template: str
    ) -> str:
        """
        Format extracted data using template

        Args:
            data: Dict of extracted field values
            template: Template string with {field_name} placeholders

        Returns:
            Formatted message string
        """
        logger.info("Formatting message")
        logger.info(f"  Template: {template}")
        logger.info(f"  Data: {data}")

        message = template

        # Replace placeholders with values
        for key, value in data.items():
            if key.startswith('_'):  # Skip metadata fields
                continue
            placeholder = f"{{{key}}}"
            if placeholder in message:
                message = message.replace(placeholder, str(value))
                logger.info(f"  Replaced {placeholder} -> {value}")

        # Check for unreplaced placeholders
        import re
        remaining = re.findall(r'\{(\w+)\}', message)
        if remaining:
            logger.warning(f"  Unreplaced placeholders: {remaining}")

        logger.info(f"  Result: {message}")

        return message

    def format_batch(
        self,
        items: list,
        template: str,
        separator: str = "\n\n---\n\n"
    ) -> str:
        """
        Format multiple items into a single message

        Args:
            items: List of data dicts
            template: Template for each item
            separator: Separator between items

        Returns:
            Combined formatted message
        """
        logger.info(f"Formatting batch of {len(items)} items")

        formatted = []
        for i, item in enumerate(items, 1):
            logger.info(f"  Formatting item {i}/{len(items)}")
            formatted.append(self.format_message(item, template))

        combined = separator.join(formatted)
        logger.info(f"  Total message length: {len(combined)} chars")

        # Telegram has 4096 char limit
        if len(combined) > 4000:
            logger.warning("  Message exceeds 4000 chars, may be truncated")

        return combined

    def escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
