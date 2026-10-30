window.addEventListener('DOMContentLoaded', () => {
    const savedSession = getCookie('sisal_session_id');
    
    if (savedSession) {
        const banner = document.getElementById('resume-banner');
        if (banner) {
            banner.classList.remove('d-none');
        }
    }
});