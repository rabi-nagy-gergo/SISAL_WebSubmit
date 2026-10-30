const API_BASE_URL = 'api';

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

// ==========================================
// Navbar Component Logic
// ==========================================
async function loadNavbar() {
    try {
        const timestamp = new Date().getTime();
        const response = await fetch(`navbar.html?v=${timestamp}`);
        
        if (!response.ok) {
            return;
        }
        
        const html = await response.text();        
        document.body.insertAdjacentHTML('afterbegin', html);
        
        const path = window.location.pathname;
        const page = path.split('/').pop() || 'index.html';
        
        const navHome = document.getElementById('nav-home');
        const navAutoqc = document.getElementById('nav-autoqc');
        const navTutorial = document.getElementById('nav-tutorial');
        const navAbout = document.getElementById('nav-about');
        
        const autoqcPages = ['autoqc_proxy.html', 'upload.html', 'validate.html', 'plots.html', 'download.html'];
        
        if (page === 'index.html' || page === '') {
            if (navHome) navHome.classList.add('active');
        } 
        else if (page === 'tutorial.html') {
            if (navTutorial) navTutorial.classList.add('active');
        } 
        else if (page === 'about.html') {
            if (navAbout) navAbout.classList.add('active');
        } 
        else if (autoqcPages.includes(page)) {
            if (navAutoqc) {
                navAutoqc.classList.add('active');
                
                navAutoqc.href = 'javascript:void(0);';
                navAutoqc.style.cursor = 'default';
                navAutoqc.title = 'You are currently in the AutoQC process';
            }
        }
    } 
    catch (error) {
        console.error("An error occurred while loading navbar: ", error);
    }
}

window.addEventListener('DOMContentLoaded', loadNavbar);