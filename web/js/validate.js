window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(2);
    
    const currentSessionId = getCookie('sisal_session_id');
    if (!currentSessionId) {
        window.location.href = 'upload.html';
        return;
    }

    // Button event listeners
    const btnBack1 = document.getElementById('btn-back-1');
    if (btnBack1) {
        btnBack1.addEventListener('click', () => {
            window.location.href = 'upload.html';
        });
    }

    const btnNext3 = document.getElementById('btn-next-3');
    if (btnNext3) {
        btnNext3.addEventListener('click', () => {
            window.location.href = 'download.html';
        });
    }

    // Start validation process automatically
    runValidation(currentSessionId);
});

async function runValidation(sessionId) {
    const spinner = document.getElementById('validation-spinner');
    const resultsDiv = document.getElementById('validation-results');
    const btnNext = document.getElementById('btn-next-3');

    try {
        const response = await fetch(`${API_BASE_URL}/validate/${sessionId}`, { method: 'POST' });
        const data = await response.json();
        
        spinner.classList.add('d-none');
        resultsDiv.classList.remove('d-none');

        renderReport(data);

        if (data.status === 'success' && data.report.is_passed && data.report.total_warnings === 0) {
            btnNext.disabled = false;
            unlockStep(3);
        }
    } 
    catch (error) {
        alert('An error occurred during validation!');
        spinner.classList.add('d-none');
    }
}

function renderReport(data) {
    const alertBox = document.getElementById('status-alert');
    const listInfo = document.getElementById('list-informative');
    const tableWarn = document.getElementById('table-warnings').querySelector('tbody');
    
    listInfo.innerHTML = '';
    tableWarn.innerHTML = '';

    if (data.status === 'fatal_error') {
        alertBox.className = 'alert alert-danger';
        alertBox.innerHTML = `<strong>Fatal Error!</strong> ${data.message}`;
        tableWarn.innerHTML = `<tr><td>${data.details}</td></tr>`;
        return;
    }

    const report = data.report;
    const isSuccess = report.is_passed && report.total_warnings === 0;

    alertBox.className = isSuccess ? 'alert alert-success' : 'alert alert-warning';
    alertBox.innerHTML = isSuccess 
        ? '<strong>Validation successful!</strong> No errors found.' 
        : `<strong>Warning!</strong> ${report.total_warnings} issue(s) found.`;

    if (report.informative_messages.length === 0) {
        listInfo.innerHTML = '<li class="list-group-item text-muted">No information available.</li>';
    } 
    else {
        report.informative_messages.forEach(msg => {
            listInfo.innerHTML += `<li class="list-group-item list-group-item-info">${msg}</li>`;
        });
    }

    if (report.warnings.length === 0) {
        tableWarn.innerHTML = '<tr><td class="text-success text-center">No errors to display.</td></tr>';
    } 
    else {
        report.warnings.forEach(warn => {
            tableWarn.innerHTML += `<tr><td>${warn}</td></tr>`;
        });
    }
}