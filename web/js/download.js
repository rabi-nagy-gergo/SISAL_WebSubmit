window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(3);

    const currentSessionId = getCookie('sisal_session_id');
    if (!currentSessionId) {
        window.location.href = 'index.html';
        return;
    }

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
            window.location.href = 'index.html';
        }
    });

    document.getElementById('btn-save').addEventListener('click', async () => {
        await fetch(`${API_BASE_URL}/session/${currentSessionId}/save`, { method: 'POST' });
        setCookie('sisal_session_id', currentSessionId, 30);
        alert('Your work has been successfully saved for 30 days!');
        window.location.href = 'index.html';
    });
});