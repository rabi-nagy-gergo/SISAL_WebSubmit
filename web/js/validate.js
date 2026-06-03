window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(2);
    const config = await getAppConfig();

    const currentSessionId = getCookie('sisal_session_id');
    if (!currentSessionId) {
        window.location.href = 'upload.html';
        return;
    }

    document.getElementById('btn-back-1')?.addEventListener('click', () => {
        window.location.href = 'upload.html';
    });

    document.getElementById('btn-next-3')?.addEventListener('click', () => {
        window.location.href = 'download.html';
    });

    runValidation(currentSessionId, config);
});

async function runValidation(sessionId, config) {
    const spinner = document.getElementById('validation-spinner');
    const resultsDiv = document.getElementById('validation-results');
    const btnNext = document.getElementById('btn-next-3');

    try {
        const response = await fetch(`${API_BASE_URL}/validate/${sessionId}`, { method: 'POST' });
        const data = await response.json();

        spinner.classList.add('d-none');
        resultsDiv.classList.remove('d-none');

        renderReport(data);

        // Load the map image dynamically
        const mapContainer = document.getElementById('map-container');
        const mapImg = document.getElementById('site-map-img');
        
        // If the image loads successfully, reveal the container
        mapImg.onload = () => { 
            mapContainer.classList.remove('d-none'); 
        };

        mapImg.onerror = () => { 
            mapContainer.classList.add('d-none'); 
        };
        
        // Fetch the map from the new backend endpoint
        mapImg.src = `${API_BASE_URL}/map/${sessionId}?t=${new Date().getTime()}`;

        if (data.status === 'success' && data.report.is_passed && 
                data.report.total_warnings === 0 && 
                data.report.total_errors === 0 && 
                data.report.total_fatal === 0) {
            btnNext.disabled = false;
            unlockStep(3);
            
            const expireDays = config.session_timeout_hours / 24;
            setCookie('sisal_session_id', sessionId, expireDays); 
            setCookie('sisal_saved_step', '3', expireDays);
        }
    } catch (error) {
        alert('An error occurred during validation!');
        spinner.classList.add('d-none');
    }
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function normalizeMessage(message, defaultPriority) {
    if (typeof message === 'string') {
        return { priority: defaultPriority, description: message, script_location: '', workbook_location: '' };
    }
    return {
        priority: message.priority || defaultPriority,
        description: message.description || '',
        script_location: message.script_location || '',
        workbook_location: message.workbook_location || ''
    };
}

function renderMessageRows(tbody, messages, defaultPriority, emptyText, emptyClass = 'text-muted') {
    tbody.innerHTML = '';

    if (!messages || messages.length === 0) {
        tbody.innerHTML = `<tr class="${defaultPriority === 'Informative' ? '' : 'row-empty'}"><td colspan="4" class="${emptyClass} text-center">${escapeHtml(emptyText)}</td></tr>`;
        return;
    }

    messages.forEach(message => {
        const msg = normalizeMessage(message, defaultPriority);
        
        let rowClass = '';
        const priorityLower = msg.priority.toLowerCase();
        
        if (priorityLower.includes('fatal')) {
            rowClass = 'row-fatal';
        } else if (priorityLower.includes('error')) {
            rowClass = 'row-error';
        } else if (priorityLower.includes('warning')) {
            rowClass = 'row-warning';
        }
        
        tbody.innerHTML += `<tr class="${rowClass}">
            <td>${escapeHtml(msg.priority)}</td>
            <td>${escapeHtml(msg.description)}</td>
            <td>${escapeHtml(msg.script_location)}</td>
            <td>${escapeHtml(msg.workbook_location)}</td>
        </tr>`;
    });
}

function renderReport(data) {
    const alertBox = document.getElementById('status-alert');
    const report = data.report || { informative_messages: [], warnings: [], total_warnings: 0, total_errors: 0, total_fatal: 0, is_passed: false };

    renderMessageRows(document.getElementById('table-informative').querySelector('tbody'), report.informative_messages, 'Informative', 'No information available.');
    renderMessageRows(document.getElementById('table-warnings').querySelector('tbody'), report.warnings, 'Warning', 'No warnings or errors to display.');

    if (data.status === 'fatal_error' || report.total_fatal > 0) {
        alertBox.className = 'alert alert-danger';
        alertBox.innerHTML = `<strong>Fatal Error!</strong> ${escapeHtml(data.message || 'Validation stopped because a fatal error occurred.')}`;
        return;
    }

    const blockingIssues = (report.total_warnings || 0) + (report.total_errors || 0) + (report.total_fatal || 0);
    const isSuccess = report.is_passed && blockingIssues === 0;

    alertBox.className = isSuccess ? 'alert alert-success' : 'alert alert-warning';
    alertBox.innerHTML = isSuccess
        ? '<strong>Validation successful!</strong> No errors found.'
        : `<strong>Warning!</strong> ${blockingIssues} issue(s) found.`;
}
