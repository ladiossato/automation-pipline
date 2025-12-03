"""
Flask Web Application
Provides web UI for job configuration and management
"""

import sys
import io
import json
import base64
import logging
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, render_template, request, jsonify, redirect, url_for

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, LOG_FORMAT, LOG_DATE_FORMAT, SCREENSHOTS_DIR
from modules.database import Database
from modules.browser_control import BrowserController
from modules.ocr_handler import OCRHandler
from modules.telegram_sender import TelegramSender, MessageFormatter
from modules.action_executor import ActionExecutor
from modules.csv_analyzer import CSVAnalyzer
from modules.dom_extractor import DOMExtractor
from init_db import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'automation-platform-secret-key-change-in-production'

# Initialize database
init_database()
db = Database()

# Lazy initialization for heavy modules
_browser = None
_ocr = None
_action_executor = None
_dom_extractor = None


def get_browser():
    """Lazy initialization of browser controller"""
    global _browser
    if _browser is None:
        _browser = BrowserController()
    return _browser


def get_ocr():
    """Lazy initialization of OCR handler"""
    global _ocr
    if _ocr is None:
        _ocr = OCRHandler()
    return _ocr


def get_action_executor():
    """Lazy initialization of action executor"""
    global _action_executor
    if _action_executor is None:
        _action_executor = ActionExecutor(get_browser(), get_ocr())
    return _action_executor


def get_dom_extractor():
    """Lazy initialization of DOM extractor"""
    global _dom_extractor
    if _dom_extractor is None:
        _dom_extractor = DOMExtractor()
        # Connect to browser via DevTools Protocol (port 9222)
        _dom_extractor.connect_to_browser()
    return _dom_extractor


# ==================== PAGE ROUTES ====================

@app.route('/')
def index():
    """Dashboard / Job list page"""
    logger.info("Loading dashboard")
    jobs = db.get_all_jobs()
    stats = db.get_stats()
    return render_template('index.html', jobs=jobs, stats=stats)


@app.route('/job/new')
def new_job():
    """New job creation page"""
    logger.info("Loading new job page")
    return render_template('job_editor.html', job=None)


@app.route('/job/<int:job_id>')
def edit_job(job_id):
    """Edit existing job page"""
    logger.info(f"Loading job editor for job {job_id}")
    job = db.get_job(job_id)
    if not job:
        return redirect(url_for('index'))
    return render_template('job_editor.html', job=job)


@app.route('/job/<int:job_id>/logs')
def job_logs(job_id):
    """View execution logs for a job"""
    logger.info(f"Loading logs for job {job_id}")
    job = db.get_job(job_id)
    logs = db.get_execution_logs(job_id)
    return render_template('logs.html', job=job, logs=logs)


@app.route('/csv-job/new')
def new_csv_job():
    """New CSV analysis job creation page"""
    logger.info("Loading new CSV job page")
    return render_template('csv_job_editor.html', job=None)


@app.route('/csv-job/<int:job_id>')
def edit_csv_job(job_id):
    """Edit existing CSV analysis job page"""
    logger.info(f"Loading CSV job editor for job {job_id}")
    job = db.get_job(job_id)
    if not job:
        return redirect(url_for('index'))
    return render_template('csv_job_editor.html', job=job)


@app.route('/dom-job/new')
def new_dom_job():
    """New DOM extraction job creation page"""
    logger.info("Loading new DOM job page")
    return render_template('dom_job_editor.html', job=None)


@app.route('/dom-job/<int:job_id>')
def edit_dom_job(job_id):
    """Edit existing DOM extraction job page"""
    logger.info(f"Loading DOM job editor for job {job_id}")
    job = db.get_job(job_id)
    if not job:
        return redirect(url_for('index'))
    return render_template('dom_job_editor.html', job=job)


# ==================== API ROUTES ====================

@app.route('/api/jobs', methods=['GET'])
def api_get_jobs():
    """Get all jobs"""
    jobs = db.get_all_jobs()
    return jsonify(jobs)


@app.route('/api/job', methods=['POST'])
def api_create_job():
    """Create new job"""
    data = request.json
    logger.info(f"Creating job: {data.get('name')}")

    try:
        job_id = db.create_job(data)
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/job/<int:job_id>', methods=['PUT'])
def api_update_job(job_id):
    """Update existing job"""
    data = request.json
    logger.info(f"Updating job {job_id}")

    try:
        db.update_job(job_id, data)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/job/<int:job_id>', methods=['DELETE'])
def api_delete_job(job_id):
    """Delete job"""
    logger.info(f"Deleting job {job_id}")

    try:
        db.delete_job(job_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/job/<int:job_id>/toggle', methods=['POST'])
def api_toggle_job(job_id):
    """Toggle job active status"""
    logger.info(f"Toggling job {job_id}")

    job = db.get_job(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    new_status = not job['active']
    db.update_job(job_id, {'active': new_status})

    return jsonify({'success': True, 'active': new_status})


@app.route('/api/capture-screen', methods=['POST'])
def api_capture_screen():
    """Capture current screen and return as base64"""
    logger.info("Capturing screen for region selector")

    try:
        browser = get_browser()
        screenshot = browser.capture_full_screen()

        # Save to file
        save_path = browser.save_screenshot(screenshot, "region_capture")

        # Convert to base64 for display
        import io as bytesio
        buffer = bytesio.BytesIO()
        screenshot.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return jsonify({
            'success': True,
            'screenshot': img_base64,
            'width': screenshot.size[0],
            'height': screenshot.size[1],
            'saved_path': save_path
        })
    except Exception as e:
        logger.error(f"Error capturing screen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-region', methods=['POST'])
def api_test_region():
    """Test OCR extraction on a region"""
    data = request.json
    logger.info(f"Testing OCR on region: {data.get('region', {}).get('name')}")

    try:
        # Decode screenshot from base64
        img_data = base64.b64decode(data['screenshot'])
        from PIL import Image
        import io as bytesio
        screenshot = Image.open(bytesio.BytesIO(img_data))

        # Get OCR handler
        ocr = get_ocr()

        # Extract from region
        result = ocr.extract_text(screenshot, data['region'])

        return jsonify({
            'success': True,
            'text': result['text'],
            'confidence': result['confidence'],
            'raw_detections': result.get('raw_detections', [])
        })
    except Exception as e:
        logger.error(f"Error testing region: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-extraction', methods=['POST'])
def api_test_extraction():
    """Test full extraction with current screen"""
    data = request.json
    logger.info("Testing full extraction")

    try:
        browser = get_browser()
        ocr = get_ocr()

        # Capture screen
        screenshot = browser.capture_full_screen()

        # Extract from all regions
        regions = data.get('ocr_regions', [])
        results = ocr.extract_all_regions(screenshot, regions)
        data_dict = ocr.get_data_as_dict(results)

        # Format message if template provided
        formatted_message = None
        if data.get('format_template'):
            formatter = MessageFormatter()
            formatted_message = formatter.format_message(data_dict, data['format_template'])

        return jsonify({
            'success': True,
            'data': data_dict,
            'formatted_message': formatted_message,
            'results': {k: {'text': v['text'], 'confidence': v['confidence']} for k, v in results.items()}
        })
    except Exception as e:
        logger.error(f"Error testing extraction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-telegram', methods=['POST'])
def api_test_telegram():
    """Test Telegram connection and send test message"""
    data = request.json
    logger.info("Testing Telegram connection")

    try:
        bot_token = data.get('telegram_bot_token')
        chat_id = data.get('telegram_chat_id')

        if not bot_token or not chat_id:
            return jsonify({'success': False, 'error': 'Bot token and chat ID required'}), 400

        telegram = TelegramSender(bot_token)

        # Test connection
        conn_result = telegram.test_connection()
        if not conn_result['success']:
            return jsonify({'success': False, 'error': conn_result['error']}), 400

        # Send test message
        send_result = telegram.test_send(chat_id)

        return jsonify({
            'success': send_result['success'],
            'bot_username': conn_result.get('username'),
            'message_id': send_result.get('message_id'),
            'error': send_result.get('error')
        })
    except Exception as e:
        logger.error(f"Error testing Telegram: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/run-job/<int:job_id>', methods=['POST'])
def api_run_job(job_id):
    """Manually trigger job execution"""
    logger.info(f"Manual job execution: {job_id}")

    try:
        # Import engine and run
        from engine import AutomationEngine
        engine = AutomationEngine()
        engine.execute_job(job_id)

        return jsonify({'success': True, 'message': 'Job executed'})
    except Exception as e:
        logger.error(f"Error running job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/job/<int:job_id>/data', methods=['GET'])
def api_get_job_data(job_id):
    """Get extracted data for a job"""
    limit = request.args.get('limit', 100, type=int)
    data = db.get_extracted_data(job_id, limit=limit)
    return jsonify(data)


@app.route('/api/job/<int:job_id>/logs', methods=['GET'])
def api_get_job_logs(job_id):
    """Get execution logs for a job"""
    limit = request.args.get('limit', 50, type=int)
    logs = db.get_execution_logs(job_id, limit=limit)
    return jsonify(logs)


@app.route('/api/test-action', methods=['POST'])
def api_test_action():
    """Test a single pre-extraction action immediately"""
    data = request.json
    logger.info(f"Testing single action: {data.get('type')}")

    try:
        executor = get_action_executor()

        # Focus browser first
        browser = get_browser()
        browser.focus_edge_browser()

        # Execute the action
        result = executor.test_action(data)

        return jsonify({
            'success': result.get('success', False),
            'details': result,
            'error': result.get('error')
        })
    except Exception as e:
        logger.error(f"Error testing action: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-actions', methods=['POST'])
def api_test_actions():
    """Test multiple pre-extraction actions in sequence"""
    data = request.json
    actions = data.get('actions', [])
    logger.info(f"Testing {len(actions)} actions")

    try:
        executor = get_action_executor()

        # Focus browser first
        browser = get_browser()
        browser.focus_edge_browser()

        # Execute all actions
        result = executor.execute_actions(actions)

        return jsonify({
            'success': result.get('success', False),
            'actions_executed': result.get('actions_executed', 0),
            'results': result.get('results', [])
        })
    except Exception as e:
        logger.error(f"Error testing actions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CSV JOB API ROUTES ====================

@app.route('/api/csv-job', methods=['POST'])
def api_create_csv_job():
    """Create new CSV analysis job"""
    data = request.json
    logger.info(f"Creating CSV job: {data.get('name')}")

    try:
        # Ensure job_type is set
        data['job_type'] = 'csv_analysis'
        job_id = db.create_job(data)
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        logger.error(f"Error creating CSV job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/test-csv-workflow', methods=['POST'])
def api_test_csv_workflow():
    """Test full CSV download and analysis workflow"""
    data = request.json
    csv_config = data.get('csv_config', {})
    logger.info("Testing CSV workflow")

    try:
        import time

        # Step 1: Execute download actions if any
        download_actions = csv_config.get('download_actions', [])
        if download_actions:
            logger.info(f"Executing {len(download_actions)} download actions")

            executor = get_action_executor()
            browser = get_browser()
            browser.focus_edge_browser()

            result = executor.execute_actions(download_actions)
            if not result.get('success', True):
                logger.warning("Some download actions failed")

            # Wait for download to complete
            time.sleep(5)

        # Step 2: Find and analyze CSV
        csv_analyzer = CSVAnalyzer()

        csv_path = csv_analyzer.find_latest_csv(csv_config.get('csv_filename_pattern', '*.csv'))
        if not csv_path:
            return jsonify({
                'success': False,
                'error': f"CSV file not found matching pattern: {csv_config.get('csv_filename_pattern')}"
            }), 404

        # Analyze prep times
        alerts, date_str = csv_analyzer.analyze_prep_times(csv_path, csv_config)

        # Format preview message
        message_preview = csv_analyzer.format_alert_message(
            alerts,
            date_str,
            csv_config.get('threshold_minutes', 10)
        )

        return jsonify({
            'success': True,
            'csv_file': csv_path,
            'date': date_str,
            'alerts': alerts,
            'message_preview': message_preview
        })

    except Exception as e:
        logger.error(f"Error testing CSV workflow: {e}")
        logger.exception("Full traceback:")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/csv-preview', methods=['POST'])
def api_csv_preview():
    """Get preview of CSV file structure"""
    data = request.json
    pattern = data.get('pattern', '*.csv')
    logger.info(f"Getting CSV preview for pattern: {pattern}")

    try:
        csv_analyzer = CSVAnalyzer()

        csv_path = csv_analyzer.find_latest_csv(pattern)
        if not csv_path:
            return jsonify({
                'success': False,
                'error': f"No CSV file found matching: {pattern}"
            }), 404

        preview = csv_analyzer.get_csv_preview(csv_path)

        return jsonify({
            'success': True,
            'file': csv_path,
            'columns': preview['columns'],
            'sample_data': preview['sample_data']
        })

    except Exception as e:
        logger.error(f"Error getting CSV preview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DOM JOB API ROUTES ====================

@app.route('/api/dom-job', methods=['POST'])
def api_create_dom_job():
    """Create or update DOM extraction job"""
    data = request.json
    logger.info(f"Saving DOM job: {data.get('name')}")

    try:
        # Ensure job_type is set
        data['job_type'] = 'dom_extraction'

        if data.get('id'):
            # Update existing job
            job_id = data['id']
            del data['id']
            db.update_job(job_id, data)
            logger.info(f"Updated DOM job ID: {job_id}")
        else:
            # Create new job
            job_id = db.create_job(data)
            logger.info(f"Created DOM job ID: {job_id}")

        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        logger.error(f"Error saving DOM job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/test-dom-selector', methods=['POST'])
def api_test_dom_selector():
    """Test a CSS selector on current page"""
    data = request.json
    selector = data.get('selector')
    logger.info(f"Testing DOM selector: {selector}")

    try:
        extractor = get_dom_extractor()
        result = extractor.test_selector(selector)

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing DOM selector: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-dom-field', methods=['POST'])
def api_test_dom_field():
    """Test a field selector within a container"""
    data = request.json
    container_selector = data.get('container_selector')
    field_selector = data.get('field_selector')
    field_name = data.get('field_name')
    logger.info(f"Testing DOM field: {field_name}")

    try:
        extractor = get_dom_extractor()
        result = extractor.test_field_selector(
            container_selector=container_selector,
            field_selector=field_selector,
            field_name=field_name
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing DOM field: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test-dom-extraction', methods=['POST'])
def api_test_dom_extraction():
    """Test full DOM extraction with provided configuration"""
    data = request.json
    logger.info("Testing DOM extraction")
    logger.info(f"  URL: {data.get('url')}")
    logger.info(f"  Selectors: {list(data.get('selectors', {}).keys())}")

    try:
        extractor = get_dom_extractor()

        # Execute pre-extraction actions if provided
        pre_actions = data.get('pre_extraction_actions', [])
        if pre_actions:
            logger.info(f"  Executing {len(pre_actions)} pre-extraction actions")
            executor = get_action_executor()
            browser = get_browser()
            browser.focus_edge_browser()
            executor.execute_actions(pre_actions)

        # Extract data
        if data.get('url'):
            extracted = extractor.extract_data(
                url=data['url'],
                selectors=data['selectors'],
                wait_for_selector=data.get('wait_for_selector'),
                wait_time=data.get('wait_time', 2)
            )
        else:
            # Extract from current page
            extracted = extractor.extract_from_current_page(
                selectors=data['selectors'],
                wait_time=data.get('wait_time', 2)
            )

        logger.info(f"  Extracted {len(extracted)} items")

        return jsonify({
            'success': True,
            'data': extracted
        })

    except Exception as e:
        logger.error(f"Error testing DOM extraction: {e}")
        logger.exception("Full traceback:")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dom-page-info', methods=['GET'])
def api_dom_page_info():
    """Get current page information from DOM extractor"""
    try:
        extractor = get_dom_extractor()
        info = extractor.get_page_info()
        return jsonify({'success': True, **info})
    except Exception as e:
        logger.error(f"Error getting page info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-selectors-ai', methods=['POST'])
def api_generate_selectors_ai():
    """
    Use Anthropic Claude to generate CSS selectors from HTML and example data

    User provides:
    - HTML block (one complete item)
    - Example data (actual values from that HTML)
    - Anthropic API key

    Returns:
    - Container selector
    - Field selectors for each data field
    """
    try:
        data = request.json
        html_block = data.get('html_block', '')
        example_data = data.get('example_data', {})
        api_key = data.get('api_key', '')

        logger.info("AI Selector Generation requested")
        logger.info(f"  Fields to extract: {list(example_data.keys())}")

        # Validation
        if not html_block:
            return jsonify({
                'success': False,
                'error': 'HTML block is required'
            }), 400

        if not example_data:
            return jsonify({
                'success': False,
                'error': 'Example data is required'
            }), 400

        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Anthropic API key is required'
            }), 400

        # Call Anthropic API
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Build prompt
        prompt = f"""You are a CSS selector expert. Analyze this HTML block and generate CSS selectors.

HTML Block:
```html
{html_block}
```

Example Data (actual text values from the HTML above):
```json
{json.dumps(example_data, indent=2)}
```

Your task:
1. Identify the outermost container element that wraps this entire item
2. For each field in the example data, find where that EXACT text appears in the HTML
3. Generate a CSS selector that targets that specific element
4. Selectors should be RELATIVE to the container (not absolute paths)

Return ONLY this JSON structure (no explanation):

{{
  "container_selector": "css selector for outer container",
  "field_selectors": {{
    "field1": "selector relative to container",
    "field2": "selector relative to container"
  }}
}}

Important:
- Use class-based selectors when available (e.g., "span.customer-name")
- If no classes, use element + nth-child (e.g., "div:nth-child(2) span")
- Selectors must be relative to container, not document root
- Test that each selector would uniquely identify the element within the container
- Return ONLY the JSON object, no markdown formatting or explanation"""

        # Make API call
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text

        # Extract JSON from response (handle potential markdown formatting)
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)

        if not json_match:
            raise ValueError("Could not find JSON in AI response")

        response_json = json.loads(json_match.group())

        # Validate response structure
        if 'container_selector' not in response_json:
            raise ValueError("Response missing 'container_selector'")

        if 'field_selectors' not in response_json:
            raise ValueError("Response missing 'field_selectors'")

        logger.info(f"  Generated selectors successfully")
        logger.info(f"  Container: {response_json['container_selector']}")
        logger.info(f"  Fields: {list(response_json['field_selectors'].keys())}")

        return jsonify({
            'success': True,
            'container_selector': response_json['container_selector'],
            'field_selectors': response_json['field_selectors']
        })

    except Exception as e:
        error_msg = str(e)
        # Check for common Anthropic errors
        if 'anthropic' in error_msg.lower() or 'api' in error_msg.lower():
            logger.error(f"Anthropic API error: {e}")
        else:
            logger.error(f"AI selector generation failed: {e}")
            logger.exception("Full traceback:")

        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("STARTING AUTOMATION PLATFORM WEB UI")
    logger.info("=" * 60)
    logger.info(f"  URL: http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"  Debug: {FLASK_DEBUG}")
    logger.info("=" * 60)

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )
