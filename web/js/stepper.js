// ==========================================
// Stepper (Status bar) Component Logic
// ==========================================

async function loadStepper(currentStep) {
    const container = document.getElementById('stepper-container');
    if (!container) return;
    
    try {
        const response = await fetch('/stepper.html');
        const html = await response.text();
        container.innerHTML = html;
        
        updateStepperVisuals(currentStep);
        
        document.querySelectorAll('.stepper-item').forEach(item => {
            item.addEventListener('click', () => {
                if (item.classList.contains('disabled')) return;
                
                const step = parseInt(item.getAttribute('data-step'));
                if (step === 1) window.location.href = 'upload.html';
                if (step === 2) window.location.href = 'validate.html';
                if (step === 3) window.location.href = 'download.html';
            });
        });
        
    }
    catch (error) {
        console.error("Failed to load stepper component: ", error);
    }
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