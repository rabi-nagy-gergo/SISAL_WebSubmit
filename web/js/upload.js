window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(1);
    const config = await getAppConfig();

    const prevFilename = sessionStorage.getItem('sisal_uploaded_filename');
    if (prevFilename) {
        document.getElementById('previous-filename').textContent = prevFilename;
        document.getElementById('previous-file-info').classList.remove('d-none');
    }

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
                sessionStorage.setItem('sisal_uploaded_filename', fileInput.files[0].name);
                
                const expireDays = config.session_timeout_hours / 24; 
                setCookie('sisal_session_id', data.session_id, expireDays); 
                setCookie('sisal_saved_step', '2', expireDays);
                window.location.href = 'validate.html';
            }
        } 
        catch (error) {
            alert('An error occurred during the file upload!');
            console.error(error);
        }
    });
});