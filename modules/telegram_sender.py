"""
Telegram Sender Module
Handles sending messages to Telegram chats/channels
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

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
    """Handles Telegram message sending with error handling"""

    def __init__(self, bot_token: str):
        """
        Initialize Telegram bot

        Args:
            bot_token: Telegram Bot API token from @BotFather
        """
        logger.info("Initializing Telegram bot")
        logger.info(f"  Token: {bot_token[:15]}...{bot_token[-5:]}")

        from telegram import Bot
        self.bot = Bot(token=bot_token)
        self.token = bot_token

        logger.info("  Telegram bot initialized")

    async def _send_message_async(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = 'HTML'
    ) -> Dict[str, Any]:
        """
        Internal async method to send message

        Args:
            chat_id: Telegram chat/channel ID
            message: Message text
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            Dict with {success, message_id, error}
        """
        try:
            result = await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )

            return {
                'success': True,
                'message_id': str(result.message_id),
                'error': None
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"  Telegram error: {error_msg}")

            return {
                'success': False,
                'message_id': None,
                'error': error_msg
            }

    def send_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = 'HTML'
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat/channel (sync wrapper)

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

        # Run async method in event loop
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new one in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._send_message_async(chat_id, message, parse_mode)
                    )
                    result = future.result()
            else:
                result = loop.run_until_complete(
                    self._send_message_async(chat_id, message, parse_mode)
                )
        except RuntimeError:
            # No event loop, create one
            result = asyncio.run(
                self._send_message_async(chat_id, message, parse_mode)
            )

        if result['success']:
            logger.info(f"  Message sent successfully")
            logger.info(f"  Message ID: {result['message_id']}")
        else:
            logger.error(f"  Failed to send: {result['error']}")

        logger.info("=" * 50)

        return result

    async def _test_connection_async(self) -> Dict[str, Any]:
        """Test bot connection by getting bot info"""
        try:
            bot_info = await self.bot.get_me()
            return {
                'success': True,
                'username': bot_info.username,
                'name': bot_info.first_name,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'username': None,
                'name': None,
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test bot connection

        Returns:
            Dict with {success, username, name, error}
        """
        logger.info("Testing Telegram bot connection...")

        try:
            result = asyncio.run(self._test_connection_async())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._test_connection_async())

        if result['success']:
            logger.info(f"  Connected as @{result['username']} ({result['name']})")
        else:
            logger.error(f"  Connection failed: {result['error']}")

        return result

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
