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

    // Check if CAPTCHA is required based on session validity
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

    document.getElementById('btn-upload').addEventListener('click', async () => {
        const fileInput = document.getElementById('fileInput');
        const errorMsg = document.getElementById('upload-error');
        const serverErrorMsg = document.getElementById('upload-server-error');

        serverErrorMsg.classList.add('d-none');
        errorMsg.classList.add('d-none');

        if (fileInput.files.length === 0) {
            errorMsg.textContent = 'Please select a file!';
            errorMsg.classList.remove('d-none');
            document.getElementById('previous-file-info').classList.add('d-none');
            return;
        }

        const selectedFile = fileInput.files[0];

        // Checks file type
        if (!selectedFile.name.toLowerCase().endsWith('.xlsx')) {
            errorMsg.textContent = 'Invalid file type! Please select a valid Excel (.xlsx) file.';
            errorMsg.classList.remove('d-none');
            document.getElementById('previous-file-info').classList.add('d-none');
            return;
        }

        // Checks file size
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

        try {
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            const data = await response.json();

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
                    document.getElementById('upload-section').classList.add('d-none');
                }

                if (response.status === 507) {
                    showUploadServerError(serverErrorMsg,
                        'Server storage is currently full.', data.detail ||
                        'Please try again later or contact the site administrator.');
                }
                else if (isCaptchaError) {
                    showUploadServerError(serverErrorMsg,
                        'Validation failed.', data.detail || 'CAPTCHA verification failed. Please try again.');
                }
                else {
                    showUploadServerError(serverErrorMsg,
                        'Upload failed.', data.detail || 'An unexpected error occurred. Please try again.');
                }
            }
        } 
        catch (error) {
            if (requiresCaptcha && typeof turnstile !== 'undefined') {
                turnstile.reset();
                document.getElementById('upload-section').classList.add('d-none');
            }
            showUploadServerError(serverErrorMsg,
                'Connection error.', 'Could not reach the server. Please check your connection and try again.');
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