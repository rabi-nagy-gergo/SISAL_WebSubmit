// Configuration (FastAPI default port)
const API_BASE_URL = '/api';
let currentSessionId = null;

// ==========================================
// Helper functions (Cookie management)
// ==========================================
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

// ==========================================
// Network functions (API Calls)
// ==========================================

// File Upload
document.getElementById('btn-upload').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const errorMsg = document.getElementById('upload-error');
    
    if (fileInput.files.length === 0) {
        errorMsg.classList.remove('d-none');
        return;
    }
    errorMsg.classList.add('d-none');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            currentSessionId = data.session_id;
            // Temporary cookie (2 hours) as a safety net (in case the tab is closed)
            setCookie('sisal_session_id', currentSessionId, 1/12); 
            
            goToStep(2);
            runValidation(); // Automatically start validation
        }
    } catch (error) {
        alert('An error occurred during the file upload!');
        console.error(error);
    }
});

// Run validation and display results
async function runValidation() {
    const spinner = document.getElementById('validation-spinner');
    const resultsDiv = document.getElementById('validation-results');
    const btnNext = document.getElementById('btn-next-3');
    
    spinner.classList.remove('d-none');
    resultsDiv.classList.add('d-none');

    try {
        const response = await fetch(`${API_BASE_URL}/validate/${currentSessionId}`, { method: 'POST' });
        const data = await response.json();
        
        spinner.classList.add('d-none');
        resultsDiv.classList.remove('d-none');

        // Populate UI elements
        renderReport(data);

        // Enable progression if everything is successful
        if (data.status === 'success' && data.report.is_passed && data.report.total_warnings === 0) {
            btnNext.disabled = false;
            if (typeof unlockStep === 'function') unlockStep(3);
        } 
        else {
            btnNext.disabled = true; // Block checkout if there are errors
            if (typeof lockStep === 'function') lockStep(3);
        }

    } 
    catch (error) {
        alert('An error occurred during validation!');
        spinner.classList.add('d-none');
    }
}

// Render report data to HTML
function renderReport(data) {
    const alertBox = document.getElementById('status-alert');
    const listInfo = document.getElementById('list-informative');
    const tableWarn = document.getElementById('table-warnings').querySelector('tbody');
    
    // Clear lists
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

    // Informative messages
    if (report.informative_messages.length === 0) {
        listInfo.innerHTML = '<li class="list-group-item text-muted">No information available.</li>';
    } 
    else {
        report.informative_messages.forEach(msg => {
            listInfo.innerHTML += `<li class="list-group-item list-group-item-info">${msg}</li>`;
        });
    }

    // Errors / Warnings
    if (report.warnings.length === 0) {
        tableWarn.innerHTML = '<tr><td class="text-success text-center">No errors to display.</td></tr>';
    } 
    else {
        report.warnings.forEach(warn => {
            tableWarn.innerHTML += `<tr><td>${warn}</td></tr>`;
        });
    }
}

// Discard work
document.getElementById('btn-discard').addEventListener('click', async () => {
    if(confirm('Are you sure you want to discard your work? All data will be deleted.')) {
        await fetch(`${API_BASE_URL}/session/${currentSessionId}/discard`, { method: 'POST' });
        deleteCookie('sisal_session_id');
        location.reload(); // Reload page to reset state
    }
});

// Save work for 30 days
document.getElementById('btn-save').addEventListener('click', async () => {
    await fetch(`${API_BASE_URL}/session/${currentSessionId}/save`, { method: 'POST' });
    setCookie('sisal_session_id', currentSessionId, 30);
    alert('Your work has been successfully saved for 30 days!');
    location.reload();
});

// ==========================================
// Initialization (On page load)
// ==========================================
window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper();
    
    const savedSession = getCookie('sisal_session_id');
    if (savedSession) {
        // If a cookie exists, ask the user what to do
        const modal = new bootstrap.Modal(document.getElementById('resumeModal'));
        modal.show();

        document.getElementById('btn-discard-resume').addEventListener('click', async () => {
            // Discard from backend and delete cookie
            await fetch(`${API_BASE_URL}/session/${savedSession}/discard`, { method: 'POST' });
            deleteCookie('sisal_session_id');
            modal.hide();
        });

        document.getElementById('btn-continue-resume').addEventListener('click', () => {
            currentSessionId = savedSession;
            modal.hide();
            // Jump to the download endpoint to continue
            goToStep(3);
            document.getElementById('btn-download').href = `${API_BASE_URL}/download/${currentSessionId}`;
        });
    }
});