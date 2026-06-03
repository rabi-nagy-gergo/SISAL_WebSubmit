window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(1);

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
                setCookie('sisal_session_id', data.session_id, 1/12); // 2 hours
                window.location.href = 'validate.html';
            }
        } 
        catch (error) {
            alert('An error occurred during the file upload!');
            console.error(error);
        }
    });
});