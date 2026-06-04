// ==========================================
// Plot label mapping (keyed by PNG filename suffix)
// ==========================================
const PLOT_LABELS = {
    '01_agemodel':    'Age Model',
    '02_age_diff':    'Interpolated Age Differences',
    '03_d18O':        'δ¹⁸O vs Time',
    '04_d13C':        'δ¹³C vs Time',
    '05_Sr_Ca':       'Sr/Ca vs Time',
    '06_Mg_Ca':       'Mg/Ca vs Time',
    '07_Ba_Ca':       'Ba/Ca vs Time',
    '08_U_Ca':        'U/Ca vs Time',
    '09_P_Ca':        'P/Ca vs Time',
    '10_Sr_isotopes': 'Sr Isotopes vs Time'
};

// ==========================================
// Helpers
// ==========================================
function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function parsePlotFilename(filename) {
    const match = filename.match(/^plot_(.+)_(\d{2}_\w+(?:_\w+)*)\.png$/);
    if (!match) return null;
    return { entityName: match[1], plotKey: match[2] };
}

// ==========================================
// Rendering
// ==========================================
function renderPlots(plots, sessionId) {
    const container = document.getElementById('plotsAccordion');
    container.innerHTML = '';

    // Group plot filenames by entity name, preserving plot order
    const entities = {};
    plots.forEach(filename => {
        const parsed = parsePlotFilename(filename);
        if (!parsed) return;
        if (!entities[parsed.entityName]) entities[parsed.entityName] = [];
        entities[parsed.entityName].push({ filename, plotKey: parsed.plotKey });
    });

    if (Object.keys(entities).length === 0) {
        container.innerHTML = '<p class="text-center text-muted py-3">No plot images were found in the output.</p>';
        return;
    }

    Object.entries(entities).forEach(([entityName, entityPlots], idx) => {
        entityPlots.sort((a, b) => a.plotKey.localeCompare(b.plotKey));

        const collapseId = `collapse-entity-${idx}`;
        const headingId  = `heading-entity-${idx}`;

        const plotCards = entityPlots.map(ep => {
            const label = PLOT_LABELS[ep.plotKey] || ep.plotKey;
            const src   = `${API_BASE_URL}/plots/${sessionId}/${encodeURIComponent(ep.filename)}`;
            return `
                <div class="col-12 col-lg-6">
                    <div class="plot-card">
                        <a href="${escapeHtml(src)}" target="_blank" title="Open full size">
                            <img src="${escapeHtml(src)}"
                                 class="img-fluid rounded plot-img"
                                 alt="${escapeHtml(label)}"
                                 loading="lazy">
                        </a>
                        <div class="plot-label">${escapeHtml(label)}</div>
                    </div>
                </div>`;
        }).join('');

        const section = document.createElement('div');
        section.className = 'accordion-item border-0 mb-4 rounded panel-plots';
        section.innerHTML = `
            <h2 class="accordion-header" id="${headingId}">
                <button class="accordion-button plots-btn rounded" type="button"
                        data-bs-toggle="collapse" data-bs-target="#${collapseId}"
                        aria-expanded="true" aria-controls="${collapseId}">
                    Entity: ${escapeHtml(entityName)}
                </button>
            </h2>
            <div id="${collapseId}" class="accordion-collapse collapse show"
                 aria-labelledby="${headingId}">
                <div class="accordion-body p-3">
                    <div class="row g-3">${plotCards}</div>
                </div>
            </div>`;
        container.appendChild(section);
    });
}

function showStatusAlert(type, html) {
    const alertBox = document.getElementById('plots-status-alert');
    alertBox.className = `alert alert-${type}`;
    alertBox.innerHTML = html;
}

// ==========================================
// Main flow
// ==========================================
async function runPlots(sessionId, config) {
    const spinner    = document.getElementById('plots-spinner');
    const resultsDiv = document.getElementById('plots-results');
    const btnNext    = document.getElementById('btn-next-4');

    try {
        // Check for already-generated plots first
        const existingResp = await fetch(`${API_BASE_URL}/plots/${sessionId}`);
        if (existingResp.ok) {
            const existingData = await existingResp.json();
            if (existingData.plots && existingData.plots.length > 0) {
                spinner.classList.add('d-none');
                resultsDiv.classList.remove('d-none');
                showStatusAlert('success', '<strong>Plots ready!</strong> Previously generated plots loaded.');
                renderPlots(existingData.plots, sessionId);
                btnNext.disabled = false;
                unlockStep(4);
                return;
            }
        }

        // Run the R plotting script
        const response = await fetch(`${API_BASE_URL}/run_plots/${sessionId}`, { method: 'POST' });
        const data = await response.json();

        spinner.classList.add('d-none');
        resultsDiv.classList.remove('d-none');

        if (data.status === 'success') {
            showStatusAlert('success',
                `<strong>Plots generated successfully!</strong> ${data.plots.length} image(s) created.`);
            renderPlots(data.plots, sessionId);
            btnNext.disabled = false;
            unlockStep(4);

            const expireDays = config.session_timeout_hours / 24;
            setCookie('sisal_session_id', sessionId, expireDays);
            setCookie('sisal_saved_step', '4', expireDays);
        } 
        else {
            const errorText = data.message || data.detail || 'An error occurred.';
            
            const detail = data.stderr
                ? `<br><pre class="mt-2 mb-0 small text-start" style="white-space: pre-wrap;">${escapeHtml(data.stderr)}</pre>`
                : '';
                
            showStatusAlert('danger',
                `<strong>R script error.</strong> ${escapeHtml(errorText)}${detail}`);
        }
    } 
    catch (error) {
        spinner.classList.add('d-none');
        resultsDiv.classList.remove('d-none');
        showStatusAlert('danger', '<strong>Connection error.</strong> Could not reach the server.');
    }
}

// ==========================================
// Initialization
// ==========================================
window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(3);
    const config = await getAppConfig();

    const currentSessionId = getCookie('sisal_session_id');
    if (!currentSessionId) {
        window.location.href = 'upload.html';
        return;
    }

    document.getElementById('btn-back-2')?.addEventListener('click', () => {
        window.location.href = 'validate.html';
    });

    document.getElementById('btn-next-4')?.addEventListener('click', () => {
        window.location.href = 'download.html';
    });

    runPlots(currentSessionId, config);
});