/**
 * DOM Job Editor JavaScript
 * Handles CSS selector configuration and DOM extraction testing
 */

// Field selectors array
let fieldSelectors = [];

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
    const field = fieldSelectors[index];

    if (!field.name || !field.selector) {
        alert('Please enter both field name and selector');
        return;
    }

    const container = document.getElementById('selector_container').value.trim();
    if (!container) {
        alert('Please enter a container selector first');
        return;
    }

    const results = document.getElementById('testResults');
    results.innerHTML = `<p class="loading">Testing field selector "${field.name}"...</p>`;

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
    const config = gatherDomConfig();

    if (!config) return;

    const results = document.getElementById('testResults');
    results.innerHTML = '<p class="loading">Testing DOM extraction... (this may take a few seconds)</p>';

    try {
        const response = await fetch('/api/test-dom-extraction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (result.success) {
            results.innerHTML = `
                <div class="test-success">
                    <h4>Extraction Successful!</h4>
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

            // Update format preview with sample data
            if (result.data.length > 0) {
                updateFormatPreview(result.data[0]);
            }
        } else {
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
        results.innerHTML = `
            <div class="test-error">
                <h4>Request Failed</h4>
                <p>${error.message}</p>
            </div>
        `;
    }
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

// ==================== Configuration Gathering ====================

function gatherDomConfig() {
    const containerSelector = document.getElementById('selector_container').value.trim();

    if (!containerSelector) {
        alert('Please enter a container selector');
        return null;
    }

    // Build selectors object
    const selectors = { container: containerSelector };

    let hasFields = false;
    fieldSelectors.forEach(field => {
        if (field.name && field.selector) {
            selectors[field.name] = field.selector;
            hasFields = true;
        }
    });

    if (!hasFields) {
        alert('Please define at least one field selector');
        return null;
    }

    return {
        url: document.getElementById('url').value.trim(),
        selectors: selectors,
        wait_for_selector: document.getElementById('wait_for_selector').value.trim() || null,
        wait_time: parseInt(document.getElementById('wait_time').value) || 2,
        pre_extraction_actions: preExtractionActions || []
    };
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
    const htmlBlock = document.getElementById('htmlBlock').value.trim();
    const exampleDataText = document.getElementById('exampleData').value.trim();
    const apiKey = document.getElementById('anthropicApiKey').value.trim();
    const resultsDiv = document.getElementById('aiResults');

    // Validation
    if (!htmlBlock) {
        alert('Please paste an HTML block first');
        return;
    }

    if (!exampleDataText) {
        alert('Please provide example data (the actual values from your HTML)');
        return;
    }

    if (!apiKey) {
        alert('Please enter your Anthropic API key\n\nGet one at: https://console.anthropic.com');
        return;
    }

    // Parse example data
    let exampleData;
    try {
        exampleData = JSON.parse(exampleDataText);
    } catch (e) {
        alert('Example data must be valid JSON\n\nMake sure you have:\n- Quotes around field names\n- Quotes around text values\n- Commas between fields\n\nExample:\n{\n  "field": "value",\n  "field2": "value2"\n}');
        return;
    }

    // Show loading state
    resultsDiv.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>AI is analyzing your HTML and generating selectors...</p>
            <p class="help-text">This usually takes 5-10 seconds</p>
        </div>
    `;

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

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
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
        } else {
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
        resultsDiv.innerHTML = `
            <div class="ai-error">
                <h4>Request Failed</h4>
                <p><strong>Error:</strong> ${escapeHtml(error.message)}</p>
                <p>Check your internet connection and API key, then try again.</p>
                <button type="button" onclick="generateSelectorsWithAI()" class="btn-secondary">
                    Try Again
                </button>
            </div>
        `;
    }
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

// ==================== Initialize ====================

// Make sure preExtractionActions exists
if (typeof preExtractionActions === 'undefined') {
    var preExtractionActions = [];
}

// Initialize field selectors on load
document.addEventListener('DOMContentLoaded', function() {
    if (fieldSelectors.length === 0) {
        addFieldSelector();
    }
    updateFieldSelectorsList();
});
