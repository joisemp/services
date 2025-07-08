let sidebarCollabs = document.querySelectorAll('.sidebar');
let menuButton = document.querySelector('.menu');

if (menuButton) {
    menuButton.addEventListener('click', function() {
        sidebarCollabs.forEach(function(sidebar) {
            // Toggle a class for better state management
            sidebar.classList.toggle('sidebar-collapsed');
        });
    });
}

