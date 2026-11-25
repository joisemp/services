const sidebars = document.querySelectorAll('.sidebar');
const menuButton = document.querySelector('.menu');
const phoneQuery = window.matchMedia('(max-width: 430px)');

function syncSidebarForViewport() {
    sidebars.forEach((sidebar) => {
        if (phoneQuery.matches) {
            sidebar.classList.add('sidebar-collapsed');
        } else {
            sidebar.classList.remove('sidebar-collapsed');
        }
    });
}

// Phone: closed by default. Larger screens: fully expanded (no icon rail).
syncSidebarForViewport();
if (typeof phoneQuery.addEventListener === 'function') {
    phoneQuery.addEventListener('change', syncSidebarForViewport);
} else if (typeof phoneQuery.addListener === 'function') {
    phoneQuery.addListener(syncSidebarForViewport);
}

if (menuButton) {
    menuButton.addEventListener('click', function () {
        sidebars.forEach((sidebar) => {
            sidebar.classList.toggle('sidebar-collapsed');
        });
    });
}
