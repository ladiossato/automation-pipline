/**
 * Region Selector Module
 * Handles screen capture and OCR region selection
 */

let currentScreenshot = null;
let screenshotWidth = 0;
let screenshotHeight = 0;
let regions = [];
let isSelecting = false;
let selectionStart = null;
let selectionBox = null;

/**
 * Capture current screen
 */
async function captureScreen() {
    const status = document.getElementById('captureStatus');
    if (status) {
        status.textContent = 'Capturing...';
    }

    try {
        const response = await fetch('/api/capture-screen', {
            method: 'POST'
        });

        const data = await response.json();

        if (!data.success) {
            if (status) status.textContent = 'Error: ' + data.error;
            return;
        }

        currentScreenshot = data.screenshot;
        screenshotWidth = data.width;
        screenshotHeight = data.height;

        // Display screenshot
        const preview = document.getElementById('screenPreview');
        if (preview) {
            preview.innerHTML = `
                <div style="position: relative; display: inline-block;">
                    <img src="data:image/png;base64,${currentScreenshot}"
                         id="screenshotImg"
                         style="max-width: 100%; cursor: crosshair;">
                    <div id="selectionOverlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0;"></div>
                </div>
            `;

            // Enable region selection (only for OCR job editor)
            const regionsContainer = document.getElementById('regionsContainer');
            if (regionsContainer) {
                enableRegionSelection();
            }
        }

        if (status) {
            status.textContent = `Captured ${data.width}x${data.height}. Click on screenshot to pick coordinates.`;
        }

    } catch (e) {
        if (status) status.textContent = 'Error: ' + e.message;
        console.error('Error capturing screen:', e);
    }
}

/**
 * Enable mouse-based region selection
 */
function enableRegionSelection() {
    const img = document.getElementById('screenshotImg');
    const overlay = document.getElementById('selectionOverlay');

    overlay.addEventListener('mousedown', (e) => {
        isSelecting = true;
        const rect = img.getBoundingClientRect();
        selectionStart = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };

        // Create selection box
        selectionBox = document.createElement('div');
        selectionBox.className = 'selection-box';
        selectionBox.style.left = selectionStart.x + 'px';
        selectionBox.style.top = selectionStart.y + 'px';
        overlay.appendChild(selectionBox);
    });

    overlay.addEventListener('mousemove', (e) => {
        if (!isSelecting || !selectionBox) return;

        const rect = img.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;

        const left = Math.min(selectionStart.x, currentX);
        const top = Math.min(selectionStart.y, currentY);
        const width = Math.abs(currentX - selectionStart.x);
        const height = Math.abs(currentY - selectionStart.y);

        selectionBox.style.left = left + 'px';
        selectionBox.style.top = top + 'px';
        selectionBox.style.width = width + 'px';
        selectionBox.style.height = height + 'px';
    });

    overlay.addEventListener('mouseup', async (e) => {
        if (!isSelecting || !selectionBox) return;
        isSelecting = false;

        const rect = img.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;

        // Calculate region in actual screenshot coordinates
        const scaleX = screenshotWidth / img.width;
        const scaleY = screenshotHeight / img.height;

        const left = Math.min(selectionStart.x, endX);
        const top = Math.min(selectionStart.y, endY);
        const width = Math.abs(endX - selectionStart.x);
        const height = Math.abs(endY - selectionStart.y);

        // Minimum size check
        if (width < 10 || height < 10) {
            selectionBox.remove();
            selectionBox = null;
            return;
        }

        // Create region
        const regionName = prompt('Enter region name (e.g., "price", "title"):');

        if (!regionName) {
            selectionBox.remove();
            selectionBox = null;
            return;
        }

        const region = {
            name: regionName,
            x: Math.round(left * scaleX),
            y: Math.round(top * scaleY),
            width: Math.round(width * scaleX),
            height: Math.round(height * scaleY)
        };

        // Test extraction on this region
        await testRegionExtraction(region, selectionBox);

        // Add to regions list
        regions.push(region);
        updateRegionList();

        // Keep selection box visible with compact label
        // Use pointer-events: none so labels don't block new region selection
        selectionBox.innerHTML = `<span class="region-label">${regionName}</span>`;
        selectionBox.style.border = '2px solid #2563eb';
        selectionBox.style.background = 'rgba(37, 99, 235, 0.1)';
        selectionBox.style.pointerEvents = 'none';  // Allow clicks through to overlay
        selectionBox = null;
    });

    // Cancel selection on mouse leave
    overlay.addEventListener('mouseleave', () => {
        if (isSelecting && selectionBox) {
            selectionBox.remove();
            selectionBox = null;
            isSelecting = false;
        }
    });
}

/**
 * Test OCR extraction on a region
 */
async function testRegionExtraction(region, box) {
    try {
        const response = await fetch('/api/test-region', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                screenshot: currentScreenshot,
                region: region
            })
        });

        const result = await response.json();

        if (result.success) {
            const confidence = (result.confidence * 100).toFixed(1);
            const text = result.text.substring(0, 50);
            alert(`Region: ${region.name}\n\nExtracted: "${text}"\nConfidence: ${confidence}%`);
        } else {
            alert('Extraction failed: ' + result.error);
        }
    } catch (e) {
        alert('Error testing region: ' + e.message);
    }
}

/**
 * Update the displayed region list
 */
function updateRegionList() {
    const container = document.getElementById('regionsContainer');

    // Skip if container doesn't exist (e.g., on DOM job editor page)
    if (!container) {
        return;
    }

    if (regions.length === 0) {
        container.innerHTML = '<p class="no-regions">No regions defined. Capture screen and draw regions.</p>';
        return;
    }

    let html = '';
    regions.forEach((region, index) => {
        html += `
            <div class="region-item" data-index="${index}">
                <strong>${region.name}</strong>
                <span>(${region.x}, ${region.y}, ${region.width}x${region.height})</span>
                <button type="button" class="btn btn-small" onclick="testSingleRegion(${index})">Test</button>
                <button type="button" class="btn btn-small btn-danger" onclick="deleteRegion(${index})">Delete</button>
            </div>
        `;
    });

    container.innerHTML = html;

    // Update format template placeholder hints
    updateTemplatePlaceholders();
}

/**
 * Delete a region
 */
function deleteRegion(index) {
    if (!confirm(`Delete region "${regions[index].name}"?`)) return;

    regions.splice(index, 1);
    updateRegionList();

    // Refresh screen preview to remove selection boxes
    if (currentScreenshot) {
        captureScreen();
    }
}

/**
 * Test a single region
 */
async function testSingleRegion(index) {
    const region = regions[index];

    if (!currentScreenshot) {
        alert('Please capture screen first');
        return;
    }

    try {
        const response = await fetch('/api/test-region', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                screenshot: currentScreenshot,
                region: region
            })
        });

        const result = await response.json();

        if (result.success) {
            const confidence = (result.confidence * 100).toFixed(1);
            alert(`Region: ${region.name}\n\nExtracted: "${result.text}"\nConfidence: ${confidence}%`);
        } else {
            alert('Extraction failed: ' + result.error);
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

/**
 * Update template placeholder hints
 */
function updateTemplatePlaceholders() {
    const templateInput = document.getElementById('format_template');
    if (!templateInput) return;

    const placeholders = regions.map(r => `{${r.name}}`).join(', ');
    const small = templateInput.nextElementSibling;
    if (small && small.tagName === 'SMALL') {
        small.textContent = `Available placeholders: ${placeholders || 'none defined'}. Supports HTML: <b>bold</b>, <i>italic</i>`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateRegionList();
});
