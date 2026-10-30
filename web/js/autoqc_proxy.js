window.addEventListener('DOMContentLoaded', () => {
    const savedSession = getCookie('sisal_session_id');
    const savedStep = getCookie('sisal_saved_step');
    const resumeCard = document.getElementById('resume-card');

    if (savedSession && savedStep) {
        resumeCard.classList.remove('d-none');

        document.getElementById('btn-discard-resume').addEventListener('click', async () => {
            document.getElementById('btn-discard-resume').disabled = true;
            document.getElementById('btn-continue-resume').disabled = true;

            try {
                await fetch(`${API_BASE_URL}/session/${savedSession}/discard`, { method: 'POST' });
            } 
            catch(e) {
                console.error('Failed to discard session on server', e);
            }
            
            deleteCookie('sisal_session_id');
            deleteCookie('sisal_saved_step');
            sessionStorage.removeItem('sisal_uploaded_filename');
            
            window.location.replace('upload.html'); 
        });

        document.getElementById('btn-continue-resume').addEventListener('click', () => {
            if (savedStep === '4') {
                window.location.replace('download.html');
            } 
            else if (savedStep === '3') {
                window.location.replace('plots.html');
            } 
            else if (savedStep === '2') {
                window.location.replace('validate.html');
            } 
            else {
                window.location.replace('upload.html');
            }
        });
    } 
    else {
        window.location.replace('upload.html');
    }
});