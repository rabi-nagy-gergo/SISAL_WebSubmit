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
    if (data.status === 'success' && report.is_passed && 
        report.total_warnings === 0 && report.total_errors === 0 && report.total_fatal === 0) {
        
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
        } 
        else if (priorityLower.includes('error')) {
            rowClass = 'row-error';
        } 
        else if (priorityLower.includes('warning')) {
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