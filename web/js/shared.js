const API_BASE_URL = '/api';

// ==========================================
// Configuration getter
// ==========================================
async function getAppConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        return await response.json();
    } 
    catch (error) {
        console.error("Could not load config from server, using fallbacks.", error);
        return { session_timeout_hours: 2, saved_session_timeout_hours: 168 }; 
    }
}

// ==========================================
// Helper functions (Cookie management)
// ==========================================
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}