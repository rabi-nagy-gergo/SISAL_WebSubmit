let requiresCaptcha = true;

window.onCaptchaSuccess = function(token) {
    document.getElementById('upload-section').classList.remove('d-none');
    document.getElementById('upload-server-error').classList.add('d-none');
};

window.addEventListener('DOMContentLoaded', async () => {
    await loadStepper(1);
    const config = await getAppConfig();

    const prevFilename = sessionStorage.getItem('sisal_uploaded_filename');
    if (prevFilename) {
        document.getElementById('previous-filename').textContent = prevFilename;
        document.getElementById('previous-file-info').classList.remove('d-none');
    }

    try {
        const captchaResp = await fetch(`${API_BASE_URL}/upload/requires-captcha`, {
            credentials: 'same-origin'
        });

        if (captchaResp.ok) {
            const captchaData = await captchaResp.json();
            requiresCaptcha = captchaData.requires_captcha;
        }
    } catch (e) {
        console.error("Could not verify session status", e);
    }

    if (requiresCaptcha) {
        document.getElementById('captcha-container').classList.remove('d-none');
    } else {
        document.getElementById('upload-section').classList.remove('d-none');
    }

    const fileInput = document.getElementById('fileInput');
    const btnUpload = document.getElementById('btn-upload');
    const errorMsg = document.getElementById('upload-error');
    const serverErrorMsg = document.getElementById('upload-server-error');

    // Re-enable the button and hide errors when a new file is selected
    fileInput.addEventListener('change', () => {
        btnUpload.disabled = false;
        errorMsg.classList.add('d-none');
        serverErrorMsg.classList.add('d-none');
    });

    btnUpload.addEventListener('click', async () => {
        serverErrorMsg.classList.add('d-none');
        errorMsg.classList.add('d-none');

        if (fileInput.files.length === 0) {
            errorMsg.textContent = 'Please select a file!';
            errorMsg.classList.remove('d-none');
            document.getElementById('previous-file-info').classList.add('d-none');
            return;
        }

        const selectedFile = fileInput.files[0];

        if (!selectedFile.name.toLowerCase().endsWith('.xlsx')) {
            errorMsg.textContent = 'Invalid file type! Please select a valid Excel (.xlsx) file.';
            errorMsg.classList.remove('d-none');
            document.getElementById('previous-file-info').classList.add('d-none');
            return;
        }

        const uploadMaxSizeMB = config.upload_max_size_mb || 10;
        const maxFileSizeBytes = uploadMaxSizeMB * 1024 * 1024;

        if (selectedFile.size > maxFileSizeBytes) {
            errorMsg.textContent = `File is too large! Maximum allowed size is ${uploadMaxSizeMB} MB.`;
            errorMsg.classList.remove('d-none');
            document.getElementById('previous-file-info').classList.add('d-none');
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);

        if (requiresCaptcha) {
            const turnstileInput = document.querySelector('[name="cf-turnstile-response"]');
            const captchaToken = turnstileInput ? turnstileInput.value : ''; 
            
            if (!captchaToken) {
                errorMsg.textContent = 'Please complete the CAPTCHA.';
                errorMsg.classList.remove('d-none');
                return;
            }
            formData.append('captcha_token', captchaToken);
        }

        // Disable button during the upload process
        btnUpload.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            
            // Handle unexpected non-JSON responses gracefully (e.g., Proxy HTML errors)
            let data;
            const contentType = response.headers.get("content-type");
            
            if (contentType && contentType.includes("application/json")) {
                data = await response.json();
            } else {
                let errorDetail = `Unexpected response from server (HTTP ${response.status}).`;
                
                switch (response.status) {
                    case 413: errorDetail = 'The file is too large for the web server proxy (HTTP 413).'; break;
                    case 429: errorDetail = 'Too many requests. You have been rate-limited (HTTP 429).'; break;
                    case 500: errorDetail = 'Internal Server Error (HTTP 500).'; break;
                    case 502: errorDetail = 'Bad Gateway. The backend container might be restarting (HTTP 502).'; break;
                    case 504: errorDetail = 'Gateway Timeout. The proxy dropped the connection (HTTP 504).'; break;
                }
                
                data = { status: 'error', detail: errorDetail };
                Object.defineProperty(response, 'ok', { value: false });
            }

            if (response.ok && data.status === 'success') {
                sessionStorage.setItem('sisal_uploaded_filename', fileInput.files[0].name);

                const expireDays = config.session_timeout_hours / 24; 
                setCookie('sisal_session_id', data.session_id, expireDays);
                setCookie('sisal_saved_step', '2', expireDays);
                window.location.href = 'validate.html';
            }
            else {
                const isCaptchaError = response.status === 403;

                if (isCaptchaError && requiresCaptcha && typeof turnstile !== 'undefined') {
                    turnstile.reset();
                }

                if (response.status === 507) {
                    showUploadServerError(serverErrorMsg, 'Server storage is currently full.', data.detail || 'Please try again later.');
                }
                else if (isCaptchaError) {
                    showUploadServerError(serverErrorMsg, 'Validation failed.', data.detail || 'CAPTCHA verification failed.');
                }
                else {
                    showUploadServerError(serverErrorMsg, 'Upload failed.', data.detail || 'An unexpected error occurred.');
                }
            }
        } 
        catch (error) {
            showUploadServerError(serverErrorMsg, 'Connection error.', 'Could not reach the server. Please check your connection and try again.');
            console.error(error);
        }
    });
});

function showUploadServerError(element, title, message) {
    element.innerHTML = `<strong>${escapeHtml(title)}</strong> ${escapeHtml(message)}`;
    element.classList.remove('d-none');
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}