window.addEventListener('DOMContentLoaded', () => {
    const savedSession = getCookie('sisal_session_id');
    
    if (savedSession) {
        const modal = new bootstrap.Modal(document.getElementById('resumeModal'));
        modal.show();

        document.getElementById('btn-discard-resume').addEventListener('click', async () => {
            await fetch(`${API_BASE_URL}/session/${savedSession}/discard`, { method: 'POST' });
            
            deleteCookie('sisal_session_id');
            deleteCookie('sisal_saved_step');
            modal.hide();
        });

        document.getElementById('btn-continue-resume').addEventListener('click', () => {
            modal.hide();

            const savedStep = getCookie('sisal_saved_step');
            if (savedStep === '3') {
                window.location.href = 'download.html';
            } 
            else if (savedStep === '2') {
                window.location.href = 'validate.html';
            } 
            else {
                window.location.href = 'upload.html';
            }
        });
    }
});