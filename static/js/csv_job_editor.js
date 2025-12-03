/**
 * CSV Job Editor Module
 * Handles CSV download action configuration
 */

let downloadActions = [];
let editingDownloadActionIndex = -1;

/**
 * Show the add download action modal
 */
function showDownloadActionModal() {
    editingDownloadActionIndex = -1;
    document.getElementById('downloadActionModalTitle').textContent = 'Add Download Action';
    document.getElementById('downloadActionType').value = 'click_coordinates';
    document.getElementById('downloadActionWaitAfter').value = '2';
    updateDownloadActionForm();
    document.getElementById('downloadActionModal').style.display = 'flex';
}

/**
 * Show edit download action modal
 */
function editDownloadAction(index) {
    editingDownloadActionIndex = index;
    const action = downloadActions[index];

    document.getElementById('downloadActionModalTitle').textContent = 'Edit Download Action';
    document.getElementById('downloadActionType').value = action.type;
    document.getElementById('downloadActionWaitAfter').value = action.wait_after || 2;

    updateDownloadActionForm();

    // Fill in the existing values
    setTimeout(() => {
        if (action.type === 'click_coordinates') {
            document.getElementById('dlClickX').value = action.x || 0;
            document.getElementById('dlClickY').value = action.y || 0;
        } else if (action.type === 'click_ocr') {
            document.getElementById('dlSearchText').value = action.search_text || '';
            document.getElementById('dlConfidenceThreshold').value = action.confidence_threshold || 0.7;
        } else if (action.type === 'wait') {
            document.getElementById('dlWaitDuration').value = action.duration || 1;
        }
    }, 50);

    document.getElementById('downloadActionModal').style.display = 'flex';
}

/**
 * Close the download action modal
 */
function closeDownloadActionModal() {
    document.getElementById('downloadActionModal').style.display = 'none';
    editingDownloadActionIndex = -1;
}

/**
 * Update the download action form fields based on selected type
 */
function updateDownloadActionForm() {
    const type = document.getElementById('downloadActionType').value;
    const container = document.getElementById('downloadActionFormFields');

    let html = '';

    if (type === 'click_coordinates') {
        html = `
            <div class="form-row">
                <div class="form-group">
                    <label for="dlClickX">X Coordinate</label>
                    <input type="number" id="dlClickX" value="0" min="0">
                </div>
                <div class="form-group">
                    <label for="dlClickY">Y Coordinate</label>
                    <input type="number" id="dlClickY" value="0" min="0">
                </div>
            </div>
            <p class="help-text">Capture the screen and note the coordinates of the element you need to click</p>
        `;
    } else if (type === 'click_ocr') {
        html = `
            <div class="form-group">
                <label for="dlSearchText">Text to Find</label>
                <input type="text" id="dlSearchText" placeholder="e.g., Export, Download, CSV">
                <small>The system will find this text on screen and click it</small>
            </div>
            <div class="form-group">
                <label for="dlConfidenceThreshold">Confidence Threshold</label>
                <input type="number" id="dlConfidenceThreshold" value="0.7" min="0" max="1" step="0.1">
                <small>Minimum OCR confidence (0.7 = 70%)</small>
            </div>
        `;
    } else if (type === 'wait') {
        html = `
            <div class="form-group">
                <label for="dlWaitDuration">Duration (seconds)</label>
                <input type="number" id="dlWaitDuration" value="2" min="0.5" step="0.5">
                <small>Time to wait (use for page loading, dropdown animations, etc.)</small>
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * Build download action object from form fields
 */
function buildDownloadActionFromForm() {
    const type = document.getElementById('downloadActionType').value;
    const waitAfter = parseFloat(document.getElementById('downloadActionWaitAfter').value) || 2;

    let action = { type, wait_after: waitAfter };

    if (type === 'click_coordinates') {
        action.x = parseInt(document.getElementById('dlClickX').value) || 0;
        action.y = parseInt(document.getElementById('dlClickY').value) || 0;
    } else if (type === 'click_ocr') {
        action.search_text = document.getElementById('dlSearchText').value;
        action.confidence_threshold = parseFloat(document.getElementById('dlConfidenceThreshold').value) || 0.7;
        if (!action.search_text) {
            alert('Please enter text to search for');
            return null;
        }
    } else if (type === 'wait') {
        action.duration = parseFloat(document.getElementById('dlWaitDuration').value) || 1;
        action.wait_after = 0; // Wait action doesn't need additional wait
    }

    return action;
}

/**
 * Save the current download action
 */
function saveDownloadAction() {
    const action = buildDownloadActionFromForm();
    if (!action) return;

    if (editingDownloadActionIndex >= 0) {
        downloadActions[editingDownloadActionIndex] = action;
    } else {
        downloadActions.push(action);
    }

    updateDownloadActionsList();
    closeDownloadActionModal();
}

/**
 * Test the current download action
 */
async function testDownloadAction() {
    const action = buildDownloadActionFromForm();
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
 * Test all download actions in sequence
 */
async function testDownloadActions() {
    if (downloadActions.length === 0) {
        alert('No download actions to test');
        return;
    }

    const btn = document.getElementById('testDownloadBtn');
    btn.disabled = true;
    btn.textContent = 'Testing...';

    try {
        const response = await fetch('/api/test-actions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions: downloadActions })
        });

        const result = await response.json();

        if (result.success) {
            alert(`All ${result.actions_executed} download actions executed successfully!`);
        } else {
            alert('Some actions failed. Check the console for details.');
        }
    } catch (e) {
        alert('Error testing actions: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Test Download Sequence';
    }
}

/**
 * Delete a download action
 */
function deleteDownloadAction(index) {
    if (!confirm('Delete this action?')) return;

    downloadActions.splice(index, 1);
    updateDownloadActionsList();
}

/**
 * Move download action up in the list
 */
function moveDownloadActionUp(index) {
    if (index <= 0) return;

    const temp = downloadActions[index];
    downloadActions[index] = downloadActions[index - 1];
    downloadActions[index - 1] = temp;

    updateDownloadActionsList();
}

/**
 * Move download action down in the list
 */
function moveDownloadActionDown(index) {
    if (index >= downloadActions.length - 1) return;

    const temp = downloadActions[index];
    downloadActions[index] = downloadActions[index + 1];
    downloadActions[index + 1] = temp;

    updateDownloadActionsList();
}

/**
 * Get human-readable description of download action
 */
function getDownloadActionDescription(action) {
    switch (action.type) {
        case 'click_coordinates':
            return `Click at (${action.x}, ${action.y})`;
        case 'click_ocr':
            return `Click "${action.search_text}"`;
        case 'wait':
            return `Wait ${action.duration}s`;
        default:
            return action.type;
    }
}

/**
 * Get action type icon
 */
function getDownloadActionIcon(type) {
    switch (type) {
        case 'click_coordinates':
        case 'click_ocr':
            return '&#128433;'; // Mouse pointer
        case 'wait':
            return '&#9202;'; // Timer
        default:
            return '&#9881;'; // Gear
    }
}

/**
 * Update the download actions list display
 */
function updateDownloadActionsList() {
    const container = document.getElementById('downloadActionsList');
    const testBtn = document.getElementById('testDownloadBtn');

    if (downloadActions.length === 0) {
        container.innerHTML = '<p class="no-actions">No download actions defined. Add the click sequence needed to download your CSV file.</p>';
        testBtn.style.display = 'none';
        return;
    }

    testBtn.style.display = 'inline-block';

    let html = '';
    downloadActions.forEach((action, index) => {
        html += `
            <div class="action-item" data-index="${index}">
                <span class="action-number">${index + 1}</span>
                <span class="action-icon">${getDownloadActionIcon(action.type)}</span>
                <span class="action-description">${getDownloadActionDescription(action)}</span>
                <span class="action-wait">${action.wait_after || 0}s wait</span>
                <div class="action-controls">
                    <button type="button" class="btn btn-small" onclick="moveDownloadActionUp(${index})" ${index === 0 ? 'disabled' : ''}>&#9650;</button>
                    <button type="button" class="btn btn-small" onclick="moveDownloadActionDown(${index})" ${index === downloadActions.length - 1 ? 'disabled' : ''}>&#9660;</button>
                    <button type="button" class="btn btn-small" onclick="editDownloadAction(${index})">Edit</button>
                    <button type="button" class="btn btn-small btn-danger" onclick="deleteDownloadAction(${index})">Delete</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateDownloadActionsList();
});
