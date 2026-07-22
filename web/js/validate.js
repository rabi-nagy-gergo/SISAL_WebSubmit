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
        window.location.href = 'plots.html';
    });

    runValidation(currentSessionId, config);
});

async function runValidation(sessionId, config) {
    const dom = getValidationDomElements();
    const uiState = { currentSection: null, currentList: null };

    try {
        const response = await fetch(`${API_BASE_URL}/validate/${sessionId}`, { method: 'POST' });
        await processValidationStream(response.body, sessionId, config, dom, uiState);
    } 
    catch (error) {
        handleValidationError(error, dom);
    }
}

async function processValidationStream(stream, sessionId, config, dom, uiState) {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split('\n');
        buffer = lines.pop();
        
        for (let line of lines) {
            if (!line.trim()) continue;
            
            const data = JSON.parse(line);
            
            if (data.type === 'progress') {
                handleProgressUpdate(data, uiState, dom);
            } 
            else if (data.type === 'complete') {
                handleValidationComplete(data, sessionId, config, dom);
            }
        }
    }
}

function handleProgressUpdate(data, uiState, dom) {
    dom.progressBar.style.width = `${data.percentage}%`;
    dom.progressBar.textContent = `${data.percentage}%`;
    dom.progressBar.setAttribute('aria-valuenow', data.percentage);
    dom.progressText.textContent = `${data.section} ...`;

    if (dom.logContainer.classList.contains('d-none')) {
        dom.logContainer.classList.remove('d-none');
    }

    if (data.section && data.section !== uiState.currentSection) {
        closePreviousSection(dom.logContainer, uiState.currentSection);
        
        uiState.currentSection = data.section;
        uiState.currentList = createNewSection(dom.logContainer, uiState.currentSection);
    }
    
    if (data.message && uiState.currentList) {
        appendLogMessage(dom.logContainer, uiState.currentList, data.message);
    }
}

function handleValidationComplete(data, sessionId, config, dom) {
    dom.spinner.classList.add('d-none');
    dom.resultsDiv.classList.remove('d-none');

    renderReport(data);
    loadSiteMapImage(sessionId);

    const report = data.report;
    
    // Allow progression if the file passes validation (allows warnings, but no errors or fatals)
    if (data.status === 'success' && report.is_passed) {
        dom.btnNext.disabled = false;
        unlockStep(3);
        
        const expireDays = config.session_timeout_hours / 24;
        setCookie('sisal_session_id', sessionId, expireDays); 
        setCookie('sisal_saved_step', '3', expireDays);
    }
}

function handleValidationError(error, dom) {
    alert('An error occurred during validation! Could not read stream.');
    dom.spinner.classList.add('d-none');
    console.error(error);
}

function closePreviousSection(logContainer, sectionName) {
    if (!sectionName) return;
    
    const lastHeader = logContainer.querySelector('.current-section-header');
    if (lastHeader) {
        lastHeader.classList.remove('current-section-header', 'text-primary');
        lastHeader.classList.add('text-success');
        lastHeader.innerHTML = `<span class="me-2 fw-bold">&#10003;</span>${escapeHtml(sectionName)}`;
    }
}

function createNewSection(logContainer, sectionName) {
    const header = document.createElement('div');
    header.className = 'current-section-header text-primary fw-bold fs-5 mt-3 mb-2';
    header.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>${escapeHtml(sectionName)}`;
    logContainer.appendChild(header);
    
    const list = document.createElement('ul');
    list.className = 'list-unstyled ms-4 mb-3 text-secondary fs-6';
    logContainer.appendChild(list);
    
    return list;
}

function appendLogMessage(logContainer, list, message) {
    const li = document.createElement('li');
    li.innerHTML = `&rsaquo; ${escapeHtml(message)}`;
    list.appendChild(li);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function renderReport(data) {
    const alertBox = document.getElementById('status-alert');
    const report = data.report || { 
        informative: [], 
        warnings: [], 
        errors: [], 
        fatals: [], 
        total_warnings: 0, 
        total_errors: 0, 
        total_fatal: 0, 
        is_passed: false 
    };

    // Render the 4 separate tables
    renderMessageRows(document.getElementById('table-informative').querySelector('tbody'), report.informative, 'Informative', 'No informative messages.');
    renderMessageRows(document.getElementById('table-warnings').querySelector('tbody'), report.warnings, 'Warning', 'No warnings to display.');
    renderMessageRows(document.getElementById('table-errors').querySelector('tbody'), report.errors, 'Error', 'No errors to display.');
    renderMessageRows(document.getElementById('table-fatals').querySelector('tbody'), report.fatals, 'Fatal', 'No fatal errors to display.');

    const totalErrors = report.total_errors || 0;
    const totalFatals = report.total_fatal || 0;
    const totalWarnings = report.total_warnings || 0;

    let iconSvg = '';
    let title = '';
    let desc = '';
    let alertClass = '';

    if (totalErrors > 0 || totalFatals > 0) {
        alertClass = 'alert-danger';
        title = 'Validation failed!';
        desc = `Found ${totalErrors} error(s) and ${totalFatals} fatal issue(s). Please review the tables below and correct your workbook.`;
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" class="bi bi-x-octagon-fill" viewBox="0 0 16 16"><path d="M11.46.146A.5.5 0 0 0 11.107 0H4.893a.5.5 0 0 0-.353.146L.146 4.54A.5.5 0 0 0 0 4.893v6.214a.5.5 0 0 0 .146.353l4.394 4.394a.5.5 0 0 0 .353.146h6.214a.5.5 0 0 0 .353-.146l4.394-4.394a.5.5 0 0 0 .146-.353V4.893a.5.5 0 0 0-.146-.353zM8 4c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995A.905.905 0 0 1 8 4m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/></svg>`;
    } 
    else if (totalWarnings > 0) {
        alertClass = 'alert-warning';
        title = 'Validation successful with warnings!';
        desc = `Found ${totalWarnings} warning(s). You may proceed, but please review the warnings below.`;
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" class="bi bi-exclamation-triangle-fill" viewBox="0 0 16 16"><path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/></svg>`;
    } 
    else {
        alertClass = 'alert-success';
        title = 'Validation successful!';
        desc = 'No issues found. You may proceed to the next step.';
        iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" class="bi bi-check-circle-fill" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg>`;
    }

    alertBox.className = `alert ${alertClass} d-flex align-items-center shadow-sm`;
    alertBox.innerHTML = `
        <div class="me-3 flex-shrink-0">
            ${iconSvg}
        </div>
        <div>
            <h5 class="fw-bold mb-1">${title}</h5>
            <p class="mb-0">${desc}</p>
        </div>
    `;
}

function renderMessageRows(tbody, messages, defaultPriority, emptyText) {
    tbody.innerHTML = '';

    if (!messages || messages.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-muted text-center">${escapeHtml(emptyText)}</td></tr>`;
        return;
    }

    messages.forEach(message => {
        const msg = normalizeMessage(message, defaultPriority);
        
        tbody.innerHTML += `<tr>
            <td>${escapeHtml(msg.priority)}</td>
            <td>${escapeHtml(msg.description)}</td>
            <td>${escapeHtml(msg.script_location)}</td>
            <td>${escapeHtml(msg.workbook_location)}</td>
        </tr>`;
    });
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

function loadSiteMapImage(sessionId) {
    const mapContainer = document.getElementById('map-container');
    const mapImg = document.getElementById('site-map-img');
    
    mapImg.onload = () => { mapContainer.classList.remove('d-none'); };
    mapImg.onerror = () => { mapContainer.classList.add('d-none'); };
    mapImg.src = `${API_BASE_URL}/map/${sessionId}?t=${new Date().getTime()}`;
}

function getValidationDomElements() {
    return {
        spinner: document.getElementById('validation-spinner'),
        resultsDiv: document.getElementById('validation-results'),
        btnNext: document.getElementById('btn-next-3'),
        progressBar: document.getElementById('progress-bar'),
        progressText: document.getElementById('progress-text'),
        logContainer: document.getElementById('status-log-container')
    };
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}