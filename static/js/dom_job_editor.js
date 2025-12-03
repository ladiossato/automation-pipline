/**
 * DOM Job Editor JavaScript
 * Handles CSS selector configuration and DOM extraction testing
 */

console.log('='.repeat(50));
console.log('DOM_JOB_EDITOR.JS LOADED SUCCESSFULLY');
console.log('='.repeat(50));

// Field selectors array
let fieldSelectors = [];

// Store last extracted data for telegram testing
let lastExtractedData = [];

// ==================== Field Selector Management ====================

function addFieldSelector(name = '', selector = '') {
    fieldSelectors.push({ name, selector });
    updateFieldSelectorsList();
}

function removeFieldSelector(index) {
    if (fieldSelectors.length > 0) {
        fieldSelectors.splice(index, 1);
        updateFieldSelectorsList();
    }
}

function updateFieldSelectorsList() {
    const list = document.getElementById('fieldSelectorsList');

    if (fieldSelectors.length === 0) {
        // Add one empty row by default
        fieldSelectors.push({ name: '', selector: '' });
    }

    list.innerHTML = fieldSelectors.map((field, index) => `
        <div class="field-selector-row" data-index="${index}">
            <input type="text"
                   class="field-name"
                   placeholder="Field name (e.g., 'price', 'title')"
                   value="${escapeHtml(field.name)}"
                   onchange="updateFieldSelector(${index}, 'name', this.value)">
            <input type="text"
                   class="field-selector"
                   placeholder="CSS selector (e.g., 'span.price', 'h2.title')"
                   value="${escapeHtml(field.selector)}"
                   onchange="updateFieldSelector(${index}, 'selector', this.value)">
            <button type="button" onclick="testFieldSelector(${index})" class="btn-test">Test</button>
            <button type="button" onclick="removeFieldSelector(${index})" class="btn-danger-small">×</button>
        </div>
    `).join('');
}

function updateFieldSelector(index, field, value) {
    if (fieldSelectors[index]) {
        fieldSelectors[index][field] = value;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Selector Testing ====================

async function testContainerSelector() {
    const selector = document.getElementById('selector_container').value.trim();

    if (!selector) {
        alert('Please enter a container selector first');
        return;
    }

    const results = document.getElementById('testResults');
    results.innerHTML = '<p class="loading">Testing container selector...</p>';

    try {
        const response = await fetch('/api/test-dom-selector', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selector })
        });

        const result = await response.json();

        if (result.success) {
            results.innerHTML = `
                <div class="test-success">
                    <h4>Container Selector Test</h4>
                    <p><strong>Found ${result.count} elements</strong> matching "${selector}"</p>
                    ${result.samples.length > 0 ? `
                        <p>Sample content:</p>
                        <ul>
                            ${result.samples.map(s => `<li>${escapeHtml(s.substring(0, 100))}...</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            `;
        } else {
            results.innerHTML = `
                <div class="test-error">
                    <h4>Container Selector Test Failed</h4>
                    <p>${result.error}</p>
                </div>
            `;
        }
    } catch (error) {
        results.innerHTML = `
            <div class="test-error">
                <h4>Test Failed</h4>
                <p>${error.message}</p>
            </div>
        `;
    }
}

async function testFieldSelector(index) {
    console.log('testFieldSelector called with index:', index);
    console.log('fieldSelectors array:', fieldSelectors);

    const field = fieldSelectors[index];
    console.log('Field at index:', field);

    if (!field || !field.name || !field.selector) {
        alert('Please enter both field name and selector');
        return;
    }

    const container = document.getElementById('selector_container').value.trim();
    console.log('Container selector:', container);

    if (!container) {
        alert('Please enter a container selector first');
        return;
    }

    const results = document.getElementById('testResults');
    if (!results) {
        console.error('testResults element not found!');
        alert('Error: Test results container not found');
        return;
    }

    results.innerHTML = `<p class="loading">Testing field selector "${field.name}"...</p>`;
    console.log('Making API call to /api/test-dom-field...');

    try {
        const response = await fetch('/api/test-dom-field', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                container_selector: container,
                field_selector: field.selector,
                field_name: field.name
            })
        });

        const result = await response.json();

        if (result.success) {
            results.innerHTML = `
                <div class="test-success">
                    <h4>Field "${field.name}" Test</h4>
                    <p><strong>Found values in ${result.found_count}/${result.container_count} containers</strong></p>
                    ${result.samples.length > 0 ? `
                        <p>Sample values:</p>
                        <ul>
                            ${result.samples.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                        </ul>
                    ` : '<p>No values found</p>'}
                </div>
            `;
        } else {
            results.innerHTML = `
                <div class="test-error">
                    <h4>Field Test Failed</h4>
                    <p>${result.error}</p>
                </div>
            `;
        }
    } catch (error) {
        results.innerHTML = `
            <div class="test-error">
                <h4>Test Failed</h4>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// ==================== Full Extraction Test ====================

async function testDomExtraction() {
    console.log('='.repeat(60));
    console.log('TEST DOM EXTRACTION BUTTON CLICKED');
    console.log('='.repeat(60));

    // First, ping the server to verify connectivity
    console.log('[STEP 0] Pinging server to verify connectivity...');
    try {
        const pingResponse = await fetch('/api/ping', { method: 'POST' });
        const pingResult = await pingResponse.json();
        console.log('[STEP 0] Ping result:', pingResult);
        if (!pingResult.success) {
            console.error('[STEP 0] Server ping failed!');
            alert('Server is not responding. Check if Flask is running.');
            return;
        }
        console.log('[STEP 0] Server is responding!');
    } catch (pingError) {
        console.error('[STEP 0] Ping failed with error:', pingError);
        alert('Cannot connect to server: ' + pingError.message);
        return;
    }

    console.log('[STEP 1] Gathering DOM config...');
    const config = gatherDomConfig();

    if (!config) {
        console.log('[STEP 1] FAILED - gatherDomConfig returned null/undefined');
        console.log('  Check if selectors are properly configured');
        return;
    }

    console.log('[STEP 1] SUCCESS - Got config:');
    console.log('  URL:', config.url || 'NOT SET');
    console.log('  Selectors:', Object.keys(config.selectors || {}));
    console.log('  Pre-actions count:', (config.pre_extraction_actions || []).length);
    console.log('  Wait time:', config.wait_time);
    console.log('  Full config:', JSON.stringify(config, null, 2));

    const results = document.getElementById('testResults');
    results.innerHTML = '<p class="loading">Testing DOM extraction... (this may take a few seconds)</p>';

    console.log('[STEP 2] Making API request to /api/test-dom-extraction...');

    try {
        const requestBody = JSON.stringify(config);
        console.log('[STEP 2] Request body length:', requestBody.length);
        console.log('[STEP 2] About to call fetch...');

        const response = await fetch('/api/test-dom-extraction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: requestBody
        });

        console.log('[STEP 2] Fetch completed!');

        console.log('[STEP 3] Got response from server');
        console.log('  Status:', response.status);
        console.log('  Status Text:', response.statusText);
        console.log('  OK:', response.ok);

        const result = await response.json();
        console.log('[STEP 3] Parsed JSON response:', result);

        if (result.success) {
            console.log('[STEP 4] SUCCESS - Extracted', result.data.length, 'items');

            // Store extracted data for Telegram testing
            lastExtractedData = result.data;
            console.log('[STEP 4] Stored', lastExtractedData.length, 'items for Telegram testing');

            results.innerHTML = `
                <div class="test-success">
                    <h4>✅ Extraction Successful!</h4>
                    <p><strong>Found ${result.data.length} items</strong></p>
                    <div class="extracted-data">
                        ${result.data.slice(0, 5).map((item, i) => `
                            <div class="data-item">
                                <strong>Item ${i + 1}:</strong>
                                <pre>${JSON.stringify(item, null, 2)}</pre>
                            </div>
                        `).join('')}
                        ${result.data.length > 5 ? `<p class="help-text">Showing first 5 of ${result.data.length} items</p>` : ''}
                    </div>
                </div>
            `;

            // Show the Telegram test button
            const telegramBtn = document.getElementById('testTelegramBtn');
            if (telegramBtn) {
                telegramBtn.style.display = 'inline-block';
                console.log('[STEP 4] Telegram test button shown');
            }

            // Update format preview with sample data
            if (result.data.length > 0) {
                updateFormatPreview(result.data[0]);
            }
        } else {
            console.log('[STEP 4] FAILED - Server returned error:', result.error);
            results.innerHTML = `
                <div class="test-error">
                    <h4>Extraction Failed</h4>
                    <p><strong>Error:</strong> ${result.error}</p>
                    <details>
                        <summary>Troubleshooting tips</summary>
                        <ul>
                            <li>Make sure your browser is on the target page</li>
                            <li>Check that container selector matches elements on page</li>
                            <li>Verify field selectors are relative to container</li>
                            <li>Try testing selectors in DevTools Console first</li>
                        </ul>
                    </details>
                </div>
            `;
        }
    } catch (error) {
        console.log('='.repeat(60));
        console.log('TEST DOM EXTRACTION - JAVASCRIPT ERROR');
        console.log('='.repeat(60));
        console.error('Error:', error);
        console.error('Error name:', error.name);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        results.innerHTML = `
            <div class="test-error">
                <h4>Request Failed</h4>
                <p>${error.message}</p>
            </div>
        `;
    }

    console.log('='.repeat(60));
    console.log('TEST DOM EXTRACTION FUNCTION COMPLETE');
    console.log('='.repeat(60));
}

function updateFormatPreview(sampleData) {
    const template = document.getElementById('format_template').value;
    const preview = document.getElementById('formatPreview');

    if (!template || !sampleData) {
        preview.innerHTML = '';
        return;
    }

    let formatted = template;
    for (const [key, value] of Object.entries(sampleData)) {
        formatted = formatted.replace(new RegExp(`\\{${key}\\}`, 'g'), value || '');
    }

    preview.innerHTML = `
        <h4>Message Preview:</h4>
        <pre>${escapeHtml(formatted)}</pre>
    `;
}

// ==================== AI Transform Toggle ====================

function toggleAiTransformSettings() {
    const checkbox = document.getElementById('enable_ai_transform');
    const settings = document.getElementById('aiTransformSettings');

    if (checkbox && settings) {
        settings.style.display = checkbox.checked ? 'block' : 'none';
    }
}

// Make it globally accessible
window.toggleAiTransformSettings = toggleAiTransformSettings;

// ==================== Configuration Gathering ====================

function gatherDomConfig() {
    console.log('[gatherDomConfig] Starting to gather configuration...');

    const containerSelector = document.getElementById('selector_container').value.trim();
    console.log('[gatherDomConfig] Container selector:', containerSelector || 'EMPTY');

    if (!containerSelector) {
        console.log('[gatherDomConfig] ERROR - No container selector provided');
        alert('Please enter a container selector');
        return null;
    }

    // Build selectors object
    const selectors = { container: containerSelector };

    console.log('[gatherDomConfig] fieldSelectors array:', fieldSelectors);
    console.log('[gatherDomConfig] fieldSelectors length:', fieldSelectors ? fieldSelectors.length : 'undefined');

    let hasFields = false;
    if (fieldSelectors && fieldSelectors.length > 0) {
        fieldSelectors.forEach((field, index) => {
            console.log(`[gatherDomConfig] Field ${index}:`, field);
            if (field.name && field.selector) {
                selectors[field.name] = field.selector;
                hasFields = true;
            }
        });
    }

    console.log('[gatherDomConfig] hasFields:', hasFields);
    console.log('[gatherDomConfig] Final selectors object:', selectors);

    if (!hasFields) {
        console.log('[gatherDomConfig] ERROR - No field selectors defined');
        alert('Please define at least one field selector');
        return null;
    }

    // Get AI transformation settings
    const enableAiTransform = document.getElementById('enable_ai_transform');
    const aiTransformApiKey = document.getElementById('ai_transform_api_key');
    const aiTransformPrompt = document.getElementById('ai_transform_prompt');

    const config = {
        url: document.getElementById('url').value.trim(),
        selectors: selectors,
        wait_for_selector: document.getElementById('wait_for_selector').value.trim() || null,
        wait_time: parseInt(document.getElementById('wait_time').value) || 2,
        pre_extraction_actions: preExtractionActions || [],
        // AI transformation settings
        anthropic_api_key: (enableAiTransform && enableAiTransform.checked && aiTransformApiKey) ? aiTransformApiKey.value.trim() : '',
        ai_transform_prompt: (enableAiTransform && enableAiTransform.checked && aiTransformPrompt) ? aiTransformPrompt.value.trim() : ''
    };

    console.log('[gatherDomConfig] SUCCESS - Final config:', config);
    console.log('[gatherDomConfig] AI Transform enabled:', enableAiTransform ? enableAiTransform.checked : false);
    return config;
}

// ==================== Job Save ====================

async function saveDomJob(event) {
    event.preventDefault();

    const config = gatherDomConfig();
    if (!config) return;

    const jobData = {
        id: document.getElementById('job_id').value || null,
        name: document.getElementById('name').value.trim(),
        url: config.url,
        job_type: 'dom_extraction',
        dom_config: config,
        format_template: document.getElementById('format_template').value,
        telegram_bot_token: document.getElementById('telegram_bot_token').value.trim(),
        telegram_chat_id: document.getElementById('telegram_chat_id').value.trim(),
        enable_deduplication: document.getElementById('enable_deduplication').checked,
        schedule_interval_hours: parseInt(document.getElementById('schedule_interval_hours').value),
        active: document.getElementById('active').checked,
        pre_extraction_actions: preExtractionActions || []
    };

    try {
        const response = await fetch('/api/dom-job', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jobData)
        });

        const result = await response.json();

        if (result.success) {
            alert('DOM Job saved successfully!');
            window.location.href = '/';
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Request failed: ' + error.message);
    }
}

// ==================== AI Selector Generation ====================

async function generateSelectorsWithAI() {
    console.log('='.repeat(50));
    console.log('=== AI SELECTOR GENERATION STARTED ===');
    console.log('='.repeat(50));
    console.log('Function called at:', new Date().toISOString());

    // STEP 1: Get DOM elements
    console.log('[STEP 1] Getting DOM elements...');
    const htmlBlockEl = document.getElementById('htmlBlock');
    const exampleDataEl = document.getElementById('exampleData');
    const apiKeyEl = document.getElementById('anthropicApiKey');
    const resultsDiv = document.getElementById('aiResults');

    console.log('  htmlBlock element:', htmlBlockEl ? 'FOUND' : 'NOT FOUND');
    console.log('  exampleData element:', exampleDataEl ? 'FOUND' : 'NOT FOUND');
    console.log('  apiKey element:', apiKeyEl ? 'FOUND' : 'NOT FOUND');
    console.log('  aiResults element:', resultsDiv ? 'FOUND' : 'NOT FOUND');

    if (!resultsDiv) {
        console.error('CRITICAL: aiResults div not found!');
        alert('Error: Results container not found. Please refresh the page.');
        return;
    }

    // Show loading IMMEDIATELY (before any validation)
    console.log('[STEP 1.5] Showing loading indicator IMMEDIATELY...');
    resultsDiv.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>Starting AI selector generation...</p>
            <p class="help-text">Validating inputs...</p>
        </div>
    `;

    // STEP 2: Get values
    console.log('[STEP 2] Getting input values...');
    const htmlBlock = htmlBlockEl ? htmlBlockEl.value.trim() : '';
    const exampleDataText = exampleDataEl ? exampleDataEl.value.trim() : '';
    const apiKey = apiKeyEl ? apiKeyEl.value.trim() : '';

    console.log('  htmlBlock length:', htmlBlock.length, 'chars');
    console.log('  exampleData length:', exampleDataText.length, 'chars');
    console.log('  apiKey length:', apiKey.length, 'chars');
    console.log('  apiKey starts with:', apiKey.substring(0, 10) + '...');

    // STEP 3: Validation
    console.log('[STEP 3] Validating inputs...');

    if (!htmlBlock) {
        console.log('  VALIDATION FAILED: No HTML block');
        resultsDiv.innerHTML = '<div class="ai-error"><p>Please paste an HTML block first</p></div>';
        alert('Please paste an HTML block first');
        return;
    }
    console.log('  HTML block: OK');

    if (!exampleDataText) {
        console.log('  VALIDATION FAILED: No example data');
        resultsDiv.innerHTML = '<div class="ai-error"><p>Please provide example data</p></div>';
        alert('Please provide example data (the actual values from your HTML)');
        return;
    }
    console.log('  Example data text: OK');

    if (!apiKey) {
        console.log('  VALIDATION FAILED: No API key');
        resultsDiv.innerHTML = '<div class="ai-error"><p>Please enter your API key</p></div>';
        alert('Please enter your Anthropic API key\n\nGet one at: https://console.anthropic.com');
        return;
    }
    console.log('  API key: OK');

    // STEP 4: Parse example data
    console.log('[STEP 4] Parsing example data JSON...');
    let exampleData;
    try {
        exampleData = JSON.parse(exampleDataText);
        console.log('  JSON parsed successfully');
        console.log('  Fields found:', Object.keys(exampleData));
    } catch (e) {
        console.error('  JSON PARSE ERROR:', e.message);
        resultsDiv.innerHTML = '<div class="ai-error"><p>Example data must be valid JSON</p></div>';
        alert('Example data must be valid JSON\n\nMake sure you have:\n- Quotes around field names\n- Quotes around text values\n- Commas between fields\n\nExample:\n{\n  "field": "value",\n  "field2": "value2"\n}');
        return;
    }

    // STEP 5: Update loading state
    console.log('[STEP 5] Showing full loading state...');
    resultsDiv.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>AI is analyzing your HTML and generating selectors...</p>
            <p class="help-text">This usually takes 5-10 seconds</p>
        </div>
    `;

    // STEP 6: Make API request
    console.log('[STEP 6] Making fetch request to /api/generate-selectors-ai...');
    console.log('  Request payload:', {
        html_block_length: htmlBlock.length,
        example_data_fields: Object.keys(exampleData),
        api_key_prefix: apiKey.substring(0, 10) + '...'
    });

    try {
        const response = await fetch('/api/generate-selectors-ai', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                html_block: htmlBlock,
                example_data: exampleData,
                api_key: apiKey
            })
        });

        console.log('[STEP 7] Response received');
        console.log('  Status:', response.status);
        console.log('  Status text:', response.statusText);
        console.log('  OK:', response.ok);

        if (!response.ok) {
            console.error('[STEP 7] HTTP ERROR - Response not OK');
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        console.log('[STEP 8] Parsing response JSON...');
        const result = await response.json();
        console.log('  Response parsed successfully');
        console.log('  Result success:', result.success);
        console.log('  Result keys:', Object.keys(result));

        if (result.success) {
            console.log('[STEP 9] SUCCESS - Displaying results');
            console.log('  Container selector:', result.container_selector);
            console.log('  Field selectors:', result.field_selectors);

            // Store results for applying
            window.generatedSelectors = result;

            // Display results
            resultsDiv.innerHTML = `
                <div class="ai-success">
                    <h4>Selectors Generated Successfully!</h4>

                    <div class="selector-preview">
                        <div class="selector-item">
                            <strong>Container Selector:</strong>
                            <code>${escapeHtml(result.container_selector)}</code>
                        </div>

                        <div class="selector-item">
                            <strong>Field Selectors:</strong>
                            <ul class="field-list">
                                ${Object.entries(result.field_selectors).map(([field, selector]) => `
                                    <li>
                                        <span class="field-name">${escapeHtml(field)}</span>
                                        <code>${escapeHtml(selector)}</code>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>

                    <div class="action-buttons">
                        <button type="button" onclick="applyAISelectors()" class="btn-primary">
                            Apply These Selectors
                        </button>
                        <button type="button" onclick="regenerateSelectors()" class="btn-secondary">
                            Regenerate
                        </button>
                    </div>
                </div>
            `;
            console.log('[STEP 9] Results displayed successfully');
        } else {
            console.log('[STEP 9] FAILURE - API returned error');
            console.log('  Error:', result.error);

            resultsDiv.innerHTML = `
                <div class="ai-error">
                    <h4>Generation Failed</h4>
                    <p><strong>Error:</strong> ${escapeHtml(result.error)}</p>
                    <details>
                        <summary>Troubleshooting tips</summary>
                        <ul>
                            <li>Make sure the HTML block is complete and valid</li>
                            <li>Verify the example data values exist in the HTML</li>
                            <li>Check that your API key is valid</li>
                            <li>Try with a simpler HTML block first</li>
                        </ul>
                    </details>
                    <button type="button" onclick="generateSelectorsWithAI()" class="btn-secondary">
                        Try Again
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('[STEP ERROR] Exception caught:', error);
        console.error('  Error name:', error.name);
        console.error('  Error message:', error.message);
        console.error('  Error stack:', error.stack);

        resultsDiv.innerHTML = `
            <div class="ai-error">
                <h4>Request Failed</h4>
                <p><strong>Error:</strong> ${escapeHtml(error.message)}</p>
                <p>Check your internet connection and API key, then try again.</p>
                <p class="help-text">Check browser console for detailed error info</p>
                <button type="button" onclick="generateSelectorsWithAI()" class="btn-secondary">
                    Try Again
                </button>
            </div>
        `;
    }

    console.log('='.repeat(50));
    console.log('=== AI SELECTOR GENERATION COMPLETE ===');
    console.log('='.repeat(50));
}

function applyAISelectors() {
    const result = window.generatedSelectors;

    if (!result) {
        alert('No selectors to apply');
        return;
    }

    // Apply container selector
    document.getElementById('selector_container').value = result.container_selector;

    // Clear existing field selectors and populate with AI results
    fieldSelectors = [];
    for (const [fieldName, selector] of Object.entries(result.field_selectors)) {
        fieldSelectors.push({ name: fieldName, selector: selector });
    }
    updateFieldSelectorsList();

    // Open the manual selectors section so user can see what was applied
    const detailsEl = document.querySelector('.manual-selectors-section');
    if (detailsEl) {
        detailsEl.open = true;
    }

    // Scroll to test section
    const testSection = document.querySelector('.test-section');
    if (testSection) {
        testSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Show success message
    const resultsDiv = document.getElementById('aiResults');
    resultsDiv.innerHTML = `
        <div class="ai-success">
            <p><strong>Selectors applied!</strong> Scroll down to "Test Extraction" to verify they work.</p>
        </div>
    `;
}

function regenerateSelectors() {
    document.getElementById('aiResults').innerHTML = '';
    document.getElementById('htmlBlock').focus();
}

// ==================== Telegram Test with Extracted Data ====================

async function testTelegramWithData() {
    console.log('='.repeat(60));
    console.log('TEST TELEGRAM WITH EXTRACTED DATA');
    console.log('='.repeat(60));

    const telegramResults = document.getElementById('telegramTestResults');

    // Check if we have extracted data
    if (!lastExtractedData || lastExtractedData.length === 0) {
        console.log('[ERROR] No extracted data available');
        telegramResults.innerHTML = `
            <div class="test-error">
                <h4>No Data Available</h4>
                <p>Please run "Test Extraction Now" first to get data for the Telegram message.</p>
            </div>
        `;
        return;
    }

    // Get Telegram config
    const botToken = document.getElementById('telegram_bot_token').value.trim();
    const chatId = document.getElementById('telegram_chat_id').value.trim();
    const formatTemplate = document.getElementById('format_template').value.trim();

    console.log('[CONFIG] Bot token:', botToken ? botToken.substring(0, 15) + '...' : 'NOT SET');
    console.log('[CONFIG] Chat ID:', chatId || 'NOT SET');
    console.log('[CONFIG] Template length:', formatTemplate.length, 'chars');
    console.log('[CONFIG] Extracted items:', lastExtractedData.length);

    // Validate inputs
    if (!botToken) {
        alert('Please enter your Telegram Bot Token in the Telegram Alerts section');
        document.getElementById('telegram_bot_token').focus();
        return;
    }

    if (!chatId) {
        alert('Please enter your Telegram Chat ID in the Telegram Alerts section');
        document.getElementById('telegram_chat_id').focus();
        return;
    }

    if (!formatTemplate) {
        alert('Please enter a message format template in the Message Format section');
        document.getElementById('format_template').focus();
        return;
    }

    // Show loading
    telegramResults.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>Sending test message to Telegram...</p>
            <p class="help-text">Using ${Math.min(lastExtractedData.length, 3)} of ${lastExtractedData.length} extracted items</p>
        </div>
    `;

    try {
        console.log('[API] Making request to /api/test-telegram-with-data...');

        const response = await fetch('/api/test-telegram-with-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_bot_token: botToken,
                telegram_chat_id: chatId,
                format_template: formatTemplate,
                extracted_data: lastExtractedData
            })
        });

        console.log('[API] Response status:', response.status);

        const result = await response.json();
        console.log('[API] Response:', result);

        if (result.success) {
            console.log('[SUCCESS] Messages sent:', result.messages_sent);

            telegramResults.innerHTML = `
                <div class="test-success">
                    <h4>📱 Telegram Test Successful!</h4>
                    <p><strong>${result.messages_sent} message(s) sent</strong> to chat ${chatId}</p>
                    <p class="help-text">Bot: @${result.bot_username || 'unknown'}</p>
                    ${result.messages && result.messages.length > 0 ? `
                        <details>
                            <summary>Message previews</summary>
                            <div class="message-previews">
                                ${result.messages.map((msg, i) => `
                                    <div class="message-preview">
                                        <strong>Message ${msg.item_index}:</strong>
                                        <pre>${escapeHtml(msg.preview)}</pre>
                                    </div>
                                `).join('')}
                            </div>
                        </details>
                    ` : ''}
                    ${result.errors && result.errors.length > 0 ? `
                        <div class="test-warning">
                            <p><strong>Some messages failed:</strong></p>
                            <ul>
                                ${result.errors.map(err => `<li>Item ${err.item_index}: ${escapeHtml(err.error)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            console.log('[ERROR] API returned error:', result.error);

            telegramResults.innerHTML = `
                <div class="test-error">
                    <h4>❌ Telegram Test Failed</h4>
                    <p><strong>Error:</strong> ${escapeHtml(result.error)}</p>
                    <details>
                        <summary>Troubleshooting tips</summary>
                        <ul>
                            <li>Check that your bot token is correct (from @BotFather)</li>
                            <li>Verify the chat ID is correct</li>
                            <li>Make sure the bot has permission to send messages to the chat</li>
                            <li>If using a channel, add the bot as an admin</li>
                            <li>Check your message format for syntax errors</li>
                        </ul>
                    </details>
                </div>
            `;
        }
    } catch (error) {
        console.error('[ERROR] Exception:', error);

        telegramResults.innerHTML = `
            <div class="test-error">
                <h4>❌ Request Failed</h4>
                <p><strong>Error:</strong> ${escapeHtml(error.message)}</p>
                <p>Check the browser console and server logs for more details.</p>
            </div>
        `;
    }

    console.log('='.repeat(60));
    console.log('TELEGRAM TEST COMPLETE');
    console.log('='.repeat(60));
}

// ==================== Initialize ====================

// preExtractionActions is already declared in action_editor.js
// No need to redeclare it here

// ==================== MAKE FUNCTIONS GLOBALLY ACCESSIBLE ====================
// This ensures onclick handlers can find these functions
window.generateSelectorsWithAI = generateSelectorsWithAI;
window.applyAISelectors = applyAISelectors;
window.regenerateSelectors = regenerateSelectors;
window.addFieldSelector = addFieldSelector;
window.removeFieldSelector = removeFieldSelector;
window.updateFieldSelector = updateFieldSelector;
window.updateFieldSelectorsList = updateFieldSelectorsList;
window.testFieldSelector = testFieldSelector;
window.testContainerSelector = testContainerSelector;
window.testDomExtraction = testDomExtraction;
window.testTelegramWithData = testTelegramWithData;
window.saveDomJob = saveDomJob;
window.escapeHtml = escapeHtml;
window.gatherDomConfig = gatherDomConfig;

console.log('DOM_JOB_EDITOR.JS: All functions attached to window object');
console.log('  generateSelectorsWithAI:', typeof window.generateSelectorsWithAI);
console.log('  testFieldSelector:', typeof window.testFieldSelector);
console.log('  testDomExtraction:', typeof window.testDomExtraction);

// Initialize field selectors on load
document.addEventListener('DOMContentLoaded', function() {
    if (fieldSelectors.length === 0) {
        addFieldSelector();
    }
    updateFieldSelectorsList();
});
