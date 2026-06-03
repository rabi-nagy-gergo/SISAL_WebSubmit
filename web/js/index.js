window.addEventListener('DOMContentLoaded', () => {
    const savedSession = getCookie('sisal_session_id');
    
    if (savedSession) {
        const modal = new bootstrap.Modal(document.getElementById('resumeModal'));
        modal.show();

        document.getElementById('btn-discard-resume').addEventListener('click', async () => {
            await fetch(`${API_BASE_URL}/session/${savedSession}/discard`, { method: 'POST' });
            deleteCookie('sisal_session_id');
            modal.hide();
        });

        document.getElementById('btn-continue-resume').addEventListener('click', () => {
            modal.hide();
            window.location.href = 'download.html';
        });
    }
});