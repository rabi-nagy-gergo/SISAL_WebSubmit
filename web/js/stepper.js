// ==========================================
// Stepper (Status bar) Component Logic
// ==========================================

async function loadStepper() {
    const container = document.getElementById('stepper-container');
    if (!container) return;
    
    try {
        const response = await fetch('/stepper.html');
        const html = await response.text();
        container.innerHTML = html;
        
        document.querySelectorAll('.stepper-item').forEach(item => {
            item.addEventListener('click', () => {
                if (item.classList.contains('disabled')) return;
                
                const step = parseInt(item.getAttribute('data-step'));
                goToStep(step);
            });
        });

        initNavigationButtons();
    }
    catch (error) {
        console.error("Failed to load stepper component: ", error);
    }
}

function initNavigationButtons() {
    // Step back from 2 to 1 (Retry)
    const btnBack = document.getElementById('btn-back-1');
    if (btnBack) {
        btnBack.addEventListener('click', () => {
            goToStep(1);
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = ''; // Clear input
        });
    }

    // Proceed from 2 to 3
    const btnNext = document.getElementById('btn-next-3');
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            goToStep(3);
            // Set download button reference
            const btnDownload = document.getElementById('btn-download');
            if (btnDownload) {
                btnDownload.href = `${API_BASE_URL}/download/${currentSessionId}`;
            }
        });
    }
}

function goToStep(step) {
    document.querySelectorAll('.step-container').forEach(el => el.classList.remove('step-active'));
    
    const activeStep = document.getElementById(`step-${step}`);
    if (activeStep) activeStep.classList.add('step-active');
    
    updateStepperVisuals(step);
}

function updateStepperVisuals(currentStep) {
    document.querySelectorAll('.stepper-item').forEach((el, index) => {
        const stepNum = index + 1;
        
        if (stepNum === currentStep) {
            el.classList.add('active');
            el.classList.remove('completed', 'disabled');
        } 
        else if (stepNum < currentStep) {
            el.classList.add('completed');
            el.classList.remove('active', 'disabled');
        } 
        else {
            el.classList.remove('active', 'completed');
        }
    });
}

function unlockStep(step) {
    const stepItem = document.getElementById(`step-btn-${step}`);
    if (stepItem) stepItem.classList.remove('disabled');
}

function lockStep(step) {
    const stepItem = document.getElementById(`step-btn-${step}`);
    if (stepItem) stepItem.classList.add('disabled');
}