/**
 * Action Editor Module
 * Handles pre-extraction action configuration
 */

let preExtractionActions = [];
let editingActionIndex = -1;
let currentActionType = 'click_coordinates';

/**
 * Show the add action modal (used by both OCR and DOM job editors)
 */
function showAddActionModal() {
    console.log('showAddActionModal called');
    editingActionIndex = -1;

    const modal = document.getElementById('actionModal');
    const modalTitle = document.getElementById('actionModalTitle');

    console.log('Modal element:', modal);
    console.log('Modal title element:', modalTitle);

    if (!modal) {
        console.error('Action modal not found!');
        alert('Error: Action modal not found. Please refresh the page.');
        return;
    }

    if (modalTitle) {
        modalTitle.textContent = 'Add Action';
    }

    // Reset the action type dropdown to default
    const actionTypeSelect = document.getElementById('actionType');
    if (actionTypeSelect) {
        actionTypeSelect.value = 'click_coordinates';
    }

    // Reset wait after field
    const waitAfterInput = document.getElementById('actionWaitAfter');
    if (waitAfterInput) {
        waitAfterInput.value = '2';
    }

    // Update the form fields for the default action type
    updateActionForm();

    // Show the modal
    modal.style.display = 'flex';
}

/**
 * Show the add action modal with a specific action type pre-selected
 * @param {string} actionType - Type of action to add
 */
function showActionModal(actionType) {
    editingActionIndex = -1;

    const modal = document.getElementById('actionModal');
    const modalTitle = document.getElementById('actionModalTitle');

    if (!modal) {
        console.error('Action modal not found!');
        alert('Error: Action modal not found. Please refresh the page.');
        return;
    }

    if (modalTitle) {
        modalTitle.textContent = 'Add Action';
    }

    // Set the action type in dropdown
    const actionTypeSelect = document.getElementById('actionType');
    if (actionTypeSelect) {
        actionTypeSelect.value = actionType || 'click_coordinates';
    }

    // Reset wait after field
    const waitAfterInput = document.getElementById('actionWaitAfter');
    if (waitAfterInput) {
        waitAfterInput.value = '2';
    }

    // Update the form fields for the selected action type
    updateActionForm();

    // Show the modal
    modal.style.display = 'flex';
}

/**
 * Show edit action modal
 */
function editAction(index) {
    editingActionIndex = index;
    const action = preExtractionActions[index];

    document.getElementById('actionModalTitle').textContent = 'Edit Action';
    document.getElementById('actionType').value = action.type;
    document.getElementById('actionWaitAfter').value = action.wait_after || 2;

    updateActionForm();

    // Fill in the existing values
    setTimeout(() => {
        if (action.type === 'click_coordinates') {
            document.getElementById('clickX').value = action.x || 0;
            document.getElementById('clickY').value = action.y || 0;
        } else if (action.type === 'click_ocr') {
            document.getElementById('searchText').value = action.search_text || '';
            document.getElementById('confidenceThreshold').value = action.confidence_threshold || 0.7;
        } else if (action.type === 'wait') {
            document.getElementById('waitDuration').value = action.duration || 1;
        } else if (action.type === 'scroll') {
            document.getElementById('scrollDirection').value = action.direction || 'down';
            document.getElementById('scrollAmount').value = action.amount || 300;
        } else if (action.type === 'press_key') {
            document.getElementById('keyName').value = action.key || '';
        }
    }, 50);

    document.getElementById('actionModal').style.display = 'flex';
}

/**
 * Close the action modal
 */
function closeActionModal() {
    document.getElementById('actionModal').style.display = 'none';
    editingActionIndex = -1;
}

/**
 * Update the action form fields based on selected type
 */
function updateActionForm() {
    const actionTypeEl = document.getElementById('actionType');
    const container = document.getElementById('actionFormFields');

    // Check if required elements exist
    if (!actionTypeEl || !container) {
        console.warn('Action form elements not found');
        return;
    }

    const type = actionTypeEl.value;
    let html = '';

    if (type === 'click_coordinates') {
        html = `
            <div class="form-row">
                <div class="form-group">
                    <label for="clickX">X Coordinate</label>
                    <input type="number" id="clickX" value="0" min="0">
                </div>
                <div class="form-group">
                    <label for="clickY">Y Coordinate</label>
                    <input type="number" id="clickY" value="0" min="0">
                </div>
            </div>
            <p class="help-text">Tip: Capture screen first, then hover over the target to get coordinates</p>
            <button type="button" class="btn btn-small" onclick="pickCoordinates()">Pick from Screen</button>
        `;
    } else if (type === 'click_ocr') {
        html = `
            <div class="form-group">
                <label for="searchText">Text to Find</label>
                <input type="text" id="searchText" placeholder="e.g., View Details, Next, Submit">
                <small>The system will find this text on screen and click it</small>
            </div>
            <div class="form-group">
                <label for="confidenceThreshold">Confidence Threshold</label>
                <input type="number" id="confidenceThreshold" value="0.7" min="0" max="1" step="0.1">
                <small>Minimum OCR confidence (0.7 = 70%)</small>
            </div>
        `;
    } else if (type === 'wait') {
        html = `
            <div class="form-group">
                <label for="waitDuration">Duration (seconds)</label>
                <input type="number" id="waitDuration" value="2" min="0.5" step="0.5">
                <small>Time to wait before next action</small>
            </div>
        `;
    } else if (type === 'scroll') {
        html = `
            <div class="form-row">
                <div class="form-group">
                    <label for="scrollDirection">Direction</label>
                    <select id="scrollDirection">
                        <option value="down">Down</option>
                        <option value="up">Up</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="scrollAmount">Amount (pixels)</label>
                    <input type="number" id="scrollAmount" value="300" min="100" step="100">
                </div>
            </div>
        `;
    } else if (type === 'press_key') {
        html = `
            <div class="form-group">
                <label for="keyName">Key</label>
                <select id="keyName">
                    <option value="enter">Enter</option>
                    <option value="tab">Tab</option>
                    <option value="escape">Escape</option>
                    <option value="space">Space</option>
                    <option value="backspace">Backspace</option>
                    <option value="delete">Delete</option>
                    <option value="up">Arrow Up</option>
                    <option value="down">Arrow Down</option>
                    <option value="left">Arrow Left</option>
                    <option value="right">Arrow Right</option>
                    <option value="pageup">Page Up</option>
                    <option value="pagedown">Page Down</option>
                    <option value="home">Home</option>
                    <option value="end">End</option>
                    <option value="f5">F5 (Refresh)</option>
                </select>
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * Pick coordinates from captured screen
 */
function pickCoordinates() {
    if (!currentScreenshot) {
        alert('Please capture the screen first in the OCR Regions section');
        return;
    }

    alert('Click on the captured screenshot below to pick coordinates.\n\nAfter clicking, the coordinates will be filled in.');

    const img = document.getElementById('screenshotImg');
    if (!img) {
        alert('Screenshot not found. Please capture the screen first.');
        return;
    }

    // Add one-time click handler
    const overlay = document.getElementById('selectionOverlay');

    const clickHandler = (e) => {
        const rect = img.getBoundingClientRect();
        const scaleX = screenshotWidth / img.width;
        const scaleY = screenshotHeight / img.height;

        const x = Math.round((e.clientX - rect.left) * scaleX);
        const y = Math.round((e.clientY - rect.top) * scaleY);

        document.getElementById('clickX').value = x;
        document.getElementById('clickY').value = y;

        alert(`Coordinates set: (${x}, ${y})`);

        overlay.removeEventListener('click', clickHandler);
    };

    overlay.addEventListener('click', clickHandler, { once: true });

    // Scroll to screenshot
    document.getElementById('screenPreview').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Build action object from form fields
 */
function buildActionFromForm() {
    const type = document.getElementById('actionType').value;
    const waitAfter = parseFloat(document.getElementById('actionWaitAfter').value) || 2;

    let action = { type, wait_after: waitAfter };

    if (type === 'click_coordinates') {
        action.x = parseInt(document.getElementById('clickX').value) || 0;
        action.y = parseInt(document.getElementById('clickY').value) || 0;
    } else if (type === 'click_ocr') {
        action.search_text = document.getElementById('searchText').value;
        action.confidence_threshold = parseFloat(document.getElementById('confidenceThreshold').value) || 0.7;
        if (!action.search_text) {
            alert('Please enter text to search for');
            return null;
        }
    } else if (type === 'wait') {
        action.duration = parseFloat(document.getElementById('waitDuration').value) || 1;
        action.wait_after = 0; // Wait action doesn't need additional wait
    } else if (type === 'scroll') {
        action.direction = document.getElementById('scrollDirection').value;
        action.amount = parseInt(document.getElementById('scrollAmount').value) || 300;
    } else if (type === 'press_key') {
        action.key = document.getElementById('keyName').value;
    }

    return action;
}

/**
 * Save the current action
 */
function saveAction() {
    const action = buildActionFromForm();
    if (!action) return;

    if (editingActionIndex >= 0) {
        preExtractionActions[editingActionIndex] = action;
    } else {
        preExtractionActions.push(action);
    }

    updateActionsList();
    closeActionModal();
}

/**
 * Save the current action (alias for DOM job editor compatibility)
 */
function saveCurrentAction() {
    saveAction();
}

/**
 * Test the current action configuration
 */
async function testCurrentAction() {
    const action = buildActionFromForm();
    if (!action) return;

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Testing...';

    try {
        const response = await fetch('/api/test-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(action)
        });

        const result = await response.json();

        if (result.success) {
            alert('Action executed successfully!');
        } else {
            alert('Action failed: ' + (result.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Error testing action: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Test Action';
    }
}

/**
 * Test all actions in sequence
 */
async function testAllActions() {
    if (preExtractionActions.length === 0) {
        alert('No actions to test');
        return;
    }

    const btn = document.getElementById('testAllActionsBtn');
    btn.disabled = true;
    btn.textContent = 'Testing...';

    try {
        const response = await fetch('/api/test-actions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions: preExtractionActions })
        });

        const result = await response.json();

        if (result.success) {
            alert(`All ${result.actions_executed} actions executed successfully!`);
        } else {
            alert('Some actions failed. Check the console for details.');
        }
    } catch (e) {
        alert('Error testing actions: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Test All Actions';
    }
}

/**
 * Delete an action
 */
function deleteAction(index) {
    if (!confirm('Delete this action?')) return;

    preExtractionActions.splice(index, 1);
    updateActionsList();
}

/**
 * Move action up in the list
 */
function moveActionUp(index) {
    if (index <= 0) return;

    const temp = preExtractionActions[index];
    preExtractionActions[index] = preExtractionActions[index - 1];
    preExtractionActions[index - 1] = temp;

    updateActionsList();
}

/**
 * Move action down in the list
 */
function moveActionDown(index) {
    if (index >= preExtractionActions.length - 1) return;

    const temp = preExtractionActions[index];
    preExtractionActions[index] = preExtractionActions[index + 1];
    preExtractionActions[index + 1] = temp;

    updateActionsList();
}

/**
 * Get human-readable description of action
 */
function getActionDescription(action) {
    switch (action.type) {
        case 'click_coordinates':
            return `Click at (${action.x}, ${action.y})`;
        case 'click_ocr':
            return `Click text "${action.search_text}"`;
        case 'wait':
            return `Wait ${action.duration}s`;
        case 'scroll':
            return `Scroll ${action.direction} ${action.amount}px`;
        case 'press_key':
            return `Press ${action.key.toUpperCase()}`;
        default:
            return action.type;
    }
}

/**
 * Get action type icon
 */
function getActionIcon(type) {
    switch (type) {
        case 'click_coordinates':
        case 'click_ocr':
            return '&#128433;'; // Mouse pointer
        case 'wait':
            return '&#9202;'; // Timer
        case 'scroll':
            return '&#8597;'; // Up-down arrows
        case 'press_key':
            return '&#9000;'; // Keyboard
        default:
            return '&#9881;'; // Gear
    }
}

/**
 * Update the actions list display
 */
function updateActionsList() {
    // Support both element IDs (actionsList for OCR job, actionList for DOM job)
    let container = document.getElementById('actionsList');
    if (!container) {
        container = document.getElementById('actionList');
    }

    if (!container) {
        console.warn('Actions list container not found');
        return;
    }

    const testAllBtn = document.getElementById('testAllActionsBtn');

    if (preExtractionActions.length === 0) {
        container.innerHTML = '<p class="no-actions">No pre-extraction actions defined. Add actions if you need to click buttons or navigate before capturing data.</p>';
        if (testAllBtn) testAllBtn.style.display = 'none';
        return;
    }

    if (testAllBtn) testAllBtn.style.display = 'inline-block';

    let html = '';
    preExtractionActions.forEach((action, index) => {
        html += `
            <div class="action-item" data-index="${index}">
                <span class="action-number">${index + 1}</span>
                <span class="action-icon">${getActionIcon(action.type)}</span>
                <span class="action-description">${getActionDescription(action)}</span>
                <span class="action-wait">${action.wait_after || 0}s wait</span>
                <div class="action-controls">
                    <button type="button" class="btn btn-small" onclick="moveActionUp(${index})" ${index === 0 ? 'disabled' : ''}>&#9650;</button>
                    <button type="button" class="btn btn-small" onclick="moveActionDown(${index})" ${index === preExtractionActions.length - 1 ? 'disabled' : ''}>&#9660;</button>
                    <button type="button" class="btn btn-small" onclick="editAction(${index})">Edit</button>
                    <button type="button" class="btn btn-small btn-danger" onclick="deleteAction(${index})">Delete</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateActionsList();
});
