"""
Telegram Integration Test Suite
Tests bot connection and message sending
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.telegram_sender import TelegramSender, MessageFormatter


def test_formatter():
    """Test message formatting without Telegram"""
    print("\n" + "=" * 60)
    print("TEST: MESSAGE FORMATTING")
    print("=" * 60 + "\n")

    formatter = MessageFormatter()

    # Test 1: Basic formatting
    print("[TEST 1] Basic template formatting")
    print("-" * 40)
    data = {'symbol': 'AAPL', 'price': '175.50', 'change': '+2.3%'}
    template = "Stock: {symbol}\nPrice: ${price}\nChange: {change}"
    result = formatter.format_message(data, template)
    print(f"  Data: {data}")
    print(f"  Template: {template}")
    print(f"  Result:\n{result}")
    assert 'AAPL' in result
    assert '175.50' in result
    print("  PASS\n")

    # Test 2: HTML formatting
    print("[TEST 2] HTML template formatting")
    print("-" * 40)
    template_html = "<b>{symbol}</b> - ${price} (<i>{change}</i>)"
    result_html = formatter.format_message(data, template_html)
    print(f"  Result: {result_html}")
    assert '<b>AAPL</b>' in result_html
    print("  PASS\n")

    # Test 3: Missing placeholders
    print("[TEST 3] Missing placeholders handled")
    print("-" * 40)
    template_missing = "Stock: {symbol} - Volume: {volume}"
    result_missing = formatter.format_message({'symbol': 'MSFT'}, template_missing)
    print(f"  Result: {result_missing}")
    # Volume should remain as placeholder
    assert '{volume}' in result_missing
    print("  PASS\n")

    # Test 4: Batch formatting
    print("[TEST 4] Batch formatting")
    print("-" * 40)
    items = [
        {'symbol': 'AAPL', 'price': '175'},
        {'symbol': 'GOOGL', 'price': '142'},
        {'symbol': 'MSFT', 'price': '378'}
    ]
    batch_template = "{symbol}: ${price}"
    batch_result = formatter.format_batch(items, batch_template, separator="\n")
    print(f"  Items: {len(items)}")
    print(f"  Result:\n{batch_result}")
    assert 'AAPL' in batch_result
    assert 'GOOGL' in batch_result
    print("  PASS\n")

    print("=" * 60)
    print("FORMATTING TESTS PASSED")
    print("=" * 60 + "\n")


def test_telegram_connection():
    """Test Telegram bot connection and sending"""
    print("\n" + "=" * 60)
    print("TELEGRAM CONNECTION TEST")
    print("=" * 60 + "\n")

    print("This test requires your Telegram bot credentials.")
    print("\nTo get a bot token:")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot and follow instructions")
    print("3. Copy the token provided\n")

    print("To get your chat ID:")
    print("1. Add your bot to a group/channel")
    print("2. Send a message in the group")
    print("3. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates")
    print("4. Find the 'chat' -> 'id' field\n")

    print("-" * 40)
    bot_token = input("Enter bot token (or 'skip' to skip): ").strip()

    if bot_token.lower() == 'skip':
        print("\nSkipping Telegram tests.")
        return True

    chat_id = input("Enter chat ID: ").strip()

    print("\n[TEST] Initializing bot...")
    try:
        telegram = TelegramSender(bot_token)
        print("  Bot initialized\n")
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False

    # Test connection
    print("[TEST] Testing connection...")
    conn_result = telegram.test_connection()
    if conn_result['success']:
        print(f"  Connected as @{conn_result['username']}\n")
    else:
        print(f"  FAILED: {conn_result['error']}\n")
        return False

    # Send test message
    print("[TEST] Sending test message...")
    send_result = telegram.test_send(chat_id)
    if send_result['success']:
        print(f"  Message sent! ID: {send_result['message_id']}")
        print("  Check your Telegram for the message.\n")
    else:
        print(f"  FAILED: {send_result['error']}\n")
        return False

    # Send formatted message
    print("[TEST] Sending formatted message...")
    formatter = MessageFormatter()
    data = {
        'symbol': 'AAPL',
        'price': '175.50',
        'change': '+2.3%'
    }
    template = "<b>Stock Alert</b>\n\nSymbol: {symbol}\nPrice: ${price}\nChange: {change}"
    formatted = formatter.format_message(data, template)

    send_result2 = telegram.send_message(chat_id, formatted)
    if send_result2['success']:
        print(f"  Formatted message sent! ID: {send_result2['message_id']}")
        print("  Check your Telegram for the formatted message.\n")
    else:
        print(f"  FAILED: {send_result2['error']}\n")
        return False

    print("=" * 60)
    print("TELEGRAM TESTS PASSED")
    print("=" * 60)
    print("\nNote: Save your bot token and chat ID for later use.")
    print(f"  Bot Token: {bot_token}")
    print(f"  Chat ID: {chat_id}\n")

    return True


def run_tests():
    """Run all tests"""
    print("\n" + "#" * 60)
    print("#" + " " * 15 + "TELEGRAM TEST SUITE" + " " * 16 + "#")
    print("#" * 60 + "\n")

    # Run formatter tests (no API needed)
    test_formatter()

    # Ask about Telegram tests
    print("\nWould you like to test Telegram connection?")
    print("This requires a bot token and chat ID.")
    response = input("Test Telegram? (y/n): ").strip().lower()

    if response == 'y':
        test_telegram_connection()

    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("\nProceed to Phase 6 (Web UI)? (y/n)")


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
