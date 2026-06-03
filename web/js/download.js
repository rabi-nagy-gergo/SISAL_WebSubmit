window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(3);
    const config = await getAppConfig();

    const currentSessionId = getCookie('sisal_session_id');
    if (!currentSessionId) {
        window.location.href = 'index.html';
        return;
    }

    const hours = config.saved_session_timeout_hours;
    const daysForUI = Math.max(1, Math.round(hours / 24));

    // Update UI texts (in days)
    document.getElementById('save-desc').textContent = `You can discard your files now, or save them on the server for ${daysForUI} days to download later.`;
    document.getElementById('btn-save').textContent = `Save (${daysForUI} days)`;

    // Button event listeners
    const btnBack2 = document.getElementById('btn-back-2');
    if (btnBack2) {
        btnBack2.addEventListener('click', () => {
            window.location.href = 'validate.html';
        });
    }

    document.getElementById('btn-download').href = `${API_BASE_URL}/download/${currentSessionId}`;

    document.getElementById('btn-discard').addEventListener('click', async () => {
        if(confirm('Are you sure you want to discard your work? All data will be deleted.')) {
            await fetch(`${API_BASE_URL}/session/${currentSessionId}/discard`, { method: 'POST' });
            
            deleteCookie('sisal_session_id');
            deleteCookie('sisal_saved_step');
            window.location.href = 'index.html';
        }
    });

    document.getElementById('btn-save').addEventListener('click', async () => {
        await fetch(`${API_BASE_URL}/session/${currentSessionId}/save`, { method: 'POST' });
        const expireDays = hours / 24;
        setCookie('sisal_session_id', currentSessionId, expireDays);
        setCookie('sisal_saved_step', '3', expireDays);
        
        alert(`Your work has been successfully saved for ${daysForUI} days!`);
        window.location.href = 'index.html';
    });
});