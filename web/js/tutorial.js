(function () {
    function reveal(hash) {
        var id = hash ? decodeURIComponent(hash.replace(/^#/, '')) : '';
        var target = id ? document.getElementById(id) : null;
        if (!target) return;
        var panel = target.closest('.collapse') || target.querySelector(':scope > .collapse');
        if (!panel || panel.classList.contains('show')) return;
        panel.addEventListener('shown.bs.collapse', function () {
            target.scrollIntoView();
        }, { once: true });
        bootstrap.Collapse.getOrCreateInstance(panel).show();
    }

    document.querySelectorAll('.card-toggle').forEach(function (header) {
        header.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                header.click();
            }
        });
    });
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a[href*="#"]');
        if (link && link.pathname === window.location.pathname) reveal(link.hash);
    });
    window.addEventListener('hashchange', function () { reveal(window.location.hash); });
    reveal(window.location.hash);
})();